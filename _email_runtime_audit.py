from app import app
from models import Setting

with app.app_context():
    for key in ('email', 'business_email'):
        item = Setting.query.filter_by(key=key).first()
        print(f'{key}={item.value if item else None}')
