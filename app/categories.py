"""
EasyBill - Categories (กลุ่มจัดประเภทเอกสาร)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app import db
from app.utils import current_company_id
from app.models import Category

bp = Blueprint('categories', __name__)


@bp.route('/')
@login_required
def index():
    cats = Category.query.filter_by(is_active=True, company_id=current_company_id()).order_by(Category.name).all()
    return render_template('categories/list.html', categories=cats)


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def edit(cid=None):
    cat = Category.query.get_or_404(cid) if cid else Category()
    if request.method == 'POST':
        cat.name = (request.form.get('name') or '').strip()
        cat.description = request.form.get('description')
        cat.color = request.form.get('color') or '#6366f1'
        if not cat.name:
            flash('กรุณาใส่ชื่อกลุ่ม', 'danger')
        else:
            cat.company_id = current_company_id()
            if not cid:
                db.session.add(cat)
            db.session.commit()
            flash('บันทึกกลุ่มเรียบร้อย', 'success')
            return redirect(url_for('categories.index'))
    return render_template('categories/form.html', category=cat)


@bp.route('/<int:cid>/delete', methods=['POST'])
@login_required
def delete(cid):
    cat = Category.query.get_or_404(cid)
    if len(cat.documents) > 0:
        cat.is_active = False
        flash(f'กลุ่ม "{cat.name}" มีเอกสารผูกอยู่ — ถูกซ่อนแทนการลบ', 'warning')
    else:
        db.session.delete(cat)
        flash('ลบกลุ่มเรียบร้อย', 'success')
    db.session.commit()
    return redirect(url_for('categories.index'))


@bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    """สำหรับ inline create จากในฟอร์มเอกสาร"""
    name = (request.form.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'name required'}), 400
    existing = Category.query.filter_by(name=name, company_id=current_company_id()).first()
    if existing:
        return jsonify({'ok': True, 'id': existing.id, 'name': existing.name})
    cat = Category(name=name, color=request.form.get('color') or '#6366f1', company_id=current_company_id())
    db.session.add(cat)
    db.session.commit()
    return jsonify({'ok': True, 'id': cat.id, 'name': cat.name})
