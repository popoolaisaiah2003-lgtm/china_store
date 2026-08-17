import openpyxl
import re
from app import create_app
from extensions import db
from models import Category, Product, ProductImage

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def parse_price(val):
    if not val:
        return 0.0
    s = str(val).strip().replace('$', '').replace('￥', '').replace(',', '')
    try:
        return float(s)
    except ValueError:
        return 0.0

def categorize(name, cat_no=""):
    n = name.upper()
    
    # 1. GLP-1 & Metabolic
    if any(k in n for k in ['SEMAGLUTIDE', 'TIRZEPATIDE', 'RETATRUTIDE', 'CAGRILINTIDE', 'MAZDUTIDE', 'SURVODUTIDE', 'GLP-1', 'AOD9604', '5-AMINO-1MQ', 'ADIPOTIDE', 'AICAR']):
        return 'Metabolic & GLP-1 Analogues'
        
    # 2. Tissue Recovery & Healing
    if any(k in n for k in ['BPC', 'TB500', 'THYMOSIN B4', 'KPV', 'ARA-290', 'THYMOSIN ALPHA', 'THYMALIN']):
        return 'Tissue Recovery & Healing'
        
    # 3. GH Secretagogues
    if any(k in n for k in ['HGH', 'SOMATROPIN', 'CJC', 'IPAMORELIN', 'GHRP', 'HEXARELIN', 'SERMORELIN', 'TESAMORELIN', 'FRAGMENT']):
        return 'GH Secretagogues'
        
    # 4. Pigmentation & Wellness
    if any(k in n for k in ['MT-1', 'MT-2', 'MELANOTAN', 'PT-141', 'GHK', 'NAD', 'GLUTATHIONE', 'EPITHALON', 'MOTS', 'SELANK', 'SEMAX', 'OXYTOCIN', 'DSIP']):
        return 'Pigmentation & Wellness'
        
    # 5. Other Peptides
    return 'Other Peptides'

def run_import():
    excel_path = r"C:\Users\HomePC\Desktop\VELORA PEPTIDE FOLDER\BTC, USDT PRICELIST.xlsx"
    wb = openpyxl.load_workbook(excel_path)
    sheet = wb.active

    app = create_app()
    with app.app_context():
        print("[Import] Clearing old demo products and categories...")
        ProductImage.query.delete()
        Product.query.delete()
        Category.query.delete()
        db.session.commit()

        # Create Categories
        cat_names = [
            'Metabolic & GLP-1 Analogues',
            'Tissue Recovery & Healing',
            'GH Secretagogues',
            'Pigmentation & Wellness',
            'Other Peptides'
        ]
        
        cat_map = {}
        for cname in cat_names:
            c = Category(name=cname, slug=slugify(cname), description=f"Premium laboratory grade {cname}.")
            db.session.add(c)
            db.session.flush()
            cat_map[cname] = c.id

        db.session.commit()

        # Parse Excel Rows
        imported_count = 0
        current_product_name = ""

        # Skip header rows (row 1 & 2)
        rows = list(sheet.iter_rows(values_only=True))[2:]

        for idx, row in enumerate(rows, start=3):
            if not row or not any(row):
                continue
                
            col0 = str(row[0]).strip() if row[0] is not None else ""
            col1 = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            col2 = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
            col3 = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""

            # Check if col1 contains product name or if it's carried over
            if col1 and not col1.endswith('vials') and not col1.endswith('vial') and not ('*' in col1 and '$' in col2):
                current_product_name = col1
            
            # Determine item attributes
            cat_no = col0
            spec = ""
            price_val = 0.0

            if '$' in col3 or '￥' in col3 or col3.replace('.', '', 1).isdigit():
                spec = col2
                price_val = parse_price(col3)
            elif '$' in col2 or '￥' in col2 or col2.replace('.', '', 1).isdigit():
                spec = col1
                price_val = parse_price(col2)
            elif '$' in col1 or '￥' in col1 or col1.replace('.', '', 1).isdigit():
                spec = col0
                price_val = parse_price(col1)

            # If product name is missing from col1, use col0 if it looks like a name
            prod_name = current_product_name
            if not prod_name or prod_name == col0:
                if col0 and not col0.isalnum() and len(col0) > 3:
                    prod_name = col0

            if not prod_name:
                prod_name = f"Peptide Compound {cat_no}"

            # Format full displayed title
            full_title = f"{prod_name} ({spec})" if spec else prod_name
            slug = slugify(f"{cat_no}-{prod_name}-{spec}")
            if not slug or len(slug) < 2:
                slug = slugify(f"prod-{idx}-{prod_name}")

            # Ensure slug uniqueness
            existing_slug = Product.query.filter_by(slug=slug).first()
            if existing_slug:
                slug = f"{slug}-{idx}"

            category_name = categorize(prod_name, cat_no)
            category_id = cat_map[category_name]

            p = Product(
                category_id=category_id,
                name=full_title,
                slug=slug,
                purity='>= 99.8%',
                sequence_or_cas=cat_no if cat_no else None,
                short_description=f"Pack Spec: {spec}" if spec else "Sterile lyophilized research peptide.",
                description=f"Analytical research grade {full_title}. High-purity synthesized peptide vial produced under cleanroom laboratory protocols.",
                price=price_val,
                stock_status='In Stock',
                is_featured=(imported_count < 8)
            )
            db.session.add(p)
            imported_count += 1

        db.session.commit()
        print(f"[Import Success] Successfully imported {imported_count} products across {len(cat_map)} categories.")

if __name__ == '__main__':
    run_import()
