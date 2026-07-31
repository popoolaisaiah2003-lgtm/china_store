from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email, EqualTo

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In to Dashboard')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password *', validators=[DataRequired()])
    new_password = PasswordField('New Password *', validators=[DataRequired(), Length(min=8, max=64)])
    confirm_password = PasswordField('Confirm New Password *', validators=[
        DataRequired(),
        EqualTo('new_password', message='New passwords must match.')
    ])
    submit = SubmitField('Update Password')


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Category')


class ProductForm(FlaskForm):
    category_id = SelectField('Category *', coerce=int, validators=[DataRequired(message="Please select a product category.")])
    name = StringField('Product Name *', validators=[DataRequired(message="Product name is required."), Length(max=150)])
    purity = StringField('Purity Grade (e.g. >= 99.8%)', validators=[Optional()], default='>= 99.8%')
    molecular_formula = StringField('Molecular Formula', validators=[Optional()])
    sequence_or_cas = StringField('Sequence / CAS Number / Product Code', validators=[Optional()])
    price = FloatField('Price ($ USD) *', validators=[DataRequired(message="Please enter a valid price."), NumberRange(min=0)])
    short_description = StringField('Short Specification Summary', validators=[Optional(), Length(max=255)])
    description = TextAreaField('Detailed Specification & Description', validators=[Optional()])
    storage_info = StringField('Storage Information', validators=[Optional()], default='-20°C Desiccated / Climate Controlled')
    stock_status = SelectField('Stock Status', choices=[
        ('In Stock', 'In Stock'),
        ('Limited Stock', 'Limited Stock'),
        ('Out of Stock', 'Out of Stock')
    ], default='In Stock')
    is_featured = BooleanField('Feature on Homepage')
    image = FileField('Main Product Image', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'svg'], 'Images only!')])
    submit = SubmitField('Save Product')


class COAForm(FlaskForm):
    product_id = SelectField('Related Product *', coerce=int, validators=[DataRequired()])
    batch_number = StringField('Batch / Lot Number *', validators=[DataRequired(), Length(max=100)])
    issue_date = StringField('Issue Date *', validators=[DataRequired(), Length(max=50)])
    coa_pdf = FileField('COA Document (PDF/Image) *', validators=[FileAllowed(['pdf', 'jpg', 'png', 'jpeg'], 'PDF or Images only!')])
    preview_image = FileField('Optional Certificate Preview Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Images only!')])
    active = BooleanField('Activate / Publish COA', default=True)
    submit = SubmitField('Upload Certificate of Analysis')


