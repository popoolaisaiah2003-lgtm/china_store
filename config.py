import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'yan-zhen-peptide-production-secret-2026'
    
    # Database Connection (Handles Railway DATABASE_URL / MYSQL_URL or local fallback)
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL') or os.environ.get('MYSQLURL')
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        elif db_url.startswith('mysql://'):
            db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@127.0.0.1/yan_zhen_peptide?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Unicode & Emoji Connection Options
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'charset': 'utf8mb4'}
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
