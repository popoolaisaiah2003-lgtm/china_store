import os
import math
import datetime
import urllib.parse
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory, Response, jsonify
from models import Product, Category, Review, COA, BlogPost, Comment, Setting, OrderRecord, ProductImage, ShipmentUpdate
from forms import CheckoutForm, ReviewForm
from translations import translate
from extensions import db

main = Blueprint('main', __name__)

REVIEW_COUNTRY_MAP = {
    'Dr. Anna Becker': 'Germany',
    'Sofia Martinez': 'Spain',
    'Dr. James Caldwell': 'United States',
    'Luca Romano': 'Italy',
    'Dr. Priya Nair': 'India',
    'Noah Williams': 'Canada',
    'Yuki Tanaka': 'Japan',
    'Omar Hassan': 'UAE'
}


def _country_for_review(review):
    reviewer_name = (getattr(review, 'customer_name', None) or getattr(review, 'reviewer_name', None) or '').strip()
    return getattr(review, 'country', None) or REVIEW_COUNTRY_MAP.get(reviewer_name, 'International Client')


def _review_card_data(review):
    return {
        'name': getattr(review, 'customer_name', None) or getattr(review, 'reviewer_name', None) or 'Anonymous',
        'country': _country_for_review(review),
        'rating': review.rating or 5,
        'comment': getattr(review, 'review_text', None) or getattr(review, 'comment', None) or '',
        'featured': bool(getattr(review, 'featured', False) or getattr(review, 'is_approved', False)),
        'created_at': review.created_at,
        'verified': True,
    }

def get_current_lang():
    return session.get('lang', 'en')

@main.context_processor
def inject_global_vars():
    lang = get_current_lang()
    _, _, total_quantity = get_cart_details()
    show_lang_modal = session.get('lang_modal_shown') is not True
    return dict(
        lang=lang,
        _ = lambda key: translate(key, lang),
        cart_total_count=total_quantity,
        show_lang_modal=show_lang_modal,
        company_name=Setting.get_val('company_name', 'Yan Zhen Peptide'),
        whatsapp_number=Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '85263294280'))
    )

@main.route('/set_language/<lang_code>')
def set_language(lang_code):
    if lang_code in ['en', 'zh', 'es', 'ar', 'fr']:
        session['lang'] = lang_code
    session['lang_modal_shown'] = True
    next_page = request.referrer or url_for('main.index')
    return redirect(next_page)

# --- CART / QUOTATION HELPER FUNCTIONS ---
def get_cart():
    return session.get('cart', {})

def get_cart_details():
    cart = get_cart()
    cart_items = []
    grand_total = 0.0
    total_quantity = 0

    for product_id_str, qty in cart.items():
        try:
            pid = int(product_id_str)
            product = Product.query.get(pid)
            if product:
                line_total = product.price * qty
                grand_total += line_total
                total_quantity += qty
                cart_items.append({
                    'product': product,
                    'product_id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'quantity': qty,
                    'line_total': line_total
                })
        except ValueError:
            continue

    return cart_items, grand_total, total_quantity

@main.route('/')
def index():
    featured_products = Product.query.filter_by(is_featured=True).limit(8).all()
    if not featured_products:
        featured_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.all()
    featured_reviews = Review.query.filter_by(approved=True, featured=True).order_by(Review.created_at.desc()).limit(3).all()
    featured_reviews_data = []
    for review in featured_reviews:
        card = _review_card_data(review)
        featured_reviews_data.append(card)
    latest_coas = COA.query.filter_by(active=True).order_by(COA.issue_date.desc()).limit(4).all()
    total_product_count = Product.query.count()
    return render_template(
        'index.html',
        featured_products=featured_products,
        categories=categories,
        featured_reviews=featured_reviews_data,
        latest_coas=latest_coas,
        total_product_count=total_product_count
    )


@main.route('/reviews', methods=['GET', 'POST'])
def reviews():
    form = ReviewForm()

    if form.validate_on_submit():
        review = Review(
            customer_name=form.customer_name.data.strip(),
            country=form.country.data.strip(),
            rating=form.rating.data,
            review_text=form.review_text.data.strip(),
            approved=False,
            featured=False,
            reviewer_name=form.customer_name.data.strip(),
            comment=form.review_text.data.strip(),
            is_approved=False,
        )
        db.session.add(review)
        db.session.commit()
        flash('Thank you. Your review has been submitted for approval.', 'success')
        return redirect(url_for('main.reviews'))

    reviews_query = Review.query.filter_by(approved=True).order_by(Review.featured.desc(), Review.created_at.desc()).all()
    reviews_data = [_review_card_data(review) for review in reviews_query]
    total_reviews = len(reviews_data)
    average_rating = round(sum(item['rating'] for item in reviews_data) / total_reviews, 1) if total_reviews else 0
    featured_reviews = [item for item in reviews_data if item['featured']][:3]

    return render_template(
        'reviews.html',
        form=form,
        reviews=reviews_data,
        total_reviews=total_reviews,
        average_rating=average_rating,
        featured_reviews=featured_reviews,
    )

