"""
ThaiBill - Settings
- ข้อมูลกิจการ + โลโก้ + ลายเซ็น (หน้า /settings/)
- Preferences ภาษา/ธีม (POST /settings/preferences)
- Backup/Restore (/settings/backup, /settings/restore)
- Google Drive (/settings/gdrive/*)
"""
import io
import json
import time
import zipfile
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_file, make_response)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Company

bp = Blueprint('settings', __name__)


# ============================================================
# Helpers
# ============================================================
def _get_company():
    from app.utils import current_company
    c = current_company()
    if not c:
        c = Company()
        db.session.add(c); db.session.commit()
        from flask import session
        session['active_company_id'] = c.id
    return c


def _save_upload(field_name, prefix):
    f = request.files.get(field_name)
    if not f or not f.filename:
        return None
    ext = Path(f.filename).suffix.lower()
    allowed = current_app.config.get('ALLOWED_IMAGE_EXTS',
                                     {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'})
    if ext not in allowed:
        flash(f'ไฟล์ "{f.filename}" ไม่รองรับ — ต้องเป็น {", ".join(sorted(allowed))}', 'danger')
        return None
    upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(f'{prefix}_{int(time.time())}{ext}')
    f.save(upload_dir / filename)
    return f'uploads/{filename}'


def _delete_upload(rel_path):
    if not rel_path:
        return
    full = Path(current_app.static_folder) / rel_path
    try:
        if full.exists() and full.is_file():
            full.unlink()
    except Exception:
        pass


def _instance_dir():
    return Path(current_app.root_path).parent / 'instance'


def _gdrive_creds_dir():
    """โฟลเดอร์เก็บ Service Account JSON (ใน instance/ จะไม่ถูกแชร์ผ่าน static)"""
    p = _instance_dir() / 'gdrive'
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============================================================
# Main settings page
# ============================================================
@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    company = _get_company()

    if request.method == 'POST':
        action = request.form.get('action', 'save')

        if action == 'remove_logo':
            _delete_upload(company.logo_path)
            company.logo_path = None
            db.session.commit()
            flash('ลบโลโก้แล้ว', 'success')
            return redirect(url_for('settings.index'))

        if action == 'remove_signature':
            _delete_upload(company.signature_path)
            company.signature_path = None
            db.session.commit()
            flash('ลบลายเซ็นแล้ว', 'success')
            return redirect(url_for('settings.index'))

        # save profile
        company.name = request.form.get('name') or company.name
        company.branch = request.form.get('branch') or 'สำนักงานใหญ่'
        company.tax_id = request.form.get('tax_id')
        company.address = request.form.get('address')
        company.phone = request.form.get('phone')
        company.email = request.form.get('email')
        company.website = request.form.get('website')
        company.bank_info = request.form.get('bank_info')
        company.default_terms = request.form.get('default_terms')
        try:
            company.default_vat_rate = float(request.form.get('default_vat_rate') or 7.0)
        except ValueError:
            company.default_vat_rate = 7.0

        new_logo = _save_upload('logo', 'logo')
        if new_logo:
            _delete_upload(company.logo_path); company.logo_path = new_logo
        new_sig = _save_upload('signature', 'signature')
        if new_sig:
            _delete_upload(company.signature_path); company.signature_path = new_sig

        db.session.commit()
        flash('บันทึกข้อมูลกิจการเรียบร้อย', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings.html', company=company,
                           gdrive_configured=_is_gdrive_configured(company))


# ============================================================
# Preferences (Language + Theme)
# ============================================================
# ============================================================
# Display settings — ผู้ใช้ตั้งได้ว่าจะแสดง field ไหนในฟอร์ม/PDF บ้าง
# ============================================================
DISPLAY_DEFAULTS = {
    # Header fields
    'show_reference':       True,
    'show_project':         True,
    'show_note':            True,
    'show_terms':           True,
    'show_vat_options':     True,
    'show_currency':        False,  # ปิดเริ่มต้น — ส่วนใหญ่ใช้ THB
    'show_category':        False,
    'show_tags':            False,
    'show_attachments':     True,
    # Item columns
    'show_item_code':       True,
    'show_item_description': True,
    'show_item_unit':       True,
    'show_item_discount':   True,
    'show_item_account':    False,
    # Items layout style
    'items_style':          'detailed',
}


# สกุลเงินที่รองรับ
CURRENCIES = [
    ('THB', '฿', 'บาทไทย'),
    ('USD', '$', 'US Dollar'),
    ('EUR', '€', 'Euro'),
    ('JPY', '¥', 'Japanese Yen'),
    ('CNY', '¥', 'Chinese Yuan'),
    ('GBP', '£', 'British Pound'),
    ('SGD', 'S$', 'Singapore Dollar'),
    ('AUD', 'A$', 'Australian Dollar'),
    ('MYR', 'RM', 'Malaysian Ringgit'),
    ('VND', '₫', 'Vietnamese Dong'),
]


def get_display_settings(company):
    """รวมค่า default + setting ของ company → คืน dict พร้อมใช้ใน template"""
    import json
    settings = dict(DISPLAY_DEFAULTS)
    if company and company.display_settings:
        try:
            saved = json.loads(company.display_settings)
            settings.update(saved)
        except Exception:
            pass
    return settings


THEMES = {
    'default':  {'name': 'ค่าเริ่มต้น (น้ำเงิน)', 'name_en': 'Default (Blue)',
                 'body': 'theme-default', 'sidebar': 'sidebar-dark-primary', 'navbar': 'navbar-white navbar-light'},
    'navy':     {'name': 'กรมท่า',                'name_en': 'Navy',
                 'body': 'theme-navy', 'sidebar': 'sidebar-dark-navy', 'navbar': 'navbar-white navbar-light'},
    'forest':   {'name': 'เขียวเข้ม',              'name_en': 'Forest',
                 'body': 'theme-forest', 'sidebar': 'sidebar-dark-success', 'navbar': 'navbar-white navbar-light'},
    'maroon':   {'name': 'แดงเข้ม',                'name_en': 'Maroon',
                 'body': 'theme-maroon', 'sidebar': 'sidebar-dark-danger', 'navbar': 'navbar-white navbar-light'},
    'purple':   {'name': 'ม่วง',                   'name_en': 'Purple',
                 'body': 'theme-purple', 'sidebar': 'sidebar-dark-indigo', 'navbar': 'navbar-white navbar-light'},
    'dark':     {'name': 'โหมดมืด',                'name_en': 'Dark Mode',
                 'body': 'dark-mode theme-default', 'sidebar': 'sidebar-dark-primary',
                 'navbar': 'navbar-dark navbar-dark'},
    'light':    {'name': 'สว่าง (ฟ้าคราม)',         'name_en': 'Light (Cyan)',
                 'body': 'theme-cyan', 'sidebar': 'sidebar-light-primary text-sm', 'navbar': 'navbar-white navbar-light'},
}


@bp.route('/preferences', methods=['POST'])
def preferences():
    """ตั้งภาษา (ทุกคน) + ธีม (ต้อง login)"""
    from flask_login import current_user
    lang = request.form.get('lang', 'th')
    theme = request.form.get('theme', 'default')

    if current_user.is_authenticated and theme in THEMES:
        company = _get_company()
        company.theme = theme
        db.session.commit()

    resp = make_response(redirect(request.referrer or url_for('main.dashboard')))
    if lang in ('th', 'en'):
        resp.set_cookie('lang', lang, max_age=60*60*24*365, samesite='Lax')

    return resp


# ============================================================
# Display settings save (จาก modal ในหน้า form)
# ============================================================
@bp.route('/display', methods=['POST'])
@login_required
def save_display():
    import json
    company = _get_company()
    bool_keys = ['show_reference', 'show_project', 'show_note', 'show_terms',
                 'show_vat_options', 'show_currency', 'show_category', 'show_tags',
                 'show_attachments', 'show_item_code', 'show_item_description',
                 'show_item_unit', 'show_item_discount', 'show_item_account']
    new_settings = {}
    for k in bool_keys:
        new_settings[k] = request.form.get(k) == '1'
    items_style = request.form.get('items_style', 'detailed')
    new_settings['items_style'] = items_style if items_style in ('detailed', 'compact') else 'detailed'

    company.display_settings = json.dumps(new_settings)
    db.session.commit()

    from flask import jsonify
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'ok': True, 'settings': new_settings})
    flash('บันทึกการตั้งค่าการแสดงผลแล้ว', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))


