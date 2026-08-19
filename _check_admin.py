"""Read-only check that the admin account exists. No writes."""
from app import app
from models import Admin

with app.app_context():
    for a in Admin.query.all():
        print(f"  username={a.username!r}  last_login={a.last_login}")
