import sys
from app import app
from models import Product, Category

sys.stdout.reconfigure(encoding='utf-8')

with app.app_context():
    total_count = Product.query.count()
    print("==================================================")
    print(f"Total Products Imported: {total_count}")
    print("==================================================")

    print("\n--- Categories Breakdown ---")
    for cat in Category.query.all():
        print(f"- {cat.name}: {cat.products.count()} products")

    print("\n--- First 10 Products with Prices ---")
    first_10 = Product.query.limit(10).all()
    for idx, p in enumerate(first_10, 1):
        print(f"{idx}. {p.name} | Price: ${p.price:.2f}")

    print("\n--- Target Verifications ---")
    sema_5mg = Product.query.filter(Product.name.ilike('%Semaglutide 5mg%')).first()
    tirz_10mg = Product.query.filter(Product.name.ilike('%Tirzepatide 10mg%')).first()

    if sema_5mg:
        print(f"CONFIRMATION: {sema_5mg.name} -> Price: ${sema_5mg.price:.2f} (Match $30: {sema_5mg.price == 30.0})")
    else:
        print("CONFIRMATION: Semaglutide 5mg not found")

    if tirz_10mg:
        print(f"CONFIRMATION: {tirz_10mg.name} -> Price: ${tirz_10mg.price:.2f} (Match $46: {tirz_10mg.price == 46.0})")
    else:
        print("CONFIRMATION: Tirzepatide 10mg not found")

    print("==================================================")