# ============================================================
# Backup
# ============================================================
@bp.route('/backup', methods=['GET'])
@login_required
def backup_download():
    """สร้าง zip ของ instance/thaibill.db + uploads/ แล้วส่งให้ download"""
    inst = _instance_dir()
    uploads = Path(current_app.config['UPLOAD_FOLDER'])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # metadata
        meta = {
            'app': 'thaibill',
            'version': 2,
            'created_at': datetime.utcnow().isoformat(),
        }
        zf.writestr('backup_info.json', json.dumps(meta, indent=2))

        # database
        db_path = inst / 'thaibill.db'
        if db_path.exists():
            zf.write(db_path, 'thaibill.db')

        # uploads (logo, signature, ...)
        if uploads.exists():
            for f in uploads.rglob('*'):
                if f.is_file():
                    arcname = f'uploads/{f.relative_to(uploads)}'
                    zf.write(f, arcname)

        # gdrive credentials (optional — เก็บไว้คู่กันเพื่อ portability)
        gd = _gdrive_creds_dir()
        for f in gd.glob('*.json'):
            zf.write(f, f'gdrive/{f.name}')

    buf.seek(0)
    fname = f'thaibill-backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.zip'
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name=fname)


@bp.route('/restore', methods=['POST'])
@login_required
def restore_upload():
    """รับ zip backup → ทับไฟล์ DB + uploads"""
    f = request.files.get('backup_file')
    if not f or not f.filename:
        flash('กรุณาเลือกไฟล์ .zip', 'danger')
        return redirect(url_for('settings.index') + '#backup')
    if not f.filename.lower().endswith('.zip'):
        flash('ไฟล์ต้องเป็น .zip', 'danger')
        return redirect(url_for('settings.index') + '#backup')

    # อ่านลง memory แล้วตรวจ
    try:
        zf = zipfile.ZipFile(f.stream)
    except zipfile.BadZipFile:
        flash('ไฟล์ zip เสีย', 'danger')
        return redirect(url_for('settings.index') + '#backup')

    # ตรวจความปลอดภัย (zip slip)
    for n in zf.namelist():
        if n.startswith('/') or '..' in n.replace('\\', '/').split('/'):
            flash('ไฟล์ zip มีพาธไม่ปลอดภัย', 'danger')
            return redirect(url_for('settings.index') + '#backup')

    members = set(zf.namelist())
    if 'backup_info.json' not in members or 'thaibill.db' not in members:
        flash('ไฟล์ zip ไม่ใช่ backup ของ ThaiBill', 'danger')
        return redirect(url_for('settings.index') + '#backup')

    # สำรองของเดิมก่อน
    inst = _instance_dir()
    uploads = Path(current_app.config['UPLOAD_FOLDER'])
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    rb_dir = inst / f'restore-backup-{stamp}'
    rb_dir.mkdir(parents=True, exist_ok=True)
    if (inst / 'thaibill.db').exists():
        shutil.copy2(inst / 'thaibill.db', rb_dir / 'thaibill.db')

    # ปิด DB connection ทั้งหมดก่อนแทนที่ไฟล์
    db.session.close()
    db.engine.dispose()

    # extract
    try:
        # 1) DB
        with zf.open('thaibill.db') as src, open(inst / 'thaibill.db', 'wb') as dst:
            shutil.copyfileobj(src, dst)

        # 2) uploads
        uploads.mkdir(parents=True, exist_ok=True)
        for n in members:
            if n.startswith('uploads/') and not n.endswith('/'):
                target = uploads / Path(n).relative_to('uploads')
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(n) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

        # 3) gdrive credentials (optional)
        gd = _gdrive_creds_dir()
        for n in members:
            if n.startswith('gdrive/') and not n.endswith('/'):
                target = gd / Path(n).name
                with zf.open(n) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
    except Exception as e:
        flash(f'กู้คืนล้มเหลว: {e}', 'danger')
        return redirect(url_for('settings.index') + '#backup')
    finally:
        zf.close()

    flash(f'กู้คืนสำเร็จ — ข้อมูลเดิมสำรองที่ {rb_dir.name} '
          f'· แนะนำ restart service เพื่อโหลด DB ใหม่อย่างสมบูรณ์ '
          f'(sudo systemctl restart thaibill)', 'success')
    return redirect(url_for('main.dashboard'))


