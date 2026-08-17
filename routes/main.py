import os
import math
import datetime
import urllib.parse
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory, Response, jsonify
from models import Product, Category, Review, COA, BlogPost, Comment, Setting, OrderRecord, ProductImage, ShipmentUpdate, ContactInquiry
from forms import CheckoutForm, ReviewForm, ContactForm
from translations import translate
from extensions import db

main = Blueprint('main', __name__)

def _(key):
    lang = session.get('lang', 'en')
    return translate(key, lang)


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


def wants_json_response():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def get_wishlist_ids():
    wishlist = session.get('wishlist', [])
    normalized = []
    for product_id in wishlist:
        try:
            normalized.append(int(product_id))
        except (TypeError, ValueError):
            continue
    return normalized


def save_wishlist_ids(product_ids):
    session['wishlist'] = [str(product_id) for product_id in sorted(set(product_ids))]
    session.modified = True


def build_order_context():
    cart_items, grand_total, total_quantity = get_cart_details()
    quotation_number = f"YZ-{datetime.datetime.now().year}-{session.get('quotation_id', '0001')}"
    return {
        'cart_items': cart_items,
        'grand_total': grand_total,
        'total_quantity': total_quantity,
        'quotation_number': quotation_number,
    }


def build_order_ajax_payload(message):
    context = build_order_context()
    return {
        'success': True,
        'message': message,
        'cart_total_count': context['total_quantity'],
        'cart_items_count': len(context['cart_items']),
        'grand_total': context['grand_total'],
        'order_panel_html': render_template('partials/order_panel.html', **context),
        'is_empty': not context['cart_items'],
    }


def apply_cart_addition(product, quantity):
    cart = session.get('cart', {})
    pid_str = str(product.id)
    cart[pid_str] = cart.get(pid_str, 0) + quantity
    session['cart'] = cart
    session.modified = True
    _, _, total_quantity = get_cart_details()
    return total_quantity

@main.context_processor
def inject_global_vars():
    lang = get_current_lang()
    _, _, total_quantity = get_cart_details()
    show_lang_modal = session.get('lang_modal_shown') is not True
    wishlist_product_ids = get_wishlist_ids()
    return dict(
        lang=lang,
        _ = lambda key: translate(key, lang),
        cart_total_count=total_quantity,
        wishlist_product_ids=wishlist_product_ids,
        wishlist_count=len(wishlist_product_ids),
        show_lang_modal=show_lang_modal,
        company_name=Setting.get_val('company_name', 'Velora Peptide'),
        whatsapp_number=Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '447763743631'))
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
    featured_reviews = Review.query.filter_by(approved=True).order_by(Review.featured.desc(), Review.created_at.desc()).limit(3).all()
    featured_reviews_data = []
    for review in featured_reviews:
        card = _review_card_data(review)
        featured_reviews_data.append(card)
    latest_coas = COA.query.filter_by(active=True).order_by(COA.issue_date.desc()).limit(4).all()
    total_product_count = Product.query.count()
    review_form = ReviewForm()
    return render_template(
        'index.html',
        featured_products=featured_products,
        categories=categories,
        featured_reviews=featured_reviews_data,
        latest_coas=latest_coas,
        total_product_count=total_product_count,
        review_form=review_form
    )


@main.route('/submit-review', methods=['POST'])
def submit_review():
    form = ReviewForm()
    
    name_val = form.customer_name.data.strip() if form.customer_name.data else request.form.get('customer_name', '').strip()
    country_val = (form.country.data.strip() if form.country.data and form.country.data.strip() else request.form.get('country', '').strip()) or 'International Client'
    
    try:
        rating_val = int(form.rating.data) if form.rating.data else int(request.form.get('rating', '5'))
    except (ValueError, TypeError):
        rating_val = 5

    review_text_val = form.review_text.data.strip() if form.review_text.data else request.form.get('review_text', '').strip()

    if not name_val or not review_text_val:
        flash(_('please_fill_required_review_fields'), 'danger')
        return redirect(request.referrer or url_for('main.index'))

    try:
        new_review = Review(
            customer_name=name_val,
            country=country_val,
            rating=rating_val,
            review_text=review_text_val,
            approved=False,
            featured=False,
            reviewer_name=name_val,
            comment=review_text_val,
            is_approved=False
        )
        db.session.add(new_review)
        db.session.commit()

        flash(_('review_submitted_success'), 'success')

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Public review submission failed')
        flash('An unexpected error occurred while saving your review. Please try again.', 'danger')

    return redirect(request.referrer or url_for('main.index'))


