"""
ThaiBill - Product / Service management
"""
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from sqlalchemy import or_
from app import db
from app.utils import current_company_id, permission_required
from app.models import Product

bp = Blueprint('products', __name__)


def _parse_decimal(s, default=0):
    try:
        return Decimal(str(s).replace(',', '').strip() or '0')
    except Exception:
        return Decimal(default)


@bp.route('/')
@login_required
def index():
    q = (request.args.get('q') or '').strip()
    query = Product.query.filter_by(company_id=current_company_id())
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Product.name.ilike(like),
            Product.code.ilike(like),
            Product.description.ilike(like),
        ))
    products = query.order_by(Product.created_at.desc()).all()
    return render_template('products/list.html', products=products, q=q)


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def edit(pid=None):
    product = Product.query.get_or_404(pid) if pid else Product()

    if request.method == 'POST':
        product.code = (request.form.get('code') or '').strip() or None
        product.name = (request.form.get('name') or '').strip()
        product.description = request.form.get('description')
        product.unit = request.form.get('unit') or 'ชิ้น'
        product.price = _parse_decimal(request.form.get('price'))
        product.cost = _parse_decimal(request.form.get('cost'))
        product.product_type = request.form.get('product_type') or 'goods'
        product.vat_type = request.form.get('vat_type') or 'exclude'

        if not product.name:
            flash('กรุณากรอกชื่อสินค้า/บริการ', 'danger')
        else:
            product.company_id = current_company_id()
            if not pid:
                if not product.code:
                    last = Product.query.order_by(Product.id.desc()).first()
                    seq = (last.id + 1) if last else 1
                    product.code = f'P{seq:05d}'
                db.session.add(product)
            db.session.commit()
            flash('บันทึกสินค้า/บริการเรียบร้อย', 'success')
            return redirect(url_for('products.index'))

    return render_template('products/form.html', product=product)


@bp.route('/<int:pid>/delete', methods=['POST'])
@login_required
@permission_required('delete_products')
def delete(pid):
    product = Product.query.get_or_404(pid)
    product.is_active = False  # soft delete
    db.session.commit()
    flash('ปิดการใช้งานสินค้าเรียบร้อย', 'success')
    return redirect(url_for('products.index'))


@bp.route('/api/search')
@login_required
def api_search():
    q = (request.args.get('q') or '').strip()
    query = Product.query.filter_by(is_active=True, company_id=current_company_id())
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Product.name.ilike(like),
            Product.code.ilike(like),
            Product.description.ilike(like),
        ))
    results = []
    for p in query.limit(20).all():
        results.append({
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'description': p.description or '',
            'unit': p.unit,
            'price': float(p.price or 0),
            'product_type': p.product_type,
        })
    return jsonify(results)
