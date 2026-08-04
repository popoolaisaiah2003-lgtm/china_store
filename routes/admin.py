import os
import time
import re
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Admin, Product, Category, ProductImage, COA, BlogPost, Review, Comment, Setting, OrderRecord, ShipmentUpdate, ContactInquiry
from forms import LoginForm, CategoryForm, ProductForm, COAForm, BlogPostForm, SettingForm, ChangePasswordForm, ShipmentUpdateForm, ReviewForm

admin = Blueprint('admin', __name__, url_prefix='/admin')

# In-memory Failed Login Tracking (Rate limiting: max 5 failed attempts per 15 minutes)
FAILED_ATTEMPTS = {}

def is_rate_limited(key):
    now = time.time()
    attempts = FAILED_ATTEMPTS.get(key, [])
    valid_attempts = [t for t in attempts if now - t < 900]
    FAILED_ATTEMPTS[key] = valid_attempts
    return len(valid_attempts) >= 5

def record_failed_attempt(key):
    now = time.time()
    attempts = FAILED_ATTEMPTS.get(key, [])
    attempts.append(now)
    FAILED_ATTEMPTS[key] = attempts

def clear_failed_attempts(key):
    FAILED_ATTEMPTS.pop(key, None)

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def admin_required(func):
    """Decorator to enforce Admin authentication"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin.login', next=request.url))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def commit_with_rollback(success_message=None, success_category='success', error_message='Database operation failed. Please try again.'):
    try:
        db.session.commit()
        if success_message:
            flash(success_message, success_category)
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Admin DB write failed')
        flash(error_message, 'danger')
        return False


@admin.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
        
    client_ip = request.remote_addr or 'unknown'
    form = LoginForm()

    if is_rate_limited(client_ip):
        flash('Account temporarily locked due to multiple failed login attempts. Please try again in 15 minutes.', 'danger')
        return render_template('admin/login.html', form=form)

    if form.validate_on_submit():
        admin_account = Admin.query.filter_by(username=form.username.data.strip()).first()
        if admin_account and admin_account.check_password(form.password.data):
            clear_failed_attempts(client_ip)
            admin_account.last_login = datetime.utcnow()
            if not commit_with_rollback(error_message='Could not complete login write. Please try again.'):
                return render_template('admin/login.html', form=form)
            
            login_user(admin_account, remember=False)
            flash('Welcome to Yan Zhen Secure Management Console.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.dashboard'))
        else:
            record_failed_attempt(client_ip)
            flash('Invalid admin credentials. Failed attempt logged.', 'danger')
            
    return render_template('admin/login.html', form=form)

@admin.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out of Secure Panel.', 'info')
    return redirect(url_for('admin.login'))

@admin.route('/dashboard')
@admin_required
def dashboard():
    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_coas = COA.query.count()
    total_posts = BlogPost.query.count()
    total_reviews = Review.query.count()
    total_orders = OrderRecord.query.count()
    
    recent_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    recent_coas = COA.query.order_by(COA.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        total_products=total_products,
        total_categories=total_categories,
        total_coas=total_coas,
        total_posts=total_posts,
        total_reviews=total_reviews,
        total_orders=total_orders,
        recent_products=recent_products,
        recent_coas=recent_coas
    )

# ---------------- SECURE CHANGE PASSWORD ----------------
@admin.route('/change-password', methods=['GET', 'POST'])
@admin_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            if commit_with_rollback('Password updated successfully! Please use your new credentials for future logins.', 'success'):
                return redirect(url_for('admin.dashboard'))

    return render_template('admin/change_password.html', form=form)


# ---------------- PRODUCT CRUD ----------------
@admin.route('/products')
@admin_required
def products():
    search_q = request.args.get('q', '').strip()
    query = Product.query
    if search_q:
        query = query.filter(Product.name.ilike(f'%{search_q}%') | Product.sequence_or_cas.ilike(f'%{search_q}%'))
        all_products = query.order_by(Product.id.desc()).all()
    else:
        all_products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin/products.html', products=all_products, search_q=search_q)

@admin.route('/products/new', methods=['GET', 'POST'])
@admin_required
def product_new():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    
    if not form.category_id.choices:
        flash('Please create at least one Category before adding products.', 'warning')
        return redirect(url_for('admin.categories'))

    if form.validate_on_submit():
        slug = slugify(form.name.data)
        existing = Product.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{Product.query.count() + 1}"

        product = Product(
            name=form.name.data,
            slug=slug,
            category_id=form.category_id.data,
            purity=form.purity.data or '>= 99.8%',
            molecular_formula=form.molecular_formula.data,
            sequence_or_cas=form.sequence_or_cas.data,
            price=form.price.data,
            short_description=form.short_description.data,
            description=form.description.data,
            storage_info=form.storage_info.data,
            stock_status=form.stock_status.data,
            is_featured=form.is_featured.data
        )
        db.session.add(product)
        db.session.flush()

        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename) if hasattr(file, 'filename') and file.filename else None
            if filename:
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                new_filename = f"prod_{product.id}_{slug}.{ext}"
                file_path = os.path.join(current_app.config['PRODUCT_UPLOAD_FOLDER'], new_filename)
                file.save(file_path)
                
                img = ProductImage(product_id=product.id, image_filename=new_filename, is_primary=True)
                db.session.add(img)

        if commit_with_rollback('Product created successfully.', 'success'):
            return redirect(url_for('admin.products'))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Validation Error ({field}): {error}", 'danger')

    return render_template('admin/product_form.html', form=form, title="Add New Product", is_edit=False)

@admin.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def product_edit(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        product.name = form.name.data
        product.category_id = form.category_id.data
        product.purity = form.purity.data
        product.molecular_formula = form.molecular_formula.data
        product.sequence_or_cas = form.sequence_or_cas.data
        product.price = form.price.data
        product.short_description = form.short_description.data
        product.description = form.description.data
        product.storage_info = form.storage_info.data
        product.stock_status = form.stock_status.data
        product.is_featured = form.is_featured.data

        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename)
            if filename:
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                new_filename = f"prod_{product.id}_{product.slug}.{ext}"
                file_path = os.path.join(current_app.config['PRODUCT_UPLOAD_FOLDER'], new_filename)
                file.save(file_path)

                ProductImage.query.filter_by(product_id=product.id).update({'is_primary': False})
                img = ProductImage(product_id=product.id, image_filename=new_filename, is_primary=True)
                db.session.add(img)

        if commit_with_rollback(f'Product "{product.name}" updated successfully.', 'success'):
            return redirect(url_for('admin.products'))

    return render_template('admin/product_form.html', form=form, product=product, title=f"Edit {product.name}", is_edit=True)

@admin.route('/products/delete/<int:id>', methods=['POST'])
@admin_required
def product_delete(id):
    product = Product.query.get_or_404(id)
    name = product.name
    db.session.delete(product)
    if commit_with_rollback(f'Product "{name}" deleted.', 'info'):
        return redirect(url_for('admin.products'))
    return redirect(url_for('admin.products'))


# ---------------- COA MANAGEMENT ----------------
@admin.route('/coa')
@admin_required
def coa_index():
    coas = COA.query.order_by(COA.created_at.desc()).all()
    return render_template('admin/coa_list.html', coas=coas)

@admin.route('/coa/new', methods=['GET', 'POST'])
@admin_required
def coa_new():
    form = COAForm()
    form.product_id.choices = [(p.id, p.name) for p in Product.query.order_by(Product.name).all()]

    if form.validate_on_submit():
        file = form.coa_pdf.data
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'pdf'
        coa_filename = f"COA_{form.product_id.data}_{form.batch_number.data}.{ext}"
        file_path = os.path.join(current_app.config['COA_UPLOAD_FOLDER'], coa_filename)
        file.save(file_path)

        preview_filename = None
        if form.preview_image.data:
            pfile = form.preview_image.data
            pname = secure_filename(pfile.filename)
            pext = pname.rsplit('.', 1)[1].lower() if '.' in pname else 'jpg'
            preview_filename = f"COA_preview_{form.product_id.data}_{form.batch_number.data}.{pext}"
            pfile.save(os.path.join(current_app.config['COA_UPLOAD_FOLDER'], preview_filename))

        coa = COA(
            product_id=form.product_id.data,
            batch_number=form.batch_number.data,
            issue_date=form.issue_date.data,
            file_url=coa_filename,
            preview_image=preview_filename,
            active=form.active.data
        )
        db.session.add(coa)
        if commit_with_rollback('COA Certificate uploaded successfully.', 'success'):
            return redirect(url_for('admin.coa_index'))

    return render_template('admin/coa_form.html', form=form)

@admin.route('/coa/delete/<int:id>', methods=['POST'])
@admin_required
def coa_delete(id):
    coa = COA.query.get_or_404(id)
    db.session.delete(coa)
    if commit_with_rollback('COA deleted successfully.', 'info'):
        return redirect(url_for('admin.coa_index'))
    return redirect(url_for('admin.coa_index'))


# ---------------- REVIEWS CRUD ----------------
@admin.route('/reviews')
@admin_required
def reviews_index():
    reviews_list = Review.query.order_by(Review.approved.asc(), Review.featured.desc(), Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews_list)


@admin.route('/reviews/new', methods=['GET', 'POST'])
@admin_required
def review_new():
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            customer_name=form.customer_name.data.strip(),
            country=form.country.data.strip(),
            rating=form.rating.data,
            review_text=form.review_text.data.strip(),
            approved=False,
            featured=form.featured.data,
            reviewer_name=form.customer_name.data.strip(),
            comment=form.review_text.data.strip(),
            is_approved=False,
        )
        db.session.add(review)
        if commit_with_rollback('Review created successfully.', 'success'):
            return redirect(url_for('admin.reviews_index'))

    return render_template('admin/review_form.html', form=form, review=None, is_edit=False)


@admin.route('/reviews/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def review_edit(id):
    review = Review.query.get_or_404(id)
    if request.method == 'GET':
        form = ReviewForm(obj=review)
        form.rating.data = review.rating or 5
        form.review_text.data = review.review_text or review.comment or ''
    else:
        form = ReviewForm()

    if form.validate_on_submit():
        review.customer_name = form.customer_name.data.strip()
        review.country = form.country.data.strip()
        review.rating = form.rating.data
        review.review_text = form.review_text.data.strip()
        review.featured = form.featured.data
        review.reviewer_name = review.customer_name
        review.comment = review.review_text
        review.approved = review.approved if review.approved is not None else False
        review.is_approved = review.approved
        if commit_with_rollback('Review updated successfully.', 'success'):
            return redirect(url_for('admin.reviews_index'))

    return render_template('admin/review_form.html', form=form, review=review, is_edit=True)


@admin.route('/reviews/<int:id>/approve', methods=['POST'])
@admin_required
def review_approve(id):
    review = Review.query.get_or_404(id)
    review.approved = True
    review.is_approved = True
    if commit_with_rollback('Review approved successfully.', 'success'):
        return redirect(url_for('admin.reviews_index'))
    return redirect(url_for('admin.reviews_index'))


@admin.route('/reviews/<int:id>/reject', methods=['POST'])
@admin_required
def review_reject(id):
    review = Review.query.get_or_404(id)
    review.approved = False
    review.is_approved = False
    review.featured = False
    if commit_with_rollback('Review rejected successfully.', 'info'):
        return redirect(url_for('admin.reviews_index'))
    return redirect(url_for('admin.reviews_index'))


@admin.route('/reviews/<int:id>/feature', methods=['POST'])
@admin_required
def review_feature(id):
    review = Review.query.get_or_404(id)
    review.featured = not bool(review.featured)
    if review.featured:
        review.approved = True
        review.is_approved = True
    if commit_with_rollback('Review feature status updated.', 'success'):
        return redirect(url_for('admin.reviews_index'))
    return redirect(url_for('admin.reviews_index'))


@admin.route('/reviews/<int:id>/delete', methods=['POST'])
@admin_required
def review_delete(id):
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    if commit_with_rollback('Review deleted successfully.', 'info'):
        return redirect(url_for('admin.reviews_index'))
    return redirect(url_for('admin.reviews_index'))


# ---------------- CATEGORIES CRUD ----------------
@admin.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        slug = slugify(form.name.data)
        existing = Category.query.filter_by(slug=slug).first()
        if existing:
            flash('A category with a similar name already exists.', 'warning')
        else:
            cat = Category(name=form.name.data, slug=slug, description=form.description.data)
            db.session.add(cat)
            if commit_with_rollback(f'Category "{cat.name}" added successfully.', 'success'):
                return redirect(url_for('admin.categories'))

    categories_list = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', form=form, categories=categories_list)

@admin.route('/categories/delete/<int:id>', methods=['POST'])
@admin_required
def category_delete(id):
    cat = Category.query.get_or_404(id)
    name = cat.name
    db.session.delete(cat)
    if commit_with_rollback(f'Category "{name}" deleted.', 'info'):
        return redirect(url_for('admin.categories'))
    return redirect(url_for('admin.categories'))


# ---------------- BLOG CMS ----------------
@admin.route('/blog')
@admin_required
def blog_posts():
    posts = BlogPost.query.order_by(BlogPost.is_featured.desc(), BlogPost.created_at.desc()).all()
    return render_template('admin/blog_posts.html', posts=posts)

@admin.route('/blog/new', methods=['GET', 'POST'])
@admin_required
def blog_new():
    form = BlogPostForm()
    if form.validate_on_submit():
        slug = slugify(form.slug.data.strip()) if form.slug.data and form.slug.data.strip() else slugify(form.title.data)
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{BlogPost.query.count() + 1}"

        image_filename = None
        if form.image.data:
            bfile = form.image.data
            bname = secure_filename(bfile.filename) if hasattr(bfile, 'filename') and bfile.filename else None
            if bname:
                bext = bname.rsplit('.', 1)[1].lower() if '.' in bname else 'jpg'
                image_filename = f"blog_{slug}.{bext}"
                bfile.save(os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], image_filename))

        post = BlogPost(
            title=form.title.data,
            slug=slug,
            summary=form.summary.data,
            content=form.content.data,
            image_filename=image_filename,
            seo_title=form.seo_title.data,
            meta_description=form.meta_description.data,
            language=form.language.data,
            tags=form.tags.data,
            is_published=form.is_published.data,
            is_featured=form.is_featured.data
        )
        db.session.add(post)
        if commit_with_rollback('Blog article created successfully.', 'success'):
            return redirect(url_for('admin.blog_posts'))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Error in {field}: {err}", 'danger')

    return render_template('admin/blog_form.html', form=form, title="Create Research Article", is_edit=False)

@admin.route('/blog/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def blog_edit(id):
    post = BlogPost.query.get_or_404(id)
    form = BlogPostForm(obj=post)

    if form.validate_on_submit():
        post.title = form.title.data
        if form.slug.data and form.slug.data.strip():
            new_slug = slugify(form.slug.data.strip())
            existing = BlogPost.query.filter(BlogPost.slug == new_slug, BlogPost.id != id).first()
            if not existing:
                post.slug = new_slug
        
        post.summary = form.summary.data
        post.content = form.content.data
        post.seo_title = form.seo_title.data
        post.meta_description = form.meta_description.data
        post.language = form.language.data
        post.tags = form.tags.data
        post.is_published = form.is_published.data
        post.is_featured = form.is_featured.data
        post.updated_at = datetime.utcnow()

        if form.image.data:
            bfile = form.image.data
            bname = secure_filename(bfile.filename) if hasattr(bfile, 'filename') and bfile.filename else None
            if bname:
                bext = bname.rsplit('.', 1)[1].lower() if '.' in bname else 'jpg'
                new_image_filename = f"blog_{post.slug}.{bext}"
                bfile.save(os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], new_image_filename))
                post.image_filename = new_image_filename

        if commit_with_rollback('Blog article updated successfully.', 'success'):
            return redirect(url_for('admin.blog_posts'))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Error in {field}: {err}", 'danger')

    return render_template('admin/blog_form.html', form=form, post=post, title=f"Edit {post.title}", is_edit=True)

@admin.route('/blog/delete/<int:id>', methods=['POST'])
@admin_required
def blog_delete(id):
    post = BlogPost.query.get_or_404(id)
    title = post.title
    
    if post.image_filename:
        file_path = os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], post.image_filename)
        other_uses = BlogPost.query.filter(BlogPost.image_filename == post.image_filename, BlogPost.id != id).count()
        if other_uses == 0 and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                current_app.logger.warning('Could not delete blog image: %s', file_path)

    db.session.delete(post)
    if commit_with_rollback(f'Article "{title}" deleted successfully.', 'info'):
        return redirect(url_for('admin.blog_posts'))
    return redirect(url_for('admin.blog_posts'))

@admin.route('/blog/toggle-publish/<int:id>', methods=['POST'])
@admin_required
def blog_toggle_publish(id):
    post = BlogPost.query.get_or_404(id)
    post.is_published = not post.is_published
    post.updated_at = datetime.utcnow()
    status_str = "published" if post.is_published else "unpublished"
    if commit_with_rollback(f'Article "{post.title}" is now {status_str}.', 'success'):
        return redirect(url_for('admin.blog_posts'))
    return redirect(url_for('admin.blog_posts'))

@admin.route('/blog/toggle-featured/<int:id>', methods=['POST'])
@admin_required
def blog_toggle_featured(id):
    post = BlogPost.query.get_or_404(id)
    post.is_featured = not post.is_featured
    post.updated_at = datetime.utcnow()
    status_str = "featured at top" if post.is_featured else "unfeatured"
    if commit_with_rollback(f'Article "{post.title}" is now {status_str}.', 'success'):
        return redirect(url_for('admin.blog_posts'))
    return redirect(url_for('admin.blog_posts'))


# ---------------- ORDERS & REVIEWS ----------------
@admin.route('/orders')
@admin_required
def orders():
    orders_list = OrderRecord.query.order_by(OrderRecord.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders_list)


@admin.route('/orders/<int:id>/mark-in-progress', methods=['POST'])
@admin_required
def order_mark_in_progress(id):
    order = OrderRecord.query.get_or_404(id)
    order.status = 'In Progress'
    if commit_with_rollback('Order marked as In Progress.', 'success'):
        return redirect(url_for('admin.orders'))
    return redirect(url_for('admin.orders'))


@admin.route('/orders/<int:id>/mark-completed', methods=['POST'])
@admin_required
def order_mark_completed(id):
    order = OrderRecord.query.get_or_404(id)
    order.status = 'Completed'
    if commit_with_rollback('Order marked as Completed.', 'success'):
        return redirect(url_for('admin.orders'))
    return redirect(url_for('admin.orders'))

@admin.route('/comments')
@admin_required
def comments():
    comments_list = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template('admin/comments.html', comments=comments_list)


# ---------------- CONTACT INQUIRIES ----------------
@admin.route('/inquiries')
@admin_required
def inquiries():
    inquiries_list = ContactInquiry.query.order_by(ContactInquiry.created_at.desc()).all()
    unread_count = ContactInquiry.query.filter_by(is_read=False).count()
    return render_template('admin/inquiries.html', inquiries=inquiries_list, unread_count=unread_count)


@admin.route('/inquiries/<int:id>')
@admin_required
def inquiry_detail(id):
    inquiry = ContactInquiry.query.get_or_404(id)
    return render_template('admin/inquiry_detail.html', inquiry=inquiry)


@admin.route('/inquiries/<int:id>/mark-read', methods=['POST'])
@admin_required
def inquiry_mark_read(id):
    inquiry = ContactInquiry.query.get_or_404(id)
    inquiry.is_read = True
    if commit_with_rollback('Inquiry marked as read.', 'success'):
        return redirect(url_for('admin.inquiries'))
    return redirect(url_for('admin.inquiries'))


@admin.route('/inquiries/<int:id>/delete', methods=['POST'])
@admin_required
def inquiry_delete(id):
    inquiry = ContactInquiry.query.get_or_404(id)
    db.session.delete(inquiry)
    if commit_with_rollback('Inquiry deleted.', 'info'):
        return redirect(url_for('admin.inquiries'))
    return redirect(url_for('admin.inquiries'))


# ---------------- LANGUAGES & SETTINGS ----------------
@admin.route('/languages')
@admin_required
def languages():
    return render_template('admin/languages.html')

@admin.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    form = SettingForm()
    if request.method == 'GET':
        form.company_name.data = Setting.get_val('company_name', 'Yan Zhen Peptide')
        form.whatsapp_number.data = Setting.get_val('whatsapp_number', '85263294280')
        form.email.data = Setting.get_val('email', 'zhenyan640@gmail.com')
        form.address.data = Setting.get_val('address', 'Yan Zhen Biotechnology Facility, Cleanroom Suite 4')
        form.default_language.data = Setting.get_val('default_language', 'en')
        form.seo_title.data = Setting.get_val('seo_title', 'Yan Zhen Peptide | HPLC Certified Wholesale Peptides')
        form.meta_description.data = Setting.get_val('meta_description', 'High-purity laboratory research peptides with guaranteed >=99.8% purity.')

    if form.validate_on_submit():
        kv_pairs = {
            'company_name': form.company_name.data,
            'whatsapp_number': form.whatsapp_number.data,
            'email': form.email.data,
            'address': form.address.data,
            'default_language': form.default_language.data,
            'seo_title': form.seo_title.data,
            'meta_description': form.meta_description.data,
        }
        for key, value in kv_pairs.items():
            item = Setting.query.filter_by(key=key).first()
            if not item:
                item = Setting(key=key, value=str(value))
                db.session.add(item)
            else:
                item.value = str(value)
        if commit_with_rollback('System settings updated successfully.', 'success'):
            return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', form=form)


# --- SHIPMENT UPDATES MANAGEMENT ---
@admin.route('/shipments')
@admin_required
def shipments():
    shipment_list = ShipmentUpdate.query.order_by(ShipmentUpdate.created_at.desc()).all()
    return render_template('admin/shipments.html', shipments=shipment_list)

@admin.route('/shipments/create', methods=['GET', 'POST'])
@admin_required
def shipment_create():
    form = ShipmentUpdateForm()
    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            file = form.image.data
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            filename = f"shipment_{int(time.time())}.{ext}"
            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'shipments')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            image_filename = filename

        shipment = ShipmentUpdate(
            country=form.country.data.strip(),
            courier=form.courier.data.strip(),
            product_name=form.product_name.data.strip(),
            quantity=form.quantity.data.strip(),
            status=form.status.data,
            shipped_at=form.shipped_at.data.strip() if form.shipped_at.data else None,
            eta=form.eta.data.strip() if form.eta.data else None,
            note=form.note.data.strip() if form.note.data else None,
            image_filename=image_filename,
            is_published=form.is_published.data
        )
        db.session.add(shipment)
        if commit_with_rollback('Shipment update published successfully.', 'success'):
            return redirect(url_for('admin.shipments'))

    return render_template('admin/shipment_form.html', form=form, title="Add Global Shipment Update")

@admin.route('/shipments/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def shipment_edit(id):
    shipment = ShipmentUpdate.query.get_or_404(id)
    form = ShipmentUpdateForm(obj=shipment)
    if form.validate_on_submit():
        if form.image.data:
            file = form.image.data
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            filename = f"shipment_{int(time.time())}.{ext}"
            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'shipments')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            shipment.image_filename = filename

        shipment.country = form.country.data.strip()
        shipment.courier = form.courier.data.strip()
        shipment.product_name = form.product_name.data.strip()
        shipment.quantity = form.quantity.data.strip()
        shipment.status = form.status.data
        shipment.shipped_at = form.shipped_at.data.strip() if form.shipped_at.data else None
        shipment.eta = form.eta.data.strip() if form.eta.data else None
        shipment.note = form.note.data.strip() if form.note.data else None
        shipment.is_published = form.is_published.data

        if commit_with_rollback('Shipment update updated successfully.', 'success'):
            return redirect(url_for('admin.shipments'))

    return render_template('admin/shipment_form.html', form=form, shipment=shipment, title="Edit Shipment Update")

@admin.route('/shipments/<int:id>/delete', methods=['POST'])
@admin_required
def shipment_delete(id):
    shipment = ShipmentUpdate.query.get_or_404(id)
    db.session.delete(shipment)
    if commit_with_rollback('Shipment record deleted.', 'success'):
        return redirect(url_for('admin.shipments'))
    return redirect(url_for('admin.shipments'))

@admin.route('/shipments/<int:id>/toggle', methods=['POST'])
@admin_required
def shipment_toggle(id):
    shipment = ShipmentUpdate.query.get_or_404(id)
    shipment.is_published = not shipment.is_published
    if commit_with_rollback(f"Shipment published status set to {shipment.is_published}.", 'info'):
        return redirect(url_for('admin.shipments'))
    return redirect(url_for('admin.shipments'))
