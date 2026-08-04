import os
from flask import Flask, session, redirect, request
import pymysql
from sqlalchemy.engine.url import make_url
from config import Config
from extensions import db, login_manager, migrate, csrf
from models import Admin, Setting, Product
from translations import translate


def _ensure_mysql_database_exists(database_uri):
    url = make_url(database_uri)
    if not url.drivername.startswith('mysql'):
        raise RuntimeError(f"Unsupported database driver for this deployment: {url.drivername}")

    connection = pymysql.connect(
        host=url.host or 'localhost',
        user=url.username or 'root',
        password=url.password or '',
        port=url.port or 3306,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{url.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        connection.close()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure target MySQL database exists before SQLAlchemy initialization.
    _ensure_mysql_database_exists(app.config['SQLALCHEMY_DATABASE_URI'])

    # Ensure upload subdirectories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PRODUCT_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['BLOG_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['COA_UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'admin.login'

    # Global Context Processor for Templates (Multi-language & Cart Badge)
    @app.context_processor
    def inject_global_vars():
        lang = session.get('lang', 'en')
        
        # Calculate cart total count
        cart = session.get('cart', {})
        total_quantity = 0
        for qty in cart.values():
            try:
                total_quantity += int(qty)
            except (ValueError, TypeError):
                pass

        show_lang_modal = session.get('lang_modal_shown') is not True
        
        return dict(
            lang=lang,
            _ = lambda key: translate(key, lang),
            cart_total_count=total_quantity,
            show_lang_modal=show_lang_modal,
            company_name=Setting.get_val('company_name', 'Yan Zhen Peptide'),
            whatsapp_number=Setting.get_val('whatsapp_number', app.config.get('WHATSAPP_NUMBER', '85263294280')),
            business_email=Setting.get_val('business_email', app.config.get('BUSINESS_EMAIL', 'zhenyan640@gmail.com'))
        )

    # Register Blueprints
    from routes.main import main as main_bp
    from routes.admin import admin as admin_bp
    from routes.blog import blog as blog_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(blog_bp)

    @app.route('/secure-panel', defaults={'path': ''})
    @app.route('/secure-panel/<path:path>')
    def secure_panel_legacy_redirect(path):
        target = '/admin'
        if path:
            target = f"{target}/{path}"

        query_string = request.query_string.decode('utf-8')
        if query_string:
            target = f"{target}?{query_string}"

        return redirect(target, code=302)

    return app

app = create_app()

# Minimal startup verification only (no schema/data writes at startup).
with app.app_context():
    active_url = db.engine.url
    print(f"DB: {active_url.drivername}://{active_url.host}/{active_url.database}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
