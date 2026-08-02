import os
from extensions import db
from sqlalchemy import text


def _split_sql_statements(sql_content):
    statements = []
    buf = []
    in_single_quote = False
    in_double_quote = False
    escaped = False

    for ch in sql_content:
        buf.append(ch)

        if escaped:
            escaped = False
            continue

        if ch == '\\':
            escaped = True
            continue

        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue

        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue

        if ch == ';' and not in_single_quote and not in_double_quote:
            statement = ''.join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []

    trailing = ''.join(buf).strip()
    if trailing:
        statements.append(trailing)

    return statements


def _execute_insert_statements(statements):
    inserted_statements = 0
    for stmt in statements:
        normalized = stmt.strip()
        if not normalized.upper().startswith('INSERT INTO'):
            continue

        try:
            db.session.execute(text(normalized))
            db.session.commit()
            inserted_statements += 1
        except Exception:
            db.session.rollback()

    return inserted_statements


def _ensure_mots_c_blog_image(app):
    from models import BlogPost

    blog_upload_folder = app.config['BLOG_UPLOAD_FOLDER']
    os.makedirs(blog_upload_folder, exist_ok=True)

    expected_filename = 'mots-c.jpg'
    legacy_filenames = ['blog_mots-c.jpeg', 'mots-c.jpeg']

    expected_path = os.path.join(blog_upload_folder, expected_filename)
    if not os.path.exists(expected_path):
        for legacy_name in legacy_filenames:
            legacy_path = os.path.join(blog_upload_folder, legacy_name)
            if os.path.exists(legacy_path):
                with open(legacy_path, 'rb') as src, open(expected_path, 'wb') as dst:
                    dst.write(src.read())
                break

    post = BlogPost.query.filter_by(slug='mots-c').first()
    if post and post.image_filename != expected_filename and os.path.exists(expected_path):
        post.image_filename = expected_filename
        db.session.commit()

def import_sql_file_if_empty(app):
    with app.app_context():
        try:
            db.create_all()
        except Exception as create_err:
            print(f"[Database Init] create_all notice: {create_err}")

        current_count = 0
        try:
            from models import Product
            current_count = Product.query.count()
            if current_count >= 170:
                print(f"[Database Import] Table products already has {current_count} items. Skipping product backfill import.")
        except Exception:
            current_count = 0

        sql_file_path = os.path.join(app.root_path, 'yan_zhen_peptide.sql')
        if not os.path.exists(sql_file_path):
            print(f"[Database Import Warning] {sql_file_path} file not found.")
            _ensure_mots_c_blog_image(app)
            return

        if current_count < 170:
            print(f"[Database Import] Importing real data from {sql_file_path} into {db.engine.url.drivername} database...")
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            statements = _split_sql_statements(sql_content)
            inserted_statements = _execute_insert_statements(statements)
            print(f"[Database Import Success] Executed {inserted_statements} INSERT statements!")

        # Re-verify product count and seed admin user
        try:
            from models import Product, Admin
            count = Product.query.count()
            print(f"[Database Import Verification] Final Product count in DB: {count}")
            
            admin = Admin.query.filter_by(username='isaiah').first()
            if not admin:
                admin = Admin(username='isaiah', email='admin@yanzhen.com')
                admin.set_password('ChangeMe123!')
                db.session.add(admin)
                db.session.commit()
                print("[Database Import] Admin 'isaiah' created.")
            else:
                admin.email = 'admin@yanzhen.com'
                admin.set_password('ChangeMe123!')
                db.session.commit()
                print("[Database Import] Admin 'isaiah' password/email updated.")

            _ensure_mots_c_blog_image(app)
        except Exception as verif_err:
            print(f"[Database Import Verification Notice]: {verif_err}")