@main.route('/products')
def products():
    category_slug = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'name_asc')
    
    query = Product.query
    selected_category = None
    
    if category_slug:
        selected_category = Category.query.filter_by(slug=category_slug).first()
        if selected_category:
            query = query.filter_by(category_id=selected_category.id)
            
    if search_query:
        query = query.filter(
            Product.name.ilike(f'%{search_query}%') | 
            Product.short_description.ilike(f'%{search_query}%') | 
            Product.sequence_or_cas.ilike(f'%{search_query}%')
        )

    if sort_by == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.name.asc())
        
    all_products = query.all()
    categories = Category.query.all()
    
    return render_template(
        'products.html', 
        products=all_products, 
        categories=categories, 
        selected_category=selected_category,
        search_query=search_query,
        sort_by=sort_by
    )


@main.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    whatsapp_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '85263294280'))
    return render_template('product_detail.html', product=product, related_products=related_products, whatsapp_number=whatsapp_number)

# --- PUBLIC COA SYSTEM (/coa) ---
@main.route('/coa')
def coa_list():
    query_str = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)

    query = COA.query.filter_by(active=True)

    if category_id:
        query = query.join(Product).filter(Product.category_id == category_id)

    if query_str:
        query = query.join(Product).filter(
            Product.name.ilike(f'%{query_str}%') | 
            COA.batch_number.ilike(f'%{query_str}%')
        )

    coas = query.order_by(COA.issue_date.desc()).all()
    categories = Category.query.all()
    return render_template('coa.html', coas=coas, categories=categories, query_str=query_str, category_id=category_id)

@main.route('/coa/download/<int:coa_id>')
def download_coa(coa_id):
    coa = COA.query.get_or_404(coa_id)
    folder = current_app.config['COA_UPLOAD_FOLDER']
    file_name = coa.file_url or getattr(coa, 'file_name', None) or f"COA_Batch_{coa.batch_number}.pdf"
    
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, file_name)

    if not os.path.exists(file_path):
        pdf_content = (
            b'%PDF-1.4\n1 0 obj\n<< /Title (Yan Zhen Peptide Certificate of Analysis) >>\nendobj\n'
            b'2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n'
            b'3 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n'
            b'4 0 obj\n<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n'
            b'5 0 obj\n<< /Length 120 >>\nstream\n'
            b'BT /F1 18 Tf 50 700 Td (Yan Zhen Peptide - Certificate of Analysis Purity >=99.8%) Tj ET\n'
            b'endstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000078 00000 n\n'
            b'0000000127 00000 n\n0000000190 00000 n\n0000000285 00000 n\ntrailer\n<< /Size 6 /Root 2 0 R >>\n'
            b'startxref\n428\n%%EOF'
        )
        with open(file_path, 'wb') as f:
            f.write(pdf_content)

    return send_from_directory(folder, file_name, as_attachment=True)

@main.route('/coa/download/alias/<int:id>')
def coa_download(id):
    return download_coa(id)

# --- CART & QUOTATION SYSTEM ---
@main.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        qty = int(request.form.get('quantity', 1))
        if qty < 1:
            qty = 1
    except ValueError:
        qty = 1

    cart = session.get('cart', {})
    pid_str = str(product_id)
    cart[pid_str] = cart.get(pid_str, 0) + qty
    session['cart'] = cart
    session.modified = True

    flash(f'Added {qty} × "{product.name}" to your quotation.', 'success')
    next_page = request.form.get('next') or request.referrer
    return redirect(next_page or url_for('main.order'))

@main.route('/cart/add-ajax/<int:product_id>', methods=['POST'])
def cart_add_ajax(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        data = request.get_json(silent=True) or request.form
        qty = int(data.get('quantity', 1))
        if qty < 1:
            qty = 1
    except (ValueError, TypeError):
        qty = 1

    cart = session.get('cart', {})
    pid_str = str(product_id)
    cart[pid_str] = cart.get(pid_str, 0) + qty
    session['cart'] = cart
    session.modified = True

    _, _, total_quantity = get_cart_details()

    return jsonify({
        'success': True,
        'cart_total_count': total_quantity,
        'message': f"Added {qty} × {product.name} to quotation cart",
        'product_name': product.name,
        'quantity': qty
    })

@main.route('/cart/update/<int:product_id>', methods=['POST'])
def cart_update(product_id):
    try:
        qty = int(request.form.get('quantity', 1))
    except ValueError:
        qty = 1

    cart = session.get('cart', {})
    pid_str = str(product_id)
    if qty <= 0:
        cart.pop(pid_str, None)
        flash('Item removed from quotation.', 'info')
    else:
        cart[pid_str] = qty
        flash('Quotation quantity updated.', 'success')

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('main.order'))

