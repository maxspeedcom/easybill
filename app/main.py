"""
ThaiBill v2 - Main routes (dashboard)
"""
from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from sqlalchemy import func
from app import db
from app.utils import current_company_id
from app.models import Document, Customer, Product

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))


@bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)
    cid = current_company_id()

    # Counts by doc type
    counts = {}
    month_totals = {}
    for dt in ('QT', 'IV', 'DO', 'TI', 'RC'):
        counts[dt] = Document.query.filter_by(doc_type=dt, company_id=cid).count()
        month_totals[dt] = db.session.query(
            func.coalesce(func.sum(Document.grand_total), 0)
        ).filter(Document.doc_type == dt,
                 Document.company_id == cid,
                 Document.issue_date >= month_start).scalar() or 0

    # KPI
    total_customers = Customer.query.filter_by(is_active=True, company_id=cid).count()
    total_products  = Product.query.filter_by(is_active=True, company_id=cid).count()

    # Quotation pending = ยังไม่ตอบรับ
    qt_pending = Document.query.filter(
        Document.doc_type == 'QT',
        Document.company_id == cid,
        Document.status.in_(['draft', 'sent'])
    ).count()
    # Invoices unpaid
    iv_unpaid_total = db.session.query(
        func.coalesce(func.sum(Document.grand_total), 0)
    ).filter(
        Document.doc_type == 'IV',
        Document.company_id == cid,
        Document.status.in_(['draft', 'sent', 'partial', 'overdue'])
    ).scalar() or 0
    # Receipts this month
    rc_month_total = month_totals['RC']

    # Recent documents (เฉพาะบริษัทปัจจุบัน)
    recent = Document.query.filter_by(company_id=cid).order_by(Document.created_at.desc()).limit(8).all()

    # 14-day chart
    chart_labels, chart_values = [], []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        s = db.session.query(
            func.coalesce(func.sum(Document.grand_total), 0)
        ).filter(Document.issue_date == d,
                 Document.doc_type == 'IV',
                 Document.company_id == cid).scalar() or 0
        chart_labels.append(d.strftime('%d/%m'))
        chart_values.append(float(s))

    return render_template(
        'dashboard.html',
        counts=counts, month_totals=month_totals,
        total_customers=total_customers, total_products=total_products,
        qt_pending=qt_pending,
        iv_unpaid_total=iv_unpaid_total,
        rc_month_total=rc_month_total,
        recent=recent,
        chart_labels=chart_labels, chart_values=chart_values,
        doc_types=Document.DOC_TYPES,
    )
