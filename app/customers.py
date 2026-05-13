"""
ThaiBill - Customer management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import or_
from app import db
from app.utils import current_company_id, permission_required
from app.models import Customer

bp = Blueprint('customers', __name__)


@bp.route('/')
@login_required
def index():
    q = (request.args.get('q') or '').strip()
    query = Customer.query.filter_by(company_id=current_company_id())
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Customer.name.ilike(like),
            Customer.code.ilike(like),
            Customer.tax_id.ilike(like),
            Customer.phone.ilike(like),
        ))
    customers = query.order_by(Customer.created_at.desc()).all()
    return render_template('customers/list.html', customers=customers, q=q)


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def edit(cid=None):
    customer = Customer.query.get_or_404(cid) if cid else Customer()

    if request.method == 'POST':
        customer.code = (request.form.get('code') or '').strip() or None
        customer.name = (request.form.get('name') or '').strip()
        customer.contact_person = request.form.get('contact_person')
        customer.tax_id = request.form.get('tax_id')
        customer.branch = request.form.get('branch') or 'สำนักงานใหญ่'
        customer.address = request.form.get('address')
        customer.phone = request.form.get('phone')
        customer.email = request.form.get('email')
        customer.customer_type = request.form.get('customer_type') or 'company'
        try:
            customer.credit_days = int(request.form.get('credit_days') or 30)
        except ValueError:
            customer.credit_days = 30
        customer.note = request.form.get('note')

        if not customer.name:
            flash('กรุณากรอกชื่อลูกค้า', 'danger')
        else:
            # ตั้ง company_id เสมอ (เผื่อ user สลับบริษัทระหว่างแก้ไข)
            customer.company_id = current_company_id()
            if not cid:
                # auto code
                if not customer.code:
                    last = Customer.query.order_by(Customer.id.desc()).first()
                    seq = (last.id + 1) if last else 1
                    customer.code = f'C{seq:05d}'
                db.session.add(customer)
            db.session.commit()
            flash('บันทึกข้อมูลลูกค้าเรียบร้อย', 'success')
            return redirect(url_for('customers.index'))

    return render_template('customers/form.html', customer=customer)


@bp.route('/<int:cid>/delete', methods=['POST'])
@login_required
@permission_required('delete_customers')
def delete(cid):
    customer = Customer.query.get_or_404(cid)
    if customer.quotations.count() > 0:
        # soft delete
        customer.is_active = False
        flash('ลูกค้านี้มีเอกสารผูกอยู่ ระบบจะปิดการใช้งานแทนการลบ', 'warning')
    else:
        db.session.delete(customer)
        flash('ลบลูกค้าเรียบร้อย', 'success')
    db.session.commit()
    return redirect(url_for('customers.index'))


# API for autocomplete in quotation form
@bp.route('/api/search')
@login_required
def api_search():
    q = (request.args.get('q') or '').strip()
    query = Customer.query.filter_by(is_active=True, company_id=current_company_id())
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Customer.name.ilike(like),
            Customer.code.ilike(like),
        ))
    results = []
    for c in query.limit(20).all():
        results.append({
            'id': c.id,
            'code': c.code,
            'name': c.name,
            'tax_id': c.tax_id,
            'branch': c.branch,
            'address': c.address,
            'contact_person': c.contact_person,
            'phone': c.phone,
        })
    return jsonify(results)
