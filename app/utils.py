"""
ThaiBill - Utility functions
"""
from datetime import datetime, date
from decimal import Decimal
from app import db


# ---------- Document numbering ----------

def next_doc_number(doc_type='QT', prefix=None):
    """
    Generate next document number e.g. QT-202601-0001
    """
    from app.models import DocumentSequence
    today = date.today()
    year_month = f'{today.year:04d}-{today.month:02d}'

    seq = DocumentSequence.query.filter_by(
        doc_type=doc_type, year_month=year_month
    ).first()
    if not seq:
        seq = DocumentSequence(doc_type=doc_type, year_month=year_month,
                               last_number=0)
        db.session.add(seq)

    seq.last_number += 1
    db.session.flush()

    p = prefix or doc_type
    ym = year_month.replace('-', '')
    return f'{p}-{ym}-{seq.last_number:04d}'


# ---------- Thai number to words ----------

_THAI_DIGITS = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่',
                'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า']
_THAI_PLACES = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน']


def _read_int_thai(num_str):
    """Read an integer string (<=7 digits) in Thai."""
    num_str = num_str.lstrip('0') or '0'
    if num_str == '0':
        return 'ศูนย์'
    if len(num_str) > 7:
        head = num_str[:-6]
        tail = num_str[-6:]
        return _read_int_thai(head) + 'ล้าน' + (_read_int_thai(tail) if tail.lstrip('0') else '')

    result = ''
    length = len(num_str)
    for i, ch in enumerate(num_str):
        digit = int(ch)
        place = length - i - 1
        if digit == 0:
            continue
        if place == 0 and digit == 1 and length > 1:
            result += 'เอ็ด'
        elif place == 1 and digit == 2:
            result += 'ยี่' + _THAI_PLACES[place]
        elif place == 1 and digit == 1:
            result += _THAI_PLACES[place]
        else:
            result += _THAI_DIGITS[digit] + _THAI_PLACES[place]
    return result


def baht_to_text(amount):
    """แปลงจำนวนเงินเป็นข้อความภาษาไทย เช่น 1234.56 -> หนึ่งพันสองร้อยสามสิบสี่บาทห้าสิบหกสตางค์"""
    try:
        amount = Decimal(str(amount))
    except Exception:
        return ''
    if amount < 0:
        return 'ลบ' + baht_to_text(-amount)

    int_part = int(amount)
    frac = int(round((amount - int_part) * 100))

    baht = _read_int_thai(str(int_part)) + 'บาท' if int_part > 0 else ''
    if frac == 0:
        return (baht or 'ศูนย์บาท') + 'ถ้วน'
    return (baht or '') + _read_int_thai(str(frac)) + 'สตางค์'


# ---------- Thai date format ----------

_THAI_MONTHS = ['', 'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
                'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
                'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
_THAI_MONTHS_SHORT = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.',
                      'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.',
                      'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']


def thai_date(d, short=False):
    if d is None:
        return ''
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except Exception:
            return d
    if isinstance(d, datetime):
        d = d.date()
    months = _THAI_MONTHS_SHORT if short else _THAI_MONTHS
    buddhist_year = d.year + 543
    return f'{d.day} {months[d.month]} {buddhist_year}'


# ---------- Format helpers ----------

def money(x, suffix=''):
    """format ตัวเลข + optional suffix (เช่น 'บาท', 'baht', 'THB')"""
    if x is None:
        return f'0.00 {suffix}'.strip()
    try:
        formatted = f'{Decimal(str(x)):,.2f}'
        return f'{formatted} {suffix}'.strip() if suffix else formatted
    except Exception:
        return str(x)


def qty(x):
    if x is None:
        return '0'
    try:
        d = Decimal(str(x))
        if d == d.to_integral_value():
            return f'{int(d):,}'
        return f'{d:,.3f}'.rstrip('0').rstrip('.')
    except Exception:
        return str(x)


# ---------- Register Jinja filters ----------

def register_template_filters(app):
    app.jinja_env.filters['money'] = money
    app.jinja_env.filters['qty'] = qty
    app.jinja_env.filters['thaidate'] = thai_date
    app.jinja_env.filters['baht_text'] = baht_to_text
    app.jinja_env.globals['today'] = date.today
    app.jinja_env.globals['now'] = datetime.now


# ---------- Multi-company helpers ----------
def current_company():
    """คืนค่า Company ที่ active อยู่ตาม session — ตรวจสิทธิ์ user ด้วย"""
    from flask import session
    from flask_login import current_user
    from app.models import Company

    # ถ้ายังไม่ login → ไม่มีบริษัท
    if not (current_user.is_authenticated):
        co = Company.query.filter_by(is_active=True).order_by(Company.id).first()
        return co

    cid = session.get('active_company_id')
    if cid:
        co = Company.query.get(cid)
        if co and co.is_active and current_user.can_access_company(cid):
            return co
        # ไม่มีสิทธิ์ → ล้าง session แล้ว fallback
        session.pop('active_company_id', None)

    # fallback: บริษัทแรกที่ user เข้าได้
    accessible = current_user.accessible_companies()
    if accessible:
        session['active_company_id'] = accessible[0].id
        return accessible[0]
    return None


def current_company_id():
    co = current_company()
    return co.id if co else None


# ---------- Permission decorators ----------
from functools import wraps
def admin_required(f):
    """ต้องเป็น admin เท่านั้น"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import flash, redirect, url_for
        from flask_login import current_user
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            flash('สิทธิ์ผู้ดูแลระบบเท่านั้น', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return wrapper


def permission_required(perm):
    """ตรวจ permission ระบุชื่อ เช่น 'delete_documents'"""
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import flash, redirect, url_for
            from flask_login import current_user
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not current_user.has_permission(perm):
                flash(f'ไม่มีสิทธิ์: {perm}', 'danger')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return deco
