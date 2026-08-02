from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', backref='category', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True)
    purity = db.Column(db.String(50), default='>= 99.8%')
    molecular_formula = db.Column(db.String(100), nullable=True)
    sequence_or_cas = db.Column(db.String(150), nullable=True)
    short_description = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock_status = db.Column(db.String(50), default='In Stock')
    is_featured = db.Column(db.Boolean, default=False)
    storage_info = db.Column(db.String(255), default='-20°C Desiccated / Climate Controlled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    images = db.relationship('ProductImage', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    coas = db.relationship('COA', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def primary_image(self):
        return ProductImage.query.filter_by(product_id=self.id, is_primary=True).first()

    @property
    def catalog_image(self):
        if self.primary_image:
            return f"uploads/products/{self.primary_image.image_filename}"
        
        name_lower = self.name.lower() if self.name else ''
        cat_name = self.category.name.lower() if (self.category and self.category.name) else ''

        # 1. GLP-1 Products (Blue-cap vial renders)
        if any(k in name_lower for k in ['semaglutide', 'tirzepatide', 'retatrutide', 'cagrilintide', 'mazdutide']) or 'glp' in cat_name:
            if 'semaglutide' in name_lower:
                return 'images/products/glp1/semaglutide.jpg'
            elif 'tirzepatide' in name_lower:
                return 'images/products/glp1/tirzepatide.jpg'
            elif 'retatrutide' in name_lower:
                return 'images/products/glp1/retatrutide.jpg'
            else:
                return 'images/products/glp1/glp1-blue.jpg'

        # 2. Healing & Recovery (Silver-cap vial renders)
        elif any(k in name_lower for k in ['bpc', 'tb-500', 'tb500', 'kpv', 'ghk']) or 'recovery' in cat_name or 'healing' in cat_name:
            if 'bpc' in name_lower:
                return 'images/products/healing/bpc157.jpg'
            else:
                return 'images/products/healing/healing-silver.jpg'

        # 3. Growth Hormone & Secretagogues (Dark-blue cap vial renders)
        elif any(k in name_lower for k in ['cjc', 'ipamorelin', 'tesamorelin', 'hgh', 'somatropin']) or 'growth' in cat_name:
            if 'hgh' in name_lower or 'somatropin' in name_lower:
                return 'images/products/gh/hgh.jpg'
            else:
                return 'images/products/gh/gh-darkblue.jpg'

        # 4. Wellness & Nootropic Peptides (White-cap vial renders)
        elif any(k in name_lower for k in ['nad', 'glutathione', 'selank', 'semax', 'epithalon']) or 'wellness' in cat_name or 'pigmentation' in cat_name:
            return 'images/products/wellness/wellness-white.jpg'

        # 5. Other / Fallback
        else:
            return 'images/products/other/peptide-generic.jpg'

    @property
    def latest_coa(self):
        return self.coas.filter_by(active=True).order_by(COA.issue_date.desc()).first()

    def __repr__(self):
        return f'<Product {self.name}>'


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ProductImage {self.image_filename}>'


class COA(db.Model):
    __tablename__ = 'coas'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_number = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.String(50), nullable=False)
    file_url = db.Column(db.String(255), nullable=False)
    preview_image = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<COA {self.batch_number}>'


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False, unique=True)
    summary = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    seo_title = db.Column(db.String(200), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(10), default='en')
    tags = db.Column(db.String(200), nullable=True)
    is_published = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def image_url(self):
        if self.image_filename:
            if self.image_filename.startswith('uploads/') or self.image_filename.startswith('images/'):
                return self.image_filename
            return f"uploads/blog/{self.image_filename}"
        return "images/blog-placeholder.jpg"

    def __repr__(self):
        return f'<BlogPost {self.title}>'


class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False, default='International')
    rating = db.Column(db.Integer, default=5)
    review_text = db.Column(db.Text, nullable=False)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Legacy columns retained so the app can migrate safely without downtime.
    reviewer_name = db.Column(db.String(100), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.Boolean, default=True)

    product = db.relationship('Product', backref='reviews')

    @property
    def display_name(self):
        return self.customer_name or self.reviewer_name or 'Anonymous'

    @property
    def display_text(self):
        return self.review_text or self.comment or ''


class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'), nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrderRecord(db.Model):
    __tablename__ = 'order_records'
    
    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_country = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(30), nullable=True)
    customer_address = db.Column(db.Text, nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    grand_total = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    @classmethod
    def get_val(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        return item.value if item else default

    @classmethod
    def set_val(cls, key, value):
        item = cls.query.filter_by(key=key).first()
        if not item:
            item = cls(key=key, value=str(value))
            db.session.add(item)
        else:
            item.value = str(value)
        db.session.commit()


class ShipmentUpdate(db.Model):
    __tablename__ = 'shipment_updates'

    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), nullable=False)
    courier = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Dispatched')
    shipped_at = db.Column(db.String(100), nullable=True)
    eta = db.Column(db.String(100), nullable=True)
    note = db.Column(db.Text, nullable=True)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ShipmentUpdate {self.country} - {self.product_name}>'