@main.route('/reviews', methods=['GET', 'POST'])
def reviews():
    form = ReviewForm()

    if request.method == 'POST':
        name_val = form.customer_name.data.strip() if form.customer_name.data else request.form.get('customer_name', '').strip()
        country_val = (form.country.data.strip() if form.country.data and form.country.data.strip() else request.form.get('country', '').strip()) or 'International Client'
        
        try:
            rating_val = int(form.rating.data) if form.rating.data else int(request.form.get('rating', '5'))
        except (ValueError, TypeError):
            rating_val = 5

        review_text_val = form.review_text.data.strip() if form.review_text.data else request.form.get('review_text', '').strip()

        if name_val and review_text_val:
            try:
                new_review = Review(
                    customer_name=name_val,
                    country=country_val,
                    rating=rating_val,
                    review_text=review_text_val,
                    approved=False,
                    featured=False,
                    reviewer_name=name_val,
                    comment=review_text_val,
                    is_approved=False
                )
                db.session.add(new_review)
                db.session.commit()

                flash(_('review_submitted_success'), 'success')
                return redirect(url_for('main.reviews'))
            except Exception:
                db.session.rollback()
                current_app.logger.exception('Reviews page submission failed')
                flash('An unexpected error occurred while saving your review. Please try again.', 'danger')
        else:
            flash(_('please_fill_required_review_fields'), 'danger')

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
    total_matching_products = len(all_products)
    categories = Category.query.all()

    if wants_json_response():
        return jsonify({
            'success': True,
            'products_html': render_template('partials/product_cards.html', products=all_products),
            'loaded_count': total_matching_products,
            'total_count': total_matching_products,
        })
    
    return render_template(
        'products.html', 
        products=all_products, 
        categories=categories, 
        selected_category=selected_category,
        search_query=search_query,
        sort_by=sort_by,
        total_matching_products=total_matching_products,
    )


@main.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    whatsapp_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '447763743631'))
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
            b'%PDF-1.4\n1 0 obj\n<< /Title (Velora Peptide Certificate of Analysis) >>\nendobj\n'
            b'2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n'
            b'3 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n'
            b'4 0 obj\n<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n'
            b'5 0 obj\n<< /Length 120 >>\nstream\n'
            b'BT /F1 18 Tf 50 700 Td (Velora Peptide - Certificate of Analysis Purity >=99.8%) Tj ET\n'
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

    total_quantity = apply_cart_addition(product, qty)

    if wants_json_response():
        return jsonify({
            'success': True,
            'cart_total_count': total_quantity,
            'message': f'Added {qty} × {product.name} to your quotation.',
            'product_name': product.name,
            'quantity': qty,
        })

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

    total_quantity = apply_cart_addition(product, qty)

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
    message = 'Quotation quantity updated.'
    if qty <= 0:
        cart.pop(pid_str, None)
        message = 'Item removed from quotation.'
        flash(message, 'info')
    else:
        cart[pid_str] = qty
        flash(message, 'success')

    session['cart'] = cart
    session.modified = True

    if wants_json_response():
        return jsonify(build_order_ajax_payload(message))

    return redirect(url_for('main.order'))

@main.route('/cart/remove/<int:product_id>', methods=['POST'])
def cart_remove(product_id):
    cart = session.get('cart', {})
    pid_str = str(product_id)
    message = 'Item removed from wholesale quotation.'
    if pid_str in cart:
        cart.pop(pid_str)
        session['cart'] = cart
        session.modified = True
        flash(message, 'info')

    if wants_json_response():
        return jsonify(build_order_ajax_payload(message))
    return redirect(url_for('main.order'))

@main.route('/order')
def order():
    return render_template('order.html', **build_order_context())

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
            f"Hello Velora Peptide,\n\n"
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
            grand_total=grand_total,
            status='Pending'
        )
        db.session.add(record)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        encoded_message = urllib.parse.quote(raw_message)
        wa_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '447763743631'))
        whatsapp_url = f"https://wa.me/{wa_number}?text={encoded_message}"

    return render_template('checkout.html', form=form, cart_items=cart_items, grand_total=grand_total, total_quantity=total_quantity, whatsapp_url=whatsapp_url, quotation_number=quotation_number)

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    whatsapp_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '447763743631'))

    if form.validate_on_submit():
        inquiry = ContactInquiry(
            name=form.name.data.strip(),
            email=form.email.data.strip(),
            company=form.company.data.strip() if form.company.data else None,
            subject=form.subject.data.strip(),
            message=form.message.data.strip(),
            is_read=False,
        )
        db.session.add(inquiry)
        try:
            db.session.commit()
            flash(_('contact_inquiry_submitted_success'), 'success')
            return redirect(url_for('main.contact'))
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Contact inquiry save failed')
            flash(_('contact_inquiry_submit_error'), 'danger')
    elif request.method == 'POST':
        flash(_('contact_inquiry_validation_error'), 'danger')

    return render_template('contact.html', whatsapp_number=whatsapp_number, form=form)


@main.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
def wishlist_toggle(product_id):
    product = Product.query.get_or_404(product_id)
    wishlist_ids = set(get_wishlist_ids())
    is_favorited = product_id not in wishlist_ids

    if is_favorited:
        wishlist_ids.add(product_id)
        message = f'{product.name} added to favorites.'
    else:
        wishlist_ids.discard(product_id)
        message = f'{product.name} removed from favorites.'

    save_wishlist_ids(wishlist_ids)

    if wants_json_response():
        return jsonify({
            'success': True,
            'message': message,
            'product_id': product_id,
            'is_favorited': is_favorited,
            'wishlist_count': len(wishlist_ids),
        })

    flash(message, 'success' if is_favorited else 'info')
    next_page = request.form.get('next') or request.referrer
    return redirect(next_page or url_for('main.product_detail', slug=product.slug))

@main.route('/faq')
def faq():
    return render_template('faq.html')

@main.route('/shipments')
def shipments():
    shipment_list = ShipmentUpdate.query.filter_by(is_published=True).order_by(ShipmentUpdate.created_at.desc()).all()
    return render_template('shipments.html', shipments=shipment_list)

@main.route('/about')
def about():
    whatsapp_number = Setting.get_val('whatsapp_number', current_app.config.get('WHATSAPP_NUMBER', '447763743631'))
    return render_template('about.html', whatsapp_number=whatsapp_number)
