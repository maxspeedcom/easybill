#!/usr/bin/env python3
"""
EasyBill v1 → v2 Migration
- เปลี่ยน table quotations → documents (เพิ่ม column doc_type, ฟิลด์ใหม่)
- เปลี่ยน table quotation_items → document_items (เปลี่ยน column quotation_id → document_id)
- คงข้อมูลเดิมไว้ทั้งหมด (เอกสารเก่าจะเป็น doc_type='QT')

Usage:
  cd /opt/thaibill
  ./venv/bin/python scripts/migrate_v1_to_v2.py
"""
import sqlite3
import shutil
import sys
from pathlib import Path
from datetime import datetime


def _ensure_extra_columns(c):
    """ตรวจและเพิ่ม column ที่อาจขาดในตารางที่มีอยู่แล้ว (idempotent)"""
    # query current tables
    tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    # documents
    c.execute("PRAGMA table_info(documents)")
    doc_cols = {r[1] for r in c.fetchall()}
    for name, defn in [
        ('doc_type',          "VARCHAR(4) NOT NULL DEFAULT 'QT'"),
        ('due_date',          'DATE'),
        ('delivery_date',     'DATE'),
        ('tax_date',          'DATE'),
        ('payment_date',      'DATE'),
        ('delivery_address',  'TEXT'),
        ('receiver_name',     'VARCHAR(120)'),
        ('payment_method',    'VARCHAR(50)'),
        ('payment_reference', 'VARCHAR(100)'),
        ('paid_amount',       'NUMERIC(14,2)'),
        ('source_doc_id',     'INTEGER'),
        ('show_approval_date', 'BOOLEAN DEFAULT 1'),
        ('approval_date',     'DATE'),
        ('currency',          "VARCHAR(3) DEFAULT 'THB'"),
        ('currency_rate',     'NUMERIC(14,6) DEFAULT 1.0'),
        ('category_id',       'INTEGER'),
        ('tags',              'VARCHAR(500)'),
    ]:
        if name not in doc_cols:
            c.execute(f'ALTER TABLE documents ADD COLUMN {name} {defn}')
            print(f'  ✓ เพิ่ม column documents.{name}')

    # document_items
    if 'document_items' in tables:
        c.execute("PRAGMA table_info(document_items)")
        it_cols = {r[1] for r in c.fetchall()}
        for name, defn in [('account_code', 'VARCHAR(50)')]:
            if name not in it_cols:
                c.execute(f'ALTER TABLE document_items ADD COLUMN {name} {defn}')
                print(f'  ✓ เพิ่ม column document_items.{name}')

    # categories
    if 'categories' not in tables:
        c.execute('''
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                color VARCHAR(20) DEFAULT '#6366f1',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('  ✓ สร้างตาราง categories')

    # document_attachments
    if 'document_attachments' not in tables:
        c.execute('''
            CREATE TABLE document_attachments (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                filename VARCHAR(255) NOT NULL,
                original_name VARCHAR(255) NOT NULL,
                file_size INTEGER DEFAULT 0,
                mime_type VARCHAR(100),
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                uploaded_by INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
        ''')
        print('  ✓ สร้างตาราง document_attachments')

    # users
    if 'users' in tables:
        c.execute("PRAGMA table_info(users)")
        u_cols = {r[1] for r in c.fetchall()}
        for name, defn in [
            ('permissions', 'TEXT'),
            ('last_login',  'DATETIME'),
        ]:
            if name not in u_cols:
                c.execute(f'ALTER TABLE users ADD COLUMN {name} {defn}')
                print(f'  ✓ เพิ่ม column users.{name}')

    # company
    c.execute("PRAGMA table_info(company)")
    co_cols = {r[1] for r in c.fetchall()}
    for name, defn in [
        ('logo_path',                   'VARCHAR(255)'),
        ('signature_path',              'VARCHAR(255)'),
        ('theme',                       "VARCHAR(30) DEFAULT 'default'"),
        ('gdrive_folder_id',            'VARCHAR(100)'),
        ('gdrive_credentials_filename', 'VARCHAR(255)'),
        ('display_settings',            'TEXT'),
        ('is_active',                   'BOOLEAN DEFAULT 1'),
        ('created_at',                  'DATETIME'),
    ]:
        if name not in co_cols:
            c.execute(f'ALTER TABLE company ADD COLUMN {name} {defn}')
            print(f'  ✓ เพิ่ม column company.{name}')

    # === Multi-company: เพิ่ม company_id ในตารางหลัก + backfill ===
    row = c.execute('SELECT id FROM company ORDER BY id LIMIT 1').fetchone()
    first_co_id = row[0] if row else None
    if first_co_id:
        for tbl in ['documents', 'customers', 'products', 'categories']:
            if tbl in tables:
                c.execute(f"PRAGMA table_info({tbl})")
                tcols = {r[1] for r in c.fetchall()}
                if 'company_id' not in tcols:
                    c.execute(f'ALTER TABLE {tbl} ADD COLUMN company_id INTEGER')
                    c.execute(f'UPDATE {tbl} SET company_id = ? WHERE company_id IS NULL', (first_co_id,))
                    print(f'  ✓ เพิ่ม {tbl}.company_id + backfill = {first_co_id}')

    # === App settings (key-value: OAuth credentials, feature flags) ===
    if 'app_settings' not in tables:
        c.execute('''
            CREATE TABLE app_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('  ✓ สร้างตาราง app_settings')

    # === User ↔ Company access (many-to-many) ===
    if 'user_companies' not in tables:
        c.execute('''
            CREATE TABLE user_companies (
                user_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, company_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (company_id) REFERENCES company(id)
            )
        ''')
        # Backfill: ทุก user (ที่เป็น role=user) ได้สิทธิ์เข้าบริษัทแรก
        # admin ไม่ต้อง backfill เพราะ helper จะคืนทุกบริษัทอยู่แล้ว
        c.execute("""
            INSERT INTO user_companies (user_id, company_id)
            SELECT u.id, ? FROM users u
            WHERE u.role = 'user'
        """, (first_co_id,))
        print(f'  ✓ สร้างตาราง user_companies + backfill user → company {first_co_id}')


def main():
    base = Path(__file__).resolve().parent.parent
    db_path = base / 'instance' / 'thaibill.db'

    if not db_path.exists():
        print(f'❌ ไม่พบฐานข้อมูล: {db_path}')
        print('   ยังไม่ต้องทำ migration เพราะนี่คือการติดตั้งใหม่ — Flask จะสร้างตารางให้เอง')
        return 0

    # Backup
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = db_path.with_suffix(f'.db.backup-{ts}')
    shutil.copy2(db_path, backup)
    print(f'✅ สำรอง DB ไว้ที่: {backup}')

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ตรวจว่าตอนนี้อยู่ schema ไหน
    tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    has_quotations = 'quotations' in tables
    has_documents = 'documents' in tables

    if not has_quotations and not has_documents:
        print('⚠️  ไม่พบทั้งตาราง quotations และ documents — รันแอปสักครั้งเพื่อสร้าง schema ใหม่')
        return 0

    if has_documents and not has_quotations:
        print('ℹ️  ฐานข้อมูลเป็น schema v2 อยู่แล้ว — ตรวจ column เพิ่มเติม')
        _ensure_extra_columns(c)
        conn.commit()
        count = c.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        print(f'✅ เสร็จ — มีเอกสาร {count} รายการ')
        conn.close()
        return 0

    print('▶ เริ่ม migrate v1 → v2 …')

    # 1) Rename quotations → documents (ตรวจ column ทีละตัว)
    c.execute("PRAGMA table_info(quotations)")
    cols = {r[1] for r in c.fetchall()}

    # SQLite รองรับ RENAME TABLE ตั้งแต่ 3.0
    c.execute('ALTER TABLE quotations RENAME TO documents')
    print('  ✓ เปลี่ยนชื่อ quotations → documents')

    # 2) เพิ่ม column ใหม่
    new_columns = [
        ("doc_type", "VARCHAR(4) NOT NULL DEFAULT 'QT'"),
        ("due_date", "DATE"),
        ("delivery_date", "DATE"),
        ("tax_date", "DATE"),
        ("payment_date", "DATE"),
        ("delivery_address", "TEXT"),
        ("receiver_name", "VARCHAR(120)"),
        ("payment_method", "VARCHAR(50)"),
        ("payment_reference", "VARCHAR(100)"),
        ("paid_amount", "NUMERIC(14, 2)"),
        ("source_doc_id", "INTEGER"),
    ]
    for name, defn in new_columns:
        if name not in cols:
            c.execute(f'ALTER TABLE documents ADD COLUMN {name} {defn}')
            print(f'  ✓ เพิ่ม column documents.{name}')

    # 3) อัปเดต doc_type='QT' สำหรับเอกสารเก่า (เผื่อมี NULL)
    c.execute("UPDATE documents SET doc_type='QT' WHERE doc_type IS NULL OR doc_type = ''")

    # 4) Rename quotation_items → document_items + เปลี่ยน column
    if 'quotation_items' in tables and 'document_items' not in tables:
        # SQLite 3.25+ รองรับ RENAME COLUMN
        try:
            c.execute('ALTER TABLE quotation_items RENAME TO document_items')
            c.execute('ALTER TABLE document_items RENAME COLUMN quotation_id TO document_id')
            print('  ✓ เปลี่ยนชื่อ quotation_items → document_items (พร้อม column document_id)')
        except sqlite3.OperationalError as e:
            # Fallback: สร้างใหม่และคัดลอกข้อมูล
            print(f'  ⚠ SQLite rename column ไม่ได้ ({e}) — สร้างตารางใหม่')
            c.execute('''
                CREATE TABLE document_items (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    position INTEGER DEFAULT 0,
                    product_id INTEGER,
                    code VARCHAR(40),
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    unit VARCHAR(20),
                    quantity NUMERIC(14, 3) DEFAULT 1,
                    unit_price NUMERIC(14, 2) DEFAULT 0,
                    discount_percent FLOAT DEFAULT 0,
                    line_total NUMERIC(14, 2) DEFAULT 0
                )
            ''')
            c.execute('''
                INSERT INTO document_items
                  (id, document_id, position, product_id, code, name, description,
                   unit, quantity, unit_price, discount_percent, line_total)
                SELECT id, quotation_id, position, product_id, code, name, description,
                       unit, quantity, unit_price, discount_percent, line_total
                FROM quotation_items
            ''')
            c.execute('DROP TABLE quotation_items')
            print('  ✓ ย้ายข้อมูลและสร้างตาราง document_items ใหม่')

    # 5) ตาราง document_sequences ใช้ชื่อเดิมอยู่แล้ว แค่ตรวจว่ามี
    if 'document_sequences' not in tables:
        c.execute('''
            CREATE TABLE IF NOT EXISTS document_sequences (
                id INTEGER PRIMARY KEY,
                doc_type VARCHAR(20) NOT NULL,
                year_month VARCHAR(7) NOT NULL,
                last_number INTEGER DEFAULT 0,
                UNIQUE(doc_type, year_month)
            )
        ''')
        print('  ✓ สร้างตาราง document_sequences')

    # 6) เพิ่ม column ใหม่ใน company (logo_path, signature_path)
    _ensure_extra_columns(c)

    conn.commit()

    # นับเอกสารหลัง migrate
    count = c.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    print(f'\n✅ Migration สำเร็จ — มีเอกสารทั้งหมด {count} รายการในระบบ')
    print(f'   หากมีปัญหาให้คืนค่า: cp {backup} {db_path}')

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
