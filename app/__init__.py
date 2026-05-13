"""
ThaiBill v2 - Flask Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from pathlib import Path
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'กรุณาเข้าสู่ระบบก่อนใช้งาน'
login_manager.login_message_category = 'warning'


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=False)

    from config import config_by_name
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config_by_name[config_name])

    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    (Path(app.root_path).parent / 'instance').mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Blueprints
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.customers import bp as customers_bp
    from app.products import bp as products_bp
    from app.documents import bp as documents_bp
    from app.settings import bp as settings_bp
    from app.categories import bp as categories_bp
    from app.users import bp as users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp,  url_prefix='/customers')
    app.register_blueprint(products_bp,   url_prefix='/products')
    app.register_blueprint(documents_bp,  url_prefix='/docs')
    app.register_blueprint(settings_bp,   url_prefix='/settings')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(users_bp,      url_prefix='/users')

    from app.utils import register_template_filters
    register_template_filters(app)

    from app.i18n import register_i18n
    register_i18n(app)

    @app.context_processor
    def inject_globals():
        from app.models import Company
        from app.settings import THEMES, get_display_settings
        from app.utils import current_company
        from flask_login import current_user
        try:
            company = current_company()
            # filter companies ตามสิทธิ์ของ user ปัจจุบัน
            if current_user.is_authenticated:
                all_companies = current_user.accessible_companies()
            else:
                all_companies = []
        except Exception:
            company = None; all_companies = []
        theme_name = (company.theme if company and company.theme else 'default')
        theme = THEMES.get(theme_name, THEMES['default'])
        return dict(company=company, theme=theme, theme_name=theme_name,
                    THEMES=THEMES,
                    all_companies=all_companies,
                    display=get_display_settings(company))

    with app.app_context():
        from app import models
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    return app
