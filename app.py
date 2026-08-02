import os
from flask import Flask, session, redirect, request
from config import Config
from extensions import db, login_manager, migrate
from models import Admin, Setting, Product
from translations import translate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload subdirectories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PRODUCT_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['BLOG_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['COA_UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
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

# Auto-initialize database tables, import real yan_zhen_peptide.sql data & seed admin user on Railway startup
with app.app_context():
    try:
        from import_helper import import_sql_file_if_empty
        import_sql_file_if_empty(app)
    except Exception as e:
        print(f"[Railway Init Warning] Auto-import notice: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
