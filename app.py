import os
from flask import Flask, session, redirect, request
import pymysql
from sqlalchemy.engine.url import make_url
from sqlalchemy import inspect, text, func
from flask_migrate import stamp, upgrade
from config import Config
from extensions import db, login_manager, migrate, csrf
from models import Admin, Setting, Product, ContactInquiry, OrderRecord
from translations import translate


def _ensure_mysql_database_exists(database_uri):
    url = make_url(database_uri)
    if not url.drivername.startswith('mysql'):
        return

    try:
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
    except Exception as exc:
        print(f"Notice: MySQL connection check skipped: {exc}")


def repair_and_upgrade_migrations(app):
    """Repair Alembic revision drift safely, then apply forward migrations.

    Scenario handled: DB already has legacy tables (e.g. admins) but alembic_version
    is behind and tries to re-run older migrations.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        admins_exists = inspector.has_table('admins')
        alembic_exists = inspector.has_table('alembic_version')

        current_revision = None
        if alembic_exists:
            row = db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            current_revision = row[0] if row else None

        # If schema already includes legacy objects but Alembic head is behind,
        # stamp to the last known safe pre-contact-inquiries revision.
        if admins_exists and current_revision in (None, 'e59a90072f49', '7c5d3c8e2f41'):
            app.logger.warning(
                "Alembic drift detected (revision=%s). Stamping to c3d9ab4f6d21 before upgrade.",
                current_revision,
            )
            stamp(directory='migrations', revision='c3d9ab4f6d21')

        # Apply any newer migrations only.
        upgrade(directory='migrations')

        # Final safety checks.
        if not inspect(db.engine).has_table('contact_inquiries'):
            raise RuntimeError('Migration repair finished but contact_inquiries table is missing.')
        order_columns = {column['name'] for column in inspect(db.engine).get_columns('order_records')}
        if 'status' not in order_columns:
            raise RuntimeError('Migration repair finished but order_records.status is missing.')

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
        is_admin_request = request.blueprint == 'admin' or (request.endpoint or '').startswith('admin.')
        
        # Calculate cart total count
        cart = session.get('cart', {})
        total_quantity = 0
        for qty in cart.values():
            try:
                total_quantity += int(qty)
            except (ValueError, TypeError):
                pass

        show_lang_modal = session.get('lang_modal_shown') is not True
        unread_inquiries_count = 0
        pending_orders_count = 0
        in_progress_orders_count = 0

        if is_admin_request:
            unread_inquiries_count = ContactInquiry.query.filter_by(is_read=False).count()
            order_status_counts = dict(
                db.session.query(OrderRecord.status, func.count(OrderRecord.id))
                .group_by(OrderRecord.status)
                .all()
            )
            pending_orders_count = order_status_counts.get('Pending', 0)
            in_progress_orders_count = order_status_counts.get('In Progress', 0)
        
        return dict(
            lang=lang,
            _ = lambda key: translate(key, lang),
            cart_total_count=total_quantity,
            show_lang_modal=show_lang_modal,
            unread_inquiries_count=unread_inquiries_count,
            pending_orders_count=pending_orders_count,
            in_progress_orders_count=in_progress_orders_count,
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

    @app.cli.command('db-repair-upgrade')
    def db_repair_upgrade_command():
        """Repair Alembic drift and apply forward migrations safely."""
        repair_and_upgrade_migrations(app)
        print('Migration repair+upgrade complete.')

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

# Optional production-safe migration repair/upgrade on startup (Railway or explicit opt-in).
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('AUTO_MIGRATE_ON_STARTUP') == '1':
    repair_and_upgrade_migrations(app)

# Minimal startup verification only (no schema/data writes at startup).
with app.app_context():
    active_url = db.engine.url
    print(f"DB: {active_url.drivername}://{active_url.host}/{active_url.database}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