# ============================================================
# Google Drive
# ============================================================
def _is_gdrive_configured(company):
    if not company.gdrive_credentials_filename:
        return False
    path = _gdrive_creds_dir() / company.gdrive_credentials_filename
    return path.exists()


@bp.route('/gdrive/save', methods=['POST'])
@login_required
def gdrive_save():
    company = _get_company()
    folder_id = (request.form.get('gdrive_folder_id') or '').strip()
    company.gdrive_folder_id = folder_id or None

    # รับ JSON file ใหม่
    f = request.files.get('gdrive_credentials')
    if f and f.filename:
        if not f.filename.lower().endswith('.json'):
            flash('Service Account credentials ต้องเป็นไฟล์ .json', 'danger')
            return redirect(url_for('settings.index') + '#gdrive')
        # ลบของเก่า
        if company.gdrive_credentials_filename:
            old = _gdrive_creds_dir() / company.gdrive_credentials_filename
            try:
                if old.exists():
                    old.unlink()
            except Exception:
                pass
        fname = secure_filename(f'sa_{int(time.time())}.json')
        f.save(_gdrive_creds_dir() / fname)
        company.gdrive_credentials_filename = fname

    db.session.commit()
    flash('บันทึกการตั้งค่า Google Drive แล้ว', 'success')
    return redirect(url_for('settings.index') + '#gdrive')


