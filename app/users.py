"""
EasyBill - User management (admin only)
"""
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User
from app.utils import admin_required

bp = Blueprint('users', __name__)


@bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.id).all()
    return render_template('users/list.html', users=users)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if not username or not password:
            flash('ใส่ชื่อผู้ใช้และรหัสผ่าน', 'danger')
            return redirect(url_for('users.new'))
        if User.query.filter_by(username=username).first():
            flash('ชื่อผู้ใช้นี้มีอยู่แล้ว', 'danger')
            return redirect(url_for('users.new'))
        u = User(
            username=username,
            email=request.form.get('email') or None,
            full_name=request.form.get('full_name') or None,
            role=request.form.get('role', 'user'),
            is_active=True,
        )
        u.set_password(password)
        db.session.add(u); db.session.commit()
        flash(f'เพิ่มผู้ใช้ {username} เรียบร้อย', 'success')
        return redirect(url_for('users.edit', uid=u.id))
    from app.models import Company
    all_active_companies = Company.query.filter_by(is_active=True).order_by(Company.id).all()
    return render_template('users/form.html', user=None, all_active_companies=all_active_companies)


@bp.route('/<int:uid>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(uid):
    from app.models import Company
    u = User.query.get_or_404(uid)
    if request.method == 'POST':
        u.full_name = request.form.get('full_name') or None
        u.email = request.form.get('email') or None
        # อย่าให้ลด role ของตัวเองเป็น user เพื่อกัน lock-out
        new_role = request.form.get('role', 'user')
        if u.id == current_user.id and new_role != 'admin':
            flash('ไม่สามารถลด role ของตัวเอง', 'warning')
        else:
            u.role = new_role
        u.is_active = bool(request.form.get('is_active'))
        # permissions + companies (เฉพาะเมื่อ role=user)
        if u.role == 'user':
            perms = {}
            for k in User.ALL_PERMS:
                perms[k] = request.form.get(f'perm_{k}') == '1'
            u.permissions = json.dumps(perms)
            # company access
            new_companies = []
            for co in Company.query.filter_by(is_active=True).all():
                if request.form.get(f'company_{co.id}') == '1':
                    new_companies.append(co)
            u.companies = new_companies
        else:
            u.permissions = None
            u.companies = []  # admin ไม่ต้องเก็บ — ดึงทุกบริษัทอยู่แล้ว
        # reset password
        new_pw = request.form.get('new_password') or ''
        if new_pw:
            u.set_password(new_pw)
            flash('รีเซ็ตรหัสผ่านแล้ว', 'info')
        db.session.commit()
        flash('บันทึกข้อมูลผู้ใช้เรียบร้อย', 'success')
        return redirect(url_for('users.index'))
    all_active_companies = Company.query.filter_by(is_active=True).order_by(Company.id).all()
    return render_template('users/form.html', user=u, all_active_companies=all_active_companies)


@bp.route('/<int:uid>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash('ห้ามระงับบัญชีตัวเอง', 'warning')
    else:
        u.is_active = not u.is_active
        db.session.commit()
        flash(f'{"เปิดใช้งาน" if u.is_active else "ระงับ"}ผู้ใช้ {u.username} แล้ว', 'success')
    return redirect(url_for('users.index'))
