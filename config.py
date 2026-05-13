"""
ThaiBill - Configuration
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-please')

    # Database (SQLite by default; เปลี่ยนเป็น PostgreSQL ได้)
    db_path = BASE_DIR / 'instance' / 'thaibill.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{db_path}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days

    # Company defaults (จะ override ด้วย Settings ใน DB)
    COMPANY_NAME = 'บริษัทของฉัน จำกัด'
    COMPANY_ADDRESS = ''
    COMPANY_TAX_ID = ''
    COMPANY_PHONE = ''

    # VAT default
    DEFAULT_VAT_RATE = 7.0

    # Timezone
    TIMEZONE = 'Asia/Bangkok'

    # File uploads (อยู่ใน app/static/uploads/ เพื่อให้ nginx serve ตรงๆ ได้)
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads'
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}


class ProductionConfig(Config):
    DEBUG = False
    # ตั้งเป็น True เฉพาะเมื่อเข้าผ่าน HTTPS เท่านั้น
    # ตั้งค่าผ่าน env var: SESSION_COOKIE_SECURE=1 (HTTPS) หรือ 0 (HTTP, default)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    DEBUG = True


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