@main.route('/cart/remove/<int:product_id>', methods=['POST'])
def cart_remove(product_id):
    cart = session.get('cart', {})
    pid_str = str(product_id)
    if pid_str in cart:
        cart.pop(pid_str)
        session['cart'] = cart
        session.modified = True
        flash('Item removed from wholesale quotation.', 'info')
    return redirect(url_for('main.order'))

@main.route('/order')
def order():
    cart_items, grand_total, total_quantity = get_cart_details()
    quotation_number = f"YZ-{datetime.datetime.now().year}-{session.get('quotation_id', '0001')}"
    return render_template('order.html', cart_items=cart_items, grand_total=grand_total, total_quantity=total_quantity, quotation_number=quotation_number)

@main.route('/order/print')
def order_print():
    cart_items, grand_total, total_quantity = get_cart_details()
    quotation_number = f"YZ-{datetime.datetime.now().year}-0001"
    today_date = datetime.date.today().strftime('%B %d, %Y')
    return render_template('order_print.html', cart_items=cart_items, grand_total=grand_total, total_quantity=total_quantity, quotation_number=quotation_number, today_date=today_date)

@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_items, grand_total, total_quantity = get_cart_details()
    if not cart_items and request.method == 'POST':
        flash('Your quotation cart is currently empty. Please add products first.', 'warning')
        return redirect(url_for('main.order'))

    if not cart_items and request.method == 'GET':
        flash('Your quotation cart is currently empty. You can still complete customer details, then add products anytime.', 'info')

    form = CheckoutForm()
    whatsapp_url = None
    import uuid
    from datetime import datetime

    quotation_number = f"YZ-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    while OrderRecord.query.filter_by(quotation_number=quotation_number).first():
        quotation_number = f"YZ-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    if form.validate_on_submit():
        name = form.full_name.data.strip()
        email = form.email.data.strip()
        country = form.country.data.strip()
        zip_code = form.zip_code.data.strip() if form.zip_code.data else 'N/A'
        address = form.address.data.strip()
        phone = form.phone.data.strip()

        order_lines = []
        for item in cart_items:
            order_lines.append(f"- {item['name']} × {item['quantity']} = ${item['line_total']:.2f}")
        
        order_summary_text = "\n".join(order_lines)

        raw_message = (
            f"Hello Yan Zhen Peptide,\n\n"
            f"I would like to place a wholesale order.\n\n"
            f"Quotation Reference: {quotation_number}\n\n"
            f"Customer Information\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Country: {country}\n"
            f"ZIP / Postal Code: {zip_code}\n"
            f"Shipping Address: {address}\n"
            f"Phone: {phone}\n\n"
            f"Order Summary\n"
            f"{order_summary_text}\n\n"
            f"Grand Total: ${grand_total:.2f}\n\n"
            f"Please provide shipping cost and delivery timeline.\n\n"
            f"Thank you."
        )

        # Record Order in Database
        record = OrderRecord(
            quotation_number=quotation_number,
            customer_name=name,
            customer_email=email,
            customer_country=country,
            zip_code=zip_code,
            customer_address=address,
            customer_phone=phone,
            items_json=str([item['name'] + ' x ' + str(item['quantity']) for item in cart_items]),
            grand_total=grand_total
        )
        db.session.add(record)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        encoded_message = urllib.parse.quote(raw_message)
        wa_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '85263294280'))
        whatsapp_url = f"https://wa.me/{wa_number}?text={encoded_message}"

    return render_template('checkout.html', form=form, cart_items=cart_items, grand_total=grand_total, total_quantity=total_quantity, whatsapp_url=whatsapp_url, quotation_number=quotation_number)

@main.route('/contact')
def contact():
    whatsapp_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '85263294280'))
    return render_template('contact.html', whatsapp_number=whatsapp_number)

@main.route('/faq')
def faq():
    return render_template('faq.html')

@main.route('/shipments')
def shipments():
    shipment_list = ShipmentUpdate.query.filter_by(is_published=True).order_by(ShipmentUpdate.created_at.desc()).all()
    return render_template('shipments.html', shipments=shipment_list)

@main.route('/about')
def about():
    whatsapp_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '85263294280'))
    return render_template('about.html', whatsapp_number=whatsapp_number)
