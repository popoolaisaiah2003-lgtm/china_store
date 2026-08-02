import os
from extensions import db
from sqlalchemy import text

def import_sql_file_if_empty(app):
    with app.app_context():
        try:
            db.create_all()
        except Exception as create_err:
            print(f"[Database Init] create_all notice: {create_err}")

        try:
            from models import Product
            current_count = Product.query.count()
            if current_count >= 170:
                print(f"[Database Import] Table products already has {current_count} items. Skipping auto-import.")
                return
        except Exception:
            current_count = 0

        sql_file_path = os.path.join(app.root_path, 'yan_zhen_peptide.sql')
        if not os.path.exists(sql_file_path):
            print(f"[Database Import Warning] {sql_file_path} file not found.")
            return

        print(f"[Database Import] Importing real data from {sql_file_path} into {db.engine.url.drivername} database...")
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        inserted_statements = 0
        for line in lines:
            stmt = line.strip()
            if stmt.startswith('INSERT INTO'):
                if stmt.endswith(';'):
                    stmt = stmt[:-1]
                try:
                    db.session.execute(text(stmt))
                    db.session.commit()
                    inserted_statements += 1
                except Exception as insert_err:
                    db.session.rollback()

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
        except Exception as verif_err:
            print(f"[Database Import Verification Notice]: {verif_err}")
