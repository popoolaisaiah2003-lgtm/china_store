import os
from flask import Flask, session
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
            whatsapp_number=Setting.get_val('whatsapp_number', app.config.get('WHATSAPP_NUMBER', '2348181882418'))
        )

    # Register Blueprints
    from routes.main import main as main_bp
    from routes.admin import admin as admin_bp
    from routes.blog import blog as blog_bp
    from routes.reviews import reviews as reviews_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(reviews_bp)

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed default Admin 'isaiah' if no admin account exists in 'admins' table
        if not Admin.query.filter_by(username='isaiah').first():
            admin_user = Admin(username='isaiah', email='admin@yanzhen.com')
            admin_user.set_password('ChangeMe123!')
            db.session.add(admin_user)
            db.session.commit()
            print("[AntiGravity Init] Created Admin 'isaiah' (admin@yanzhen.com) with password 'ChangeMe123!'")

    app.run(host='0.0.0.0', port=8080, debug=True)