class BlogPostForm(FlaskForm):
    title = StringField('Article Title *', validators=[DataRequired(message="Article title is required."), Length(max=200)])
    slug = StringField('URL Slug', validators=[Optional(), Length(max=220)])
    summary = TextAreaField('Executive Summary / Excerpt', validators=[Optional()])
    content = TextAreaField('Full Body Content *', validators=[DataRequired(message="Article body content is required.")])
    image = FileField('Cover Image', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Images only!')])
    seo_title = StringField('SEO Title', validators=[Optional(), Length(max=200)])
    meta_description = StringField('Meta Description', validators=[Optional(), Length(max=255)])
    language = SelectField('Article Language', choices=[
        ('en', 'English'),
        ('zh', 'Chinese (中文)'),
        ('es', 'Spanish (Español)'),
        ('ar', 'Arabic (العربية)'),
        ('fr', 'French (Français)')
    ], default='en')
    tags = StringField('Tags (comma separated)', validators=[Optional()])
    is_published = BooleanField('Publish Article Immediately', default=True)
    is_featured = BooleanField('Feature at Top of Blog', default=False)
    submit = SubmitField('Save Blog Post')


COUNTRY_CHOICES = [
    ('', 'Select Country...'),
    ('Nigeria', 'Nigeria'),
    ('Ireland', 'Ireland'),
    ('United States', 'United States'),
    ('United Kingdom', 'United Kingdom'),
    ('Canada', 'Canada'),
    ('Australia', 'Australia'),
    ('Germany', 'Germany'),
    ('France', 'France'),
    ('Italy', 'Italy'),
    ('Spain', 'Spain'),
    ('Netherlands', 'Netherlands'),
    ('Switzerland', 'Switzerland'),
    ('Sweden', 'Sweden'),
    ('Norway', 'Norway'),
    ('Denmark', 'Denmark'),
    ('Finland', 'Finland'),
    ('Belgium', 'Belgium'),
    ('Austria', 'Austria'),
    ('Poland', 'Poland'),
    ('Czech Republic', 'Czech Republic'),
    ('Portugal', 'Portugal'),
    ('Greece', 'Greece'),
    ('Japan', 'Japan'),
    ('South Korea', 'South Korea'),
    ('Singapore', 'Singapore'),
    ('United Arab Emirates', 'United Arab Emirates'),
    ('Saudi Arabia', 'Saudi Arabia'),
    ('Qatar', 'Qatar'),
    ('Kuwait', 'Kuwait'),
    ('Israel', 'Israel'),
    ('Turkey', 'Turkey'),
    ('Brazil', 'Brazil'),
    ('Mexico', 'Mexico'),
    ('Argentina', 'Argentina'),
    ('Chile', 'Chile'),
    ('Colombia', 'Colombia'),
    ('South Africa', 'South Africa'),
    ('New Zealand', 'New Zealand'),
    ('India', 'India'),
    ('Malaysia', 'Malaysia'),
    ('Thailand', 'Thailand'),
    ('Vietnam', 'Vietnam'),
    ('Indonesia', 'Indonesia'),
    ('Philippines', 'Philippines'),
    ('Hong Kong SAR', 'Hong Kong SAR'),
    ('Taiwan', 'Taiwan'),
    ('China', 'China'),
    ('Other / International Destination', 'Other Country (Specify in Address)')
]


class CheckoutForm(FlaskForm):
    full_name = StringField('Full Name *', validators=[DataRequired(message="Full Name is required"), Length(max=100)])
    email = StringField('Email Address *', validators=[DataRequired(message="Email Address is required"), Email(message="Please enter a valid email address"), Length(max=120)])
    country = SelectField('Country *', choices=COUNTRY_CHOICES, validators=[DataRequired(message="Please select your shipping country")])
    zip_code = StringField('ZIP / Postal Code', validators=[Optional(), Length(max=30)])
    address = TextAreaField('Shipping Address *', validators=[DataRequired(message="Shipping Address is required"), Length(max=300)])
    phone = StringField('Phone Number *', validators=[DataRequired(message="Phone Number is required"), Length(max=30)])
    submit = SubmitField('Generate Wholesale Order on WhatsApp')


class SettingForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired()], default='Yan Zhen Peptide')
    whatsapp_number = StringField('WhatsApp Support Number', validators=[DataRequired()], default='85263294280')
    email = StringField('Contact Email', validators=[Optional()])
    address = StringField('Facility Address', validators=[Optional()])
    default_language = SelectField('Default Site Language', choices=[
        ('en', 'English'),
        ('zh', 'Chinese (中文)'),
        ('es', 'Spanish'),
        ('ar', 'Arabic'),
        ('fr', 'French')
    ], default='en')
    seo_title = StringField('Default SEO Meta Title', validators=[Optional()])
    meta_description = TextAreaField('Default SEO Meta Description', validators=[Optional()])
    submit = SubmitField('Save System Settings')


class ShipmentUpdateForm(FlaskForm):
    country = StringField('Destination Country *', validators=[DataRequired(), Length(max=100)])
    courier = StringField('Courier Service / Logistics *', validators=[DataRequired(), Length(max=100)])
    product_name = StringField('Product(s) Included *', validators=[DataRequired(), Length(max=200)])
    quantity = StringField('Quantity / Units *', validators=[DataRequired(), Length(max=100)])
    status = SelectField('Shipment Status *', choices=[
        ('Processing', 'Processing'),
        ('Dispatched', 'Dispatched'),
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
        ('Issue', 'Issue')
    ], default='Dispatched', validators=[DataRequired()])
    shipped_at = StringField('Shipped Date', validators=[Optional(), Length(max=100)])
    eta = StringField('Estimated Delivery (ETA)', validators=[Optional(), Length(max=100)])
    note = TextAreaField('Dispatch Note / Remarks', validators=[Optional(), Length(max=500)])
    image = FileField('Upload Parcel / Tracking Photo', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')])
    is_published = BooleanField('Publish to Public Site', default=True)
    submit = SubmitField('Save Shipment Update')
