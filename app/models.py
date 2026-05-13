"""
ThaiBill v2 - Database Models
Document model รองรับ 5 ประเภท: QT, IV, DO, TI, RC
"""
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


# Association: user ↔ company (สิทธิ์เข้าบริษัทไหนได้บ้าง)
user_companies = db.Table('user_companies',
    db.Column('user_id',    db.Integer, db.ForeignKey('users.id'),    primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('company.id'),  primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    full_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')  # 'admin' หรือ 'user'
    permissions = db.Column(db.Text)  # JSON overrides (เฉพาะ role=user)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # บริษัทที่ user คนนี้เข้าได้ (admin จะเข้าได้ทุกบริษัทโดย default ไม่ต้อง add ที่นี่)
    companies = db.relationship('Company', secondary=user_companies, backref='users')

    # ค่า default permissions ตาม role
    DEFAULT_USER_PERMS = {
        'view_documents': True,  'create_documents': True,
        'edit_documents': True,  'delete_documents': False,
        'view_customers': True,  'create_customers': True,
        'edit_customers': True,  'delete_customers': False,
        'view_products':  True,  'create_products':  True,
        'edit_products':  True,  'delete_products':  False,
        'view_categories': True, 'manage_categories': False,
        'view_reports':    True,
        'view_settings':   False, 'manage_settings':  False,
        'manage_users':    False, 'manage_companies': False,
    }
    ALL_PERMS = list(DEFAULT_USER_PERMS.keys())

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)
    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def is_admin(self):
        return self.role == 'admin'

    def get_permissions(self):
        """ดึง permissions dict — admin ได้ทุกอย่าง, user merge กับ defaults"""
        if self.role == 'admin':
            return {k: True for k in self.ALL_PERMS}
        import json
        perms = dict(self.DEFAULT_USER_PERMS)
        if self.permissions:
            try:
                perms.update(json.loads(self.permissions))
            except Exception:
                pass
        return perms

    def has_permission(self, key):
        return self.get_permissions().get(key, False)

    def accessible_companies(self):
        """คืน list บริษัทที่ user คนนี้เข้าได้ (admin เข้าได้ทุกบริษัท)"""
        from app.models import Company
        if self.is_admin():
            return Company.query.filter_by(is_active=True).order_by(Company.id).all()
        return [c for c in self.companies if c.is_active]

    def can_access_company(self, company_id):
        if self.is_admin():
            return True
        return any(c.id == company_id for c in self.companies)


class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default='บริษัทของฉัน จำกัด')
    branch = db.Column(db.String(100), default='สำนักงานใหญ่')
    tax_id = db.Column(db.String(20))
    address = db.Column(db.Text)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    logo_path = db.Column(db.String(255))
    signature_path = db.Column(db.String(255))
    bank_info = db.Column(db.Text)
    default_vat_rate = db.Column(db.Float, default=7.0)
    default_terms = db.Column(db.Text,
        default='ยืนราคา 30 วัน\nเงื่อนไขการชำระเงิน: เครดิต 30 วัน')
    # Preferences
    theme = db.Column(db.String(30), default='default')
    display_settings = db.Column(db.Text)  # JSON: ตั้งค่าการแสดงผลใน form/PDF
    # Google Drive
    gdrive_folder_id = db.Column(db.String(100))
    gdrive_credentials_filename = db.Column(db.String(255))
    # Multi-company support
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(120))
    tax_id = db.Column(db.String(20))
    branch = db.Column(db.String(100), default='สำนักงานใหญ่')
    address = db.Column(db.Text)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    customer_type = db.Column(db.String(20), default='company')
    credit_days = db.Column(db.Integer, default=30)
    note = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), default='ชิ้น')
    price = db.Column(db.Numeric(14, 2), default=0)
    cost = db.Column(db.Numeric(14, 2), default=0)
    product_type = db.Column(db.String(20), default='goods')
    vat_type = db.Column(db.String(20), default='exclude')
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Document(db.Model):
    """Generic document - QT/IV/DO/TI/RC"""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(4), nullable=False, index=True)
    number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), index=True)

    issue_date    = db.Column(db.Date, default=date.today, nullable=False)
    valid_until   = db.Column(db.Date)   # QT
    due_date      = db.Column(db.Date)   # IV
    delivery_date = db.Column(db.Date)   # DO
    tax_date      = db.Column(db.Date)   # TI
    payment_date  = db.Column(db.Date)   # RC

    reference = db.Column(db.String(100))
    project_name = db.Column(db.String(200))

    customer_snapshot_name = db.Column(db.String(200))
    customer_snapshot_tax_id = db.Column(db.String(20))
    customer_snapshot_branch = db.Column(db.String(100))
    customer_snapshot_address = db.Column(db.Text)
    customer_snapshot_contact = db.Column(db.String(120))

    subtotal = db.Column(db.Numeric(14, 2), default=0)
    discount_amount = db.Column(db.Numeric(14, 2), default=0)
    after_discount = db.Column(db.Numeric(14, 2), default=0)
    vat_rate = db.Column(db.Float, default=7.0)
    vat_amount = db.Column(db.Numeric(14, 2), default=0)
    grand_total = db.Column(db.Numeric(14, 2), default=0)
    price_includes_vat = db.Column(db.Boolean, default=False)

    delivery_address = db.Column(db.Text)
    receiver_name = db.Column(db.String(120))

    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    paid_amount = db.Column(db.Numeric(14, 2))

    # === NEW v2.1 fields ===
    # สกุลเงิน
    currency = db.Column(db.String(3), default='THB')      # ISO 4217
    currency_rate = db.Column(db.Numeric(14, 6), default=1.0)  # vs THB
    # กลุ่มจัดประเภท
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    # แท็ก (comma-separated เก็บง่าย ค้นง่าย)
    tags = db.Column(db.String(500))

    # Signature/approval block
    show_approval_date = db.Column(db.Boolean, default=True)
    approval_date = db.Column(db.Date)  # ถ้า null จะใช้ issue_date

    note = db.Column(db.Text)
    terms = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')

    source_doc_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    source_doc = db.relationship('Document', remote_side='Document.id',
                                 backref='derived_docs')

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('DocumentItem', backref='document',
                            lazy='joined', cascade='all, delete-orphan',
                            order_by='DocumentItem.position')
    customer = db.relationship('Customer', backref='documents')

    DOC_TYPES = {
        'QT': {'name': 'ใบเสนอราคา',    'name_en': 'Quotation',      'color': 'primary', 'icon': 'fa-file-invoice'},
        'IV': {'name': 'ใบแจ้งหนี้',     'name_en': 'Invoice',        'color': 'warning', 'icon': 'fa-file-invoice-dollar'},
        'DO': {'name': 'ใบส่งของ',      'name_en': 'Delivery Order', 'color': 'info',    'icon': 'fa-truck'},
        'TI': {'name': 'ใบกำกับภาษี',   'name_en': 'Tax Invoice',    'color': 'success', 'icon': 'fa-receipt'},
        'RC': {'name': 'ใบเสร็จรับเงิน', 'name_en': 'Receipt',        'color': 'danger',  'icon': 'fa-money-bill-wave'},
    }

    STATUS_LABELS = {
        'draft':     ('ร่าง',            'secondary'),
        'sent':      ('ส่งให้ลูกค้า',     'primary'),
        'accepted':  ('ลูกค้าตอบรับ',     'success'),
        'rejected':  ('ลูกค้าปฏิเสธ',     'danger'),
        'expired':   ('หมดอายุ',          'warning'),
        'converted': ('ออกเอกสารแล้ว',   'info'),
        'paid':      ('ชำระแล้ว',          'success'),
        'partial':   ('ชำระบางส่วน',      'warning'),
        'overdue':   ('เกินกำหนด',         'danger'),
        'shipped':   ('ส่งสินค้าแล้ว',     'info'),
        'delivered': ('ส่งถึงปลายทาง',    'success'),
        'issued':    ('ออกแล้ว',           'success'),
        'void':      ('ยกเลิก',            'danger'),
    }

    STATUSES_BY_TYPE = {
        'QT': ['draft', 'sent', 'accepted', 'rejected', 'expired', 'converted'],
        'IV': ['draft', 'sent', 'partial', 'paid', 'overdue', 'void'],
        'DO': ['draft', 'shipped', 'delivered', 'void'],
        'TI': ['draft', 'issued', 'void'],
        'RC': ['draft', 'issued', 'void'],
    }

    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, 'secondary'))

    def type_info(self):
        return self.DOC_TYPES.get(self.doc_type,
            {'name': '?', 'color': 'secondary', 'icon': 'fa-file'})


