import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'qS1LlujIc4F40akOT20n8wIwZZlIK9L8eoJS1RkSIVwmmrX-_6HgfHLOl6ixPjvc'

    # MySQL-only database configuration (local XAMPP default, Railway override via DATABASE_URL).
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:@localhost/china_store_db')
    if SQLALCHEMY_DATABASE_URI.startswith('mysql://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('mysql://', 'mysql+pymysql://', 1)

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