@bp.route('/gdrive/remove', methods=['POST'])
@login_required
def gdrive_remove():
    company = _get_company()
    if company.gdrive_credentials_filename:
        old = _gdrive_creds_dir() / company.gdrive_credentials_filename
        try:
            if old.exists():
                old.unlink()
        except Exception:
            pass
    company.gdrive_credentials_filename = None
    company.gdrive_folder_id = None
    db.session.commit()
    flash('ลบการตั้งค่า Google Drive แล้ว', 'success')
    return redirect(url_for('settings.index') + '#gdrive')


def _get_gdrive_service(company):
    """สร้าง Google Drive API service จาก Service Account credentials"""
    if not _is_gdrive_configured(company):
        raise ValueError('ยังไม่ได้ตั้งค่า Google Drive')
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError(
            'ไม่พบ google-api-python-client — ติดตั้งด้วย: '
            'pip install google-api-python-client google-auth')

    cred_path = _gdrive_creds_dir() / company.gdrive_credentials_filename
    creds = service_account.Credentials.from_service_account_file(
        str(cred_path), scopes=['https://www.googleapis.com/auth/drive.file'])
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


@bp.route('/gdrive/test', methods=['POST'])
@login_required
def gdrive_test():
    company = _get_company()
    try:
        svc = _get_gdrive_service(company)
        # ลอง list 1 ไฟล์เพื่อเทสต์ auth
        about = svc.about().get(fields='user').execute()
        email = about.get('user', {}).get('emailAddress', '?')
        flash(f'เชื่อมต่อสำเร็จ — Service Account: {email}', 'success')
    except Exception as e:
        flash(f'เชื่อมต่อล้มเหลว: {e}', 'danger')
    return redirect(url_for('settings.index') + '#gdrive')


@bp.route('/gdrive/upload', methods=['POST'])
@login_required
def gdrive_upload():
    """สร้าง backup zip แล้วอัปโหลดเข้า Google Drive โฟลเดอร์ที่ระบุ"""
    company = _get_company()
    if not company.gdrive_folder_id:
        flash('กรุณาระบุรหัสโฟลเดอร์ Google Drive', 'danger')
        return redirect(url_for('settings.index') + '#gdrive')

    try:
        svc = _get_gdrive_service(company)
    except Exception as e:
        flash(f'เชื่อมต่อ Google Drive ล้มเหลว: {e}', 'danger')
        return redirect(url_for('settings.index') + '#gdrive')

    # สร้าง backup zip ใน temp file
    inst = _instance_dir()
    uploads = Path(current_app.config['UPLOAD_FOLDER'])

    tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    try:
        with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('backup_info.json', json.dumps({
                'app': 'thaibill', 'version': 2,
                'created_at': datetime.utcnow().isoformat(),
            }, indent=2))
            db_path = inst / 'thaibill.db'
            if db_path.exists():
                zf.write(db_path, 'thaibill.db')
            if uploads.exists():
                for f in uploads.rglob('*'):
                    if f.is_file():
                        zf.write(f, f'uploads/{f.relative_to(uploads)}')

        # อัปโหลดไป Drive
        from googleapiclient.http import MediaFileUpload
        fname = f'thaibill-backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.zip'
        media = MediaFileUpload(tmp.name, mimetype='application/zip', resumable=False)
        result = svc.files().create(body={
            'name': fname,
            'parents': [company.gdrive_folder_id],
        }, media_body=media, fields='id,name,webViewLink').execute()

        link = result.get('webViewLink', '')
        flash(f'อัปโหลด "{fname}" สำเร็จ — {link}', 'success')
    except Exception as e:
        flash(f'อัปโหลดล้มเหลว: {e}', 'danger')
    finally:
        try:
            Path(tmp.name).unlink()
        except Exception:
            pass

    return redirect(url_for('settings.index') + '#gdrive')


