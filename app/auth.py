"""
EasyBill - Authentication (login + Google/Microsoft OAuth)
"""
import os
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template('auth/login.html',
                           google_enabled=_oauth_enabled('google'),
                           ms_enabled=_oauth_enabled('microsoft'))


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ออกจากระบบเรียบร้อย', 'success')
    return redirect(url_for('auth.login'))


# ============================================================
# OAuth: Google + Microsoft
# ใช้งานได้เมื่อตั้ง env vars: 
#   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
#   MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT (optional, default 'common')
# ต้องการ HTTPS (ยกเว้น http://localhost) สำหรับ redirect URI
# ============================================================

OAUTH_CONFIG = {
    'google': {
        'auth_url':    'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url':   'https://oauth2.googleapis.com/token',
        'userinfo':    'https://www.googleapis.com/oauth2/v3/userinfo',
        'scope':       'openid email profile',
        'client_id_env':     'GOOGLE_CLIENT_ID',
        'client_secret_env': 'GOOGLE_CLIENT_SECRET',
    },
    'microsoft': {
        'auth_url':    'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize',
        'token_url':   'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
        'userinfo':    'https://graph.microsoft.com/v1.0/me',
        'scope':       'openid email profile User.Read',
        'client_id_env':     'MS_CLIENT_ID',
        'client_secret_env': 'MS_CLIENT_SECRET',
        'tenant_env':        'MS_TENANT',
    },
}


def _oauth_config(provider):
    """ดึง config — ลำดับ: DB (AppSetting) → ENV variable"""
    from app.models import AppSetting
    cfg = OAUTH_CONFIG.get(provider)
    if not cfg:
        return None

    # 1) DB (admin set ผ่าน UI)
    db_id = AppSetting.get_value(f'oauth_{provider}_client_id')
    db_secret = AppSetting.get_value(f'oauth_{provider}_client_secret')
    db_enabled = AppSetting.get_bool(f'oauth_{provider}_enabled', False)

    # 2) ENV fallback
    env_id = os.environ.get(cfg['client_id_env'])
    env_secret = os.environ.get(cfg['client_secret_env'])

    client_id = db_id or env_id
    client_secret = db_secret or env_secret

    if not client_id or not client_secret:
        return None
    # ถ้าตั้งใน DB ต้อง enabled ด้วย ถึงจะใช้
    if db_id and not db_enabled:
        return None

    tenant = (AppSetting.get_value(f'oauth_{provider}_tenant')
              or os.environ.get(cfg.get('tenant_env', ''), 'common'))
    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'auth_url': cfg['auth_url'].replace('{tenant}', tenant),
        'token_url': cfg['token_url'].replace('{tenant}', tenant),
        'userinfo': cfg['userinfo'],
        'scope': cfg['scope'],
    }


def _oauth_enabled(provider):
    """เช็คว่าเปิดใช้งานหรือเปล่า (สำหรับ login page)"""
    return _oauth_config(provider) is not None


@bp.route('/login/<provider>')
def oauth_login(provider):
    """เริ่ม OAuth flow — redirect ไปหน้า login ของ Google/Microsoft"""
    cfg = _oauth_config(provider)
    if not cfg:
        return render_template('auth/oauth_setup.html',
                               provider=provider,
                               provider_name='Google' if provider == 'google' else 'Microsoft')

    state = secrets.token_urlsafe(32)
    session[f'oauth_state_{provider}'] = state

    redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True)
    from urllib.parse import urlencode
    params = {
        'client_id': cfg['client_id'],
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': cfg['scope'],
        'state': state,
        'access_type': 'offline',
        'prompt': 'select_account',
    }
    return redirect(f"{cfg['auth_url']}?{urlencode(params)}")


@bp.route('/login/<provider>/callback')
def oauth_callback(provider):
    """รับ OAuth callback — แลก code เป็น token แล้วดึงข้อมูลผู้ใช้"""
    cfg = _oauth_config(provider)
    if not cfg:
        flash(f'ไม่ได้ตั้งค่า OAuth {provider}', 'danger')
        return redirect(url_for('auth.login'))

    # ตรวจ state ป้องกัน CSRF
    expected = session.pop(f'oauth_state_{provider}', None)
    if not expected or request.args.get('state') != expected:
        flash('OAuth state ไม่ถูกต้อง (อาจถูกขัดจังหวะ)', 'danger')
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    if not code:
        err = request.args.get('error_description') or request.args.get('error') or 'unknown'
        flash(f'OAuth ล้มเหลว: {err}', 'danger')
        return redirect(url_for('auth.login'))

    try:
        import requests
        redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True)
        token_resp = requests.post(cfg['token_url'], data={
            'code': code,
            'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret'],
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }, timeout=10)
        token_resp.raise_for_status()
        token = token_resp.json()
        access_token = token.get('access_token')

        user_resp = requests.get(cfg['userinfo'],
                                 headers={'Authorization': f'Bearer {access_token}'},
                                 timeout=10)
        user_resp.raise_for_status()
        info = user_resp.json()

        email = info.get('email') or info.get('mail') or info.get('userPrincipalName')
        name = info.get('name') or info.get('displayName') or email
        if not email:
            flash('ไม่พบอีเมลใน OAuth response', 'danger')
            return redirect(url_for('auth.login'))

        # หา user จาก email หรือ username
        user = User.query.filter(
            (User.username == email) | (User.email == email)
        ).first() if hasattr(User, 'email') else User.query.filter_by(username=email).first()

        if not user:
            # Auto-create ถ้า admin เปิด setting นี้ไว้
            from app.models import AppSetting
            if AppSetting.get_bool('oauth_auto_create_users', False):
                user = User(username=email, email=email, full_name=name,
                            role='user', is_active=True)
                # สุ่มรหัสผ่าน (user จะ login ผ่าน OAuth เท่านั้น)
                import secrets as _sec
                user.set_password(_sec.token_urlsafe(24))
                db.session.add(user); db.session.commit()
                flash(f'สร้างบัญชีอัตโนมัติให้ {email} (role=user) — ติดต่อ admin เพื่อกำหนดสิทธิ์บริษัท', 'info')
            else:
                flash(f'ยังไม่มีบัญชี {email} ในระบบ — แจ้งผู้ดูแลให้สร้างบัญชีก่อน', 'warning')
                return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('บัญชีนี้ถูกระงับการใช้งาน', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=True)
        flash(f'เข้าสู่ระบบสำเร็จด้วย {provider.capitalize()} ({email})', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        flash(f'OAuth ล้มเหลว: {e}', 'danger')
        return redirect(url_for('auth.login'))
