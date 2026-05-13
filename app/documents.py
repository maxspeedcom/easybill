"""
ThaiBill v2 - Document Blueprint
รองรับทุกประเภท: QT, IV, DO, TI, RC ผ่าน URL /docs/<doc_type>/
"""
from datetime import date, timedelta, datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, make_response, abort)
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.utils import current_company_id, permission_required
from app.models import (Document, DocumentItem, Customer, Company, Product,
                        Category, DocumentAttachment)
from app.utils import next_doc_number

bp = Blueprint('documents', __name__)


# ============================================================
# Helpers
# ============================================================
def _money(x, default='0'):
    try:
        v = Decimal(str(x).replace(',', '').strip() or default)
    except Exception:
        v = Decimal(default)
    return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _decimal(x, default='0'):
    try:
        return Decimal(str(x).replace(',', '').strip() or default)
    except Exception:
        return Decimal(default)


def _calc_totals(d):
    subtotal = Decimal('0.00')
    for it in d.items:
        gross = (it.quantity or 0) * (it.unit_price or 0)
        disc  = gross * Decimal(str(it.discount_percent or 0)) / Decimal('100')
        total = (Decimal(str(gross)) - disc).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        it.line_total = total
        subtotal += total

    after_discount = subtotal - Decimal(str(d.discount_amount or 0))
    if after_discount < 0:
        after_discount = Decimal('0.00')

    vat_rate = Decimal(str(d.vat_rate or 0))
    if d.price_includes_vat:
        grand = after_discount
        base = (after_discount * Decimal('100') / (Decimal('100') + vat_rate)) if vat_rate else after_discount
        vat_amount = grand - base
        d.after_discount = base.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        d.vat_amount = vat_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        d.grand_total = grand.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        vat_amount = (after_discount * vat_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        d.after_discount = after_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        d.vat_amount = vat_amount
        d.grand_total = (after_discount + vat_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    d.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _get_company():
    c = Company.query.first()
    if not c:
        c = Company()
        db.session.add(c)
        db.session.commit()
    return c


def _image_data_url(rel_path):
    """อ่านไฟล์รูปจาก static folder แล้วคืน data: URL สำหรับฝังในเอกสาร"""
    if not rel_path:
        return None
    import base64, mimetypes
    from flask import current_app
    from pathlib import Path
    full_path = Path(current_app.static_folder) / rel_path
    if not full_path.exists() or not full_path.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(full_path))
    if not mime:
        mime = 'image/png'
    with open(full_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f'data:{mime};base64,{b64}'


def _render_pdf_html(doc, doc_type, print_mode=False):
    """สร้าง HTML สำหรับ PDF/print โดยฝังรูปโลโก้และลายเซ็นเป็น data URL"""
    company = _get_company()
    return render_template('documents/pdf.html',
        doc=doc, doc_type=doc_type,
        type_info=Document.DOC_TYPES[doc_type],
        company=company,
        logo_data_url=_image_data_url(company.logo_path),
        signature_data_url=_image_data_url(company.signature_path),
        print_mode=print_mode)


def _validate_doc_type(doc_type):
    if doc_type not in Document.DOC_TYPES:
        abort(404)


# ============================================================
# Routes
# ============================================================
@bp.route('/<doc_type>/')
@login_required
def index(doc_type):
    _validate_doc_type(doc_type)
    q = (request.args.get('q') or '').strip()
    status = request.args.get('status') or ''

    query = Document.query.filter_by(doc_type=doc_type, company_id=current_company_id())
    if q:
        like = f'%{q}%'
        query = query.outerjoin(Customer).filter(or_(
            Document.number.ilike(like),
            Customer.name.ilike(like),
            Document.customer_snapshot_name.ilike(like),
            Document.project_name.ilike(like),
        ))
    if status:
        query = query.filter_by(status=status)

    docs = query.order_by(Document.issue_date.desc(), Document.id.desc()).all()
    return render_template('documents/list.html',
                           docs=docs, doc_type=doc_type,
                           q=q, status=status,
                           type_info=Document.DOC_TYPES[doc_type],
                           statuses=Document.STATUSES_BY_TYPE[doc_type])


@bp.route('/<doc_type>/new', methods=['GET', 'POST'])
@bp.route('/<doc_type>/<int:doc_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(doc_type, doc_id=None):
    _validate_doc_type(doc_type)

    if doc_id:
        doc = Document.query.get_or_404(doc_id)
        if doc.doc_type != doc_type:
            abort(404)
    else:
        doc = Document(doc_type=doc_type)

    if request.method == 'POST':
        try:
            customer_id = int(request.form.get('customer_id') or 0)
        except ValueError:
            customer_id = 0
        customer = Customer.query.get(customer_id)
        if not customer:
            flash('กรุณาเลือกลูกค้า', 'danger')
            return render_template('documents/form.html', **_form_context(doc, doc_type))

        doc.customer_id = customer.id
        doc.customer_snapshot_name = customer.name
        doc.customer_snapshot_tax_id = customer.tax_id
        doc.customer_snapshot_branch = customer.branch
        doc.customer_snapshot_address = customer.address
        doc.customer_snapshot_contact = customer.contact_person

        # Common fields
        for fld in ('issue_date', 'valid_until', 'due_date',
                    'delivery_date', 'tax_date', 'payment_date',
                    'approval_date'):
            val = request.form.get(fld)
            if val:
                try:
                    setattr(doc, fld, datetime.fromisoformat(val).date())
                except ValueError:
                    pass
            elif fld == 'issue_date':
                doc.issue_date = date.today()
            elif fld == 'approval_date':
                doc.approval_date = None  # ค่าว่าง = ใช้ issue_date

        doc.show_approval_date = bool(request.form.get('show_approval_date'))

        # === NEW v2.1: currency, category, tags ===
        doc.currency = (request.form.get('currency') or 'THB').upper()[:3]
        try:
            doc.currency_rate = float(request.form.get('currency_rate') or 1.0)
        except ValueError:
            doc.currency_rate = 1.0
        try:
            cat_id = int(request.form.get('category_id') or 0)
            doc.category_id = cat_id if cat_id > 0 else None
        except ValueError:
            doc.category_id = None
        # tags: รับเป็น string คั่นด้วยจุลภาค หรือ JSON array
        tags_raw = request.form.get('tags') or ''
        tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
        doc.tags = ', '.join(tags_list) if tags_list else None

        doc.reference = request.form.get('reference')
        doc.project_name = request.form.get('project_name')
        doc.note = request.form.get('note')
        doc.terms = request.form.get('terms')
        doc.price_includes_vat = bool(request.form.get('price_includes_vat'))
        try:
            doc.vat_rate = float(request.form.get('vat_rate') or 0)
        except ValueError:
            doc.vat_rate = 0.0
        doc.discount_amount = _money(request.form.get('discount_amount'))
        doc.status = request.form.get('status') or 'draft'

        # Type-specific fields
        if doc_type == 'DO':
            doc.delivery_address = request.form.get('delivery_address')
            doc.receiver_name = request.form.get('receiver_name')
        if doc_type == 'RC':
            doc.payment_method = request.form.get('payment_method')
            doc.payment_reference = request.form.get('payment_reference')
            doc.paid_amount = _money(request.form.get('paid_amount'))

        if not doc.id:
            doc.number = next_doc_number(doc_type)
            doc.created_by = current_user.id
            doc.company_id = current_company_id()
            db.session.add(doc)
            db.session.flush()

        # Replace items
        for it in list(doc.items):
            db.session.delete(it)
        db.session.flush()

        names  = request.form.getlist('item_name[]')
        codes  = request.form.getlist('item_code[]')
        descs  = request.form.getlist('item_description[]')
        units  = request.form.getlist('item_unit[]')
        qtys   = request.form.getlist('item_quantity[]')
        prices = request.form.getlist('item_unit_price[]')
        discs  = request.form.getlist('item_discount_percent[]')
        pids   = request.form.getlist('item_product_id[]')
        accts  = request.form.getlist('item_account[]')

        for i, name in enumerate(names):
            name = (name or '').strip()
            if not name:
                continue
            try:
                pid = int(pids[i]) if i < len(pids) and pids[i] else None
            except ValueError:
                pid = None
            db.session.add(DocumentItem(
                document_id=doc.id, position=i, product_id=pid,
                code=codes[i] if i < len(codes) else None,
                name=name,
                description=descs[i] if i < len(descs) else None,
                unit=units[i] if i < len(units) else 'ชิ้น',
                quantity=_decimal(qtys[i] if i < len(qtys) else 1, '1'),
                unit_price=_money(prices[i] if i < len(prices) else 0),
                discount_percent=float(_decimal(discs[i] if i < len(discs) else 0)),
                account_code=accts[i] if i < len(accts) else None,
            ))
        db.session.flush()
        doc = Document.query.get(doc.id)
        _calc_totals(doc)
        db.session.commit()
        # flash ละเอียด — บอกถ้าเป็นการอนุมัติ
        if doc.status == 'accepted' and doc_type == 'QT':
            flash(f'✓ อนุมัติใบเสนอราคา {doc.number} เรียบร้อย', 'success')
        elif doc.status == 'paid' and doc_type == 'IV':
            flash(f'✓ บันทึกการชำระเงิน {doc.number} เรียบร้อย', 'success')
        else:
            flash(f'บันทึก{Document.DOC_TYPES[doc_type]["name"]} {doc.number} เรียบร้อย', 'success')
        return redirect(url_for('documents.view', doc_type=doc_type, doc_id=doc.id))

    # GET
    if not doc.id:
        doc.issue_date = date.today()
        company = _get_company()
        doc.vat_rate = company.default_vat_rate
        doc.terms = company.default_terms
        if doc_type == 'QT':
            doc.valid_until = date.today() + timedelta(days=30)
        if doc_type == 'IV':
            doc.due_date = date.today() + timedelta(days=30)
        if doc_type == 'DO':
            doc.delivery_date = date.today()
        if doc_type == 'TI':
            doc.tax_date = date.today()
        if doc_type == 'RC':
            doc.payment_date = date.today()

    return render_template('documents/form.html', **_form_context(doc, doc_type))


def _currencies():
    from app.settings import CURRENCIES
    return CURRENCIES


def _form_context(doc, doc_type):
    """รวม context สำหรับ render form — รวมลูกค้าของ doc ด้วย แม้จะไม่อยู่ในบริษัทปัจจุบัน"""
    cid = current_company_id()
    customers = Customer.query.filter_by(is_active=True, company_id=cid).order_by(Customer.name).all()
    products  = Product.query.filter_by(is_active=True, company_id=cid).order_by(Product.name).all()
    categories = Category.query.filter_by(is_active=True, company_id=cid).order_by(Category.name).all()
    # ถ้า doc มีลูกค้าที่อยู่บริษัทอื่น → ใส่เพิ่มไว้ใน dropdown ด้วย
    if doc and doc.customer_id and not any(c.id == doc.customer_id for c in customers):
        extra = Customer.query.get(doc.customer_id)
        if extra:
            customers = customers + [extra]
    return dict(
        doc=doc, doc_type=doc_type,
        type_info=Document.DOC_TYPES[doc_type],
        statuses=Document.STATUSES_BY_TYPE[doc_type],
        company=_get_company(),
        all_customers=customers,
        all_products=products,
        all_categories=categories,
        currencies=_currencies(),
    )


@bp.route('/<doc_type>/<int:doc_id>')
@login_required
def view(doc_type, doc_id):
    _validate_doc_type(doc_type)
    doc = Document.query.get_or_404(doc_id)
    if doc.doc_type != doc_type:
        return redirect(url_for('documents.view', doc_type=doc.doc_type, doc_id=doc_id))
    return render_template('documents/view.html',
        doc=doc, doc_type=doc_type, type_info=Document.DOC_TYPES[doc_type],
        statuses=Document.STATUSES_BY_TYPE[doc_type],
        company=_get_company())


@bp.route('/<doc_type>/<int:doc_id>/pdf')
@login_required
def pdf(doc_type, doc_id):
    _validate_doc_type(doc_type)
    doc = Document.query.get_or_404(doc_id)
    if doc.doc_type != doc_type:
        abort(404)
    html = _render_pdf_html(doc, doc_type)
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=request.host_url).write_pdf()
        resp = make_response(pdf_bytes)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'inline; filename="{doc.number}.pdf"'
        return resp
    except Exception:
        return html


@bp.route('/<doc_type>/<int:doc_id>/print')
@login_required
def print_view(doc_type, doc_id):
    _validate_doc_type(doc_type)
    doc = Document.query.get_or_404(doc_id)
    if doc.doc_type != doc_type:
        abort(404)
    return _render_pdf_html(doc, doc_type, print_mode=True)


@bp.route('/<doc_type>/<int:doc_id>/status', methods=['POST'])
@login_required
def set_status(doc_type, doc_id):
    _validate_doc_type(doc_type)
    doc = Document.query.get_or_404(doc_id)
    if doc.doc_type != doc_type:
        abort(404)
    new_status = request.form.get('status')
    if new_status in Document.STATUSES_BY_TYPE[doc_type]:
        doc.status = new_status
        db.session.commit()
        flash('อัปเดตสถานะเรียบร้อย', 'success')
    return redirect(url_for('documents.view', doc_type=doc_type, doc_id=doc_id))


@bp.route('/<doc_type>/<int:doc_id>/delete', methods=['POST'])
@login_required
@permission_required('delete_documents')
def delete(doc_type, doc_id):
    _validate_doc_type(doc_type)
    doc = Document.query.get_or_404(doc_id)
    if doc.doc_type != doc_type:
        abort(404)
    db.session.delete(doc)
    db.session.commit()
    flash('ลบเอกสารเรียบร้อย', 'success')
    return redirect(url_for('documents.index', doc_type=doc_type))


@bp.route('/<doc_type>/<int:doc_id>/duplicate', methods=['POST'])
@login_required
def duplicate(doc_type, doc_id):
    _validate_doc_type(doc_type)
    src = Document.query.get_or_404(doc_id)
    if src.doc_type != doc_type:
        abort(404)
    return _clone_doc(src, doc_type, source_link=False)


@bp.route('/<doc_type>/<int:doc_id>/convert/<target_type>', methods=['POST'])
@login_required
def convert(doc_type, doc_id, target_type):
    """แปลงเอกสาร เช่น QT -> IV, IV -> RC"""
    _validate_doc_type(doc_type)
    _validate_doc_type(target_type)
    src = Document.query.get_or_404(doc_id)
    if src.doc_type != doc_type:
        abort(404)
    new_doc = _clone_doc(src, target_type, source_link=True, redirect_now=False)
    # Mark source as converted (สำหรับ QT)
    if doc_type == 'QT' and src.status not in ('rejected', 'expired'):
        src.status = 'converted'
        db.session.commit()
    flash(f'แปลงเป็น{Document.DOC_TYPES[target_type]["name"]} {new_doc.number} เรียบร้อย', 'success')
    return redirect(url_for('documents.edit', doc_type=target_type, doc_id=new_doc.id))


def _clone_doc(src, target_type, source_link=False, redirect_now=True):
    new = Document(
        doc_type=target_type,
        number=next_doc_number(target_type),
        customer_id=src.customer_id,
        company_id=src.company_id or current_company_id(),
        customer_snapshot_name=src.customer_snapshot_name,
        customer_snapshot_tax_id=src.customer_snapshot_tax_id,
        customer_snapshot_branch=src.customer_snapshot_branch,
        customer_snapshot_address=src.customer_snapshot_address,
        customer_snapshot_contact=src.customer_snapshot_contact,
        issue_date=date.today(),
        reference=src.reference,
        project_name=src.project_name,
        note=src.note,
        terms=src.terms,
        vat_rate=src.vat_rate,
        price_includes_vat=src.price_includes_vat,
        discount_amount=src.discount_amount,
        status='draft',
        created_by=current_user.id,
        source_doc_id=src.id if source_link else None,
    )
    # Type-specific date defaults
    if target_type == 'QT':
        new.valid_until = date.today() + timedelta(days=30)
    elif target_type == 'IV':
        new.due_date = date.today() + timedelta(days=30)
    elif target_type == 'DO':
        new.delivery_date = date.today()
    elif target_type == 'TI':
        new.tax_date = date.today()
    elif target_type == 'RC':
        new.payment_date = date.today()
        new.paid_amount = src.grand_total

    db.session.add(new)
    db.session.flush()
    for it in src.items:
        db.session.add(DocumentItem(
            document_id=new.id, position=it.position, product_id=it.product_id,
            code=it.code, name=it.name, description=it.description,
            unit=it.unit, quantity=it.quantity, unit_price=it.unit_price,
            discount_percent=it.discount_percent,
        ))
    db.session.flush()
    new = Document.query.get(new.id)
    _calc_totals(new)
    db.session.commit()

    if redirect_now:
        flash(f'ทำสำเนาเป็น {new.number}', 'success')
        return redirect(url_for('documents.edit', doc_type=target_type, doc_id=new.id))
    return new


# ============================================================
# Attachments
# ============================================================
def _attachment_dir(doc_id):
    """โฟลเดอร์ไฟล์แนบของเอกสาร"""
    from pathlib import Path
    from flask import current_app
    p = Path(current_app.root_path).parent / 'instance' / 'attachments' / str(doc_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


@bp.route('/<doc_type>/<int:doc_id>/attach', methods=['POST'])
@login_required
def attach(doc_type, doc_id):
    """อัปโหลดไฟล์แนบกับเอกสาร"""
    import time, mimetypes
    from werkzeug.utils import secure_filename
    from pathlib import Path
    _validate_doc_type(doc_type)
    doc = Document.query.get_or_404(doc_id)
    files = request.files.getlist('attachment')
    saved = 0
    for f in files:
        if not f or not f.filename:
            continue
        # ตรวจขนาด (current_app.config['MAX_CONTENT_LENGTH'] บังคับ Flask แล้ว)
        original = f.filename
        ext = Path(original).suffix.lower()
        safe = secure_filename(f'{int(time.time())}_{original}')[:200]
        if not safe:
            continue
        save_to = _attachment_dir(doc_id) / safe
        f.save(save_to)
        mime, _ = mimetypes.guess_type(original)
        size = save_to.stat().st_size
        att = DocumentAttachment(
            document_id=doc.id, filename=safe, original_name=original,
            mime_type=mime or 'application/octet-stream',
            file_size=size, uploaded_by=current_user.id
        )
        db.session.add(att)
        saved += 1
    db.session.commit()
    flash(f'อัปโหลด {saved} ไฟล์', 'success' if saved else 'warning')
    return redirect(url_for('documents.edit', doc_type=doc_type, doc_id=doc_id))


@bp.route('/<doc_type>/<int:doc_id>/attachments/<int:aid>')
@login_required
def attachment_download(doc_type, doc_id, aid):
    """ดาวน์โหลดไฟล์แนบ"""
    from flask import send_file
    att = DocumentAttachment.query.get_or_404(aid)
    if att.document_id != doc_id:
        abort(404)
    path = _attachment_dir(doc_id) / att.filename
    if not path.exists():
        flash('ไฟล์หาย', 'danger')
        return redirect(url_for('documents.view', doc_type=doc_type, doc_id=doc_id))
    return send_file(str(path), as_attachment=True, download_name=att.original_name,
                     mimetype=att.mime_type)


@bp.route('/<doc_type>/<int:doc_id>/attachments/<int:aid>/delete', methods=['POST'])
@login_required
def attachment_delete(doc_type, doc_id, aid):
    """ลบไฟล์แนบ"""
    att = DocumentAttachment.query.get_or_404(aid)
    if att.document_id != doc_id:
        abort(404)
    path = _attachment_dir(doc_id) / att.filename
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
    db.session.delete(att)
    db.session.commit()
    flash('ลบไฟล์แนบแล้ว', 'success')
    return redirect(url_for('documents.edit', doc_type=doc_type, doc_id=doc_id))
