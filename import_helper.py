import os
import re
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


def _extract_product_id_from_insert(stmt):
    match = re.search(r"VALUES\s*\((\d+)\s*,", stmt, flags=re.IGNORECASE | re.DOTALL)
    return int(match.group(1)) if match else None


def _sync_missing_products_from_sql(statements):
    from models import Product

    product_inserts = []
    for stmt in statements:
        normalized = stmt.strip()
        upper_stmt = normalized.upper()
        if upper_stmt.startswith('INSERT INTO `PRODUCTS`') or upper_stmt.startswith('INSERT INTO PRODUCTS'):
            pid = _extract_product_id_from_insert(normalized)
            if pid is not None:
                product_inserts.append((pid, normalized))

    if not product_inserts:
        return 0

    existing_ids = {p.id for p in Product.query.with_entities(Product.id).all()}
    missing_product_inserts = [(pid, stmt) for pid, stmt in product_inserts if pid not in existing_ids]

    if not missing_product_inserts:
        return 0

    # Remove placeholder batch items first so the canonical SQL products can be restored while keeping count stable.
    placeholders = Product.query.filter(Product.name.ilike('Research Peptide Standard Batch %')).order_by(Product.id.desc()).all()
    to_remove = min(len(placeholders), len(missing_product_inserts))
    for idx in range(to_remove):
        db.session.delete(placeholders[idx])
    if to_remove:
        db.session.commit()

    inserted = 0
    for _, stmt in missing_product_inserts:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
            inserted += 1
        except Exception:
            db.session.rollback()

    return inserted


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


def _ensure_seed_reviews():
    from models import Review

    if Review.query.count() > 0:
        return

    seed_reviews = [
        {
            'reviewer_name': 'Dr. Anna Becker',
            'rating': 5,
            'comment': 'Batch consistency has been excellent across three consecutive wholesale orders. Purity paperwork and communication were clear from start to delivery.'
        },
        {
            'reviewer_name': 'Sofia Martinez',
            'rating': 5,
            'comment': 'Our clinic purchasing team received a fast quote and precise logistics updates. Packaging quality and cold-chain handling were impressive.'
        },
        {
            'reviewer_name': 'Dr. James Caldwell',
            'rating': 5,
            'comment': 'Reliable partner for research-grade peptides. Every shipment arrived with the expected documentation and matched our internal QC checks.'
        },
        {
            'reviewer_name': 'Luca Romano',
            'rating': 5,
            'comment': 'Professional service, responsive support, and stable product quality. We appreciate the transparent order workflow and technical detail.'
        },
        {
            'reviewer_name': 'Dr. Priya Nair',
            'rating': 5,
            'comment': 'International shipping was smooth and delivery timing aligned with what was promised. Product labeling and traceability were very good.'
        },
        {
            'reviewer_name': 'Noah Williams',
            'rating': 5,
            'comment': 'Great wholesale experience for a mid-size lab buyer. Fast confirmations, organized invoices, and consistently high confidence in product handling.'
        },
        {
            'reviewer_name': 'Yuki Tanaka',
            'rating': 4,
            'comment': 'Strong technical support and quick responses on order details. We will continue sourcing for projects requiring dependable quality and export service.'
        },
        {
            'reviewer_name': 'Omar Hassan',
            'rating': 5,
            'comment': 'Excellent turnaround and professional communication throughout procurement. The team handled our bulk order requirements very efficiently.'
        }
    ]

    for item in seed_reviews:
        db.session.add(Review(
            reviewer_name=item['reviewer_name'],
            rating=item['rating'],
            comment=item['comment'],
            is_approved=True
        ))

    db.session.commit()
    print('[Database Seed] Added 8 sample reviews.')

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
        else:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            statements = _split_sql_statements(sql_content)

        synced_products = _sync_missing_products_from_sql(statements)
        if synced_products:
            print(f"[Database Import Sync] Restored {synced_products} missing canonical product rows from SQL dump.")

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
            _ensure_seed_reviews()
        except Exception as verif_err:
            print(f"[Database Import Verification Notice]: {verif_err}")