class DocumentItem(db.Model):
    __tablename__ = 'document_items'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    position = db.Column(db.Integer, default=0)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    code = db.Column(db.String(40))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20))
    quantity = db.Column(db.Numeric(14, 3), default=1)
    unit_price = db.Column(db.Numeric(14, 2), default=0)
    discount_percent = db.Column(db.Float, default=0)
    line_total = db.Column(db.Numeric(14, 2), default=0)
    # บัญชี (chart of accounts code)
    account_code = db.Column(db.String(50))


class Category(db.Model):
    """กลุ่มจัดประเภทเอกสาร"""
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(20), default='#6366f1')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), index=True)

    documents = db.relationship('Document', backref='category')


class DocumentAttachment(db.Model):
    """ไฟล์แนบของเอกสาร"""
    __tablename__ = 'document_attachments'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)       # filename ในระบบ
    original_name = db.Column(db.String(255), nullable=False)  # ชื่อเดิมจาก user
    file_size = db.Column(db.Integer, default=0)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    document = db.relationship('Document', backref=db.backref('attachments', cascade='all, delete-orphan'))


class DocumentSequence(db.Model):
    __tablename__ = 'document_sequences'
    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(20), nullable=False)
    year_month = db.Column(db.String(7), nullable=False)
    last_number = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint('doc_type', 'year_month', name='uq_doc_seq'),)


class AppSetting(db.Model):
    """Key-value system settings (OAuth credentials, feature flags ฯลฯ)"""
    __tablename__ = 'app_settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_value(cls, key, default=None):
        s = cls.query.get(key)
        return s.value if s and s.value is not None and s.value != '' else default

    @classmethod
    def set_value(cls, key, value):
        s = cls.query.get(key)
        if not s:
            s = cls(key=key); db.session.add(s)
        s.value = value if value is not None else ''
        s.updated_at = datetime.utcnow()
        return s

    @classmethod
    def get_bool(cls, key, default=False):
        v = cls.get_value(key)
        if v is None: return default
        return v.lower() in ('1','true','yes','on')