# ============================================================
# Multi-company: switch / add new
# ============================================================
@bp.route('/companies/switch/<int:cid>')
@login_required
def switch_company(cid):
    """สลับบริษัทที่ใช้งาน — ตรวจว่า user มีสิทธิ์เข้าบริษัทนี้"""
    from flask import session
    co = Company.query.get_or_404(cid)
    if not co.is_active:
        flash('บริษัทนี้ถูกระงับ', 'warning')
        return redirect(url_for('main.dashboard'))
    if not current_user.can_access_company(cid):
        flash(f'คุณไม่มีสิทธิ์เข้าใช้งานบริษัท "{co.name}" — ติดต่อผู้ดูแลระบบ', 'danger')
        return redirect(url_for('main.dashboard'))
    session['active_company_id'] = co.id
    flash(f'สลับมาที่ "{co.name}" แล้ว', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))


@bp.route('/companies/new', methods=['GET', 'POST'])
@login_required
def new_company():
    """เพิ่มบริษัทใหม่"""
    from flask import session
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('กรุณาใส่ชื่อบริษัท', 'danger')
            return redirect(url_for('settings.new_company'))
        co = Company(name=name,
                     branch=request.form.get('branch') or 'สำนักงานใหญ่',
                     tax_id=request.form.get('tax_id') or None,
                     address=request.form.get('address') or None,
                     phone=request.form.get('phone') or None,
                     email=request.form.get('email') or None,
                     website=request.form.get('website') or None,
                     is_active=True)
        db.session.add(co); db.session.commit()
        session['active_company_id'] = co.id
        flash(f'เพิ่มบริษัท "{co.name}" และสลับมาที่นี่แล้ว', 'success')
        return redirect(url_for('settings.index'))
    return render_template('settings_new_company.html')


# ============================================================
# OAuth settings (admin only — UI ตั้งค่า Google/Microsoft)
# ============================================================
@bp.route('/oauth', methods=['GET', 'POST'])
@login_required
def oauth_settings():
    from app.utils import admin_required
    if not current_user.is_admin():
        flash('สิทธิ์ผู้ดูแลระบบเท่านั้น', 'danger')
        return redirect(url_for('main.dashboard'))

    from app.models import AppSetting
    if request.method == 'POST':
        # Google
        AppSetting.set_value('oauth_google_client_id',     request.form.get('google_client_id', '').strip())
        AppSetting.set_value('oauth_google_client_secret', request.form.get('google_client_secret', '').strip())
        AppSetting.set_value('oauth_google_enabled',       '1' if request.form.get('google_enabled') else '0')
        # Microsoft
        AppSetting.set_value('oauth_microsoft_client_id',     request.form.get('ms_client_id', '').strip())
        AppSetting.set_value('oauth_microsoft_client_secret', request.form.get('ms_client_secret', '').strip())
        AppSetting.set_value('oauth_microsoft_tenant',        request.form.get('ms_tenant', 'common').strip())
        AppSetting.set_value('oauth_microsoft_enabled',       '1' if request.form.get('ms_enabled') else '0')
        # Auto-create
        AppSetting.set_value('oauth_auto_create_users',
                             '1' if request.form.get('auto_create') else '0')
        db.session.commit()
        flash('บันทึก OAuth settings เรียบร้อย', 'success')
        return redirect(url_for('settings.oauth_settings'))

    # GET
    config = {
        'google_client_id':       AppSetting.get_value('oauth_google_client_id', ''),
        'google_client_secret':   AppSetting.get_value('oauth_google_client_secret', ''),
        'google_enabled':         AppSetting.get_bool('oauth_google_enabled', False),
        'ms_client_id':           AppSetting.get_value('oauth_microsoft_client_id', ''),
        'ms_client_secret':       AppSetting.get_value('oauth_microsoft_client_secret', ''),
        'ms_tenant':              AppSetting.get_value('oauth_microsoft_tenant', 'common'),
        'ms_enabled':             AppSetting.get_bool('oauth_microsoft_enabled', False),
        'auto_create':            AppSetting.get_bool('oauth_auto_create_users', False),
    }
    google_redirect = url_for('auth.oauth_callback', provider='google', _external=True)
    ms_redirect = url_for('auth.oauth_callback', provider='microsoft', _external=True)
    return render_template('settings_oauth.html', config=config,
                           google_redirect=google_redirect, ms_redirect=ms_redirect)
