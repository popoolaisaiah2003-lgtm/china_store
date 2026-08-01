import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'yan-zhen-peptide-production-secret-2026'
    
    db_url = (
        os.environ.get('DATABASE_URL')
        or os.environ.get('MYSQL_URL')
        or os.environ.get('MYSQLURL')
    )

    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        elif db_url.startswith('mysql://'):
            db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)

        SQLALCHEMY_DATABASE_URI = db_url
    else:
        instance_dir = os.path.join(basedir, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_dir, 'yan_zhen_peptide.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options without charset connect_args to support PostgreSQL & MySQL seamlessly
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }

    # Upload Directories
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    PRODUCT_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'products')
    BLOG_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'blog')
    COA_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'coa')
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    WHATSAPP_NUMBER = '85263294280'
    BUSINESS_EMAIL = 'zhenyan640@gmail.com'
    BRAND_NAME = 'Yan Zhen Peptide'

    # Session & Security Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
