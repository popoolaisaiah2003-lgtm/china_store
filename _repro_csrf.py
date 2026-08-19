"""Reproduce the admin login CSRF failure. Read-only: no DB writes."""
import re
import time
from itsdangerous import URLSafeTimedSerializer

from app import app
from flask_wtf.csrf import generate_csrf

print("=== CONFIG SNAPSHOT ===")
for key in (
    "SECRET_KEY",
    "WTF_CSRF_TIME_LIMIT",
    "WTF_CSRF_SECRET_KEY",
    "WTF_CSRF_ENABLED",
    "WTF_CSRF_SSL_STRICT",
    "PERMANENT_SESSION_LIFETIME",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_SAMESITE",
    "SESSION_REFRESH_EACH_REQUEST",
):
    present = key in app.config
    print(f"  {key:32} present={present!s:5} value={app.config.get(key)!r}")

print("\n=== SECRET_KEY STABILITY ACROSS create_app() CALLS ===")
from app import create_app
k1 = create_app().config["SECRET_KEY"]
k2 = create_app().config["SECRET_KEY"]
print("  create_app #1 :", repr(k1[:12] + "..."))
print("  create_app #2 :", repr(k2[:12] + "..."))
print("  stable        :", k1 == k2 == app.config["SECRET_KEY"])

print("\n=== TOKEN AGE DECODE ===")
with app.test_request_context():
    tok = generate_csrf()
    s = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="wtf-csrf-token")
    raw, ts = s.loads(tok, return_timestamp=True)
    print("  token issued at :", ts)
    print("  now             :", time.strftime("%Y-%m-%d %H:%M:%S"))

print("\n=== LIVE GET/POST /admin/login ===")
client = app.test_client()
r = client.get("/admin/login")
print("  GET status:", r.status_code)
html = r.get_data(as_text=True)
m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
token = m.group(1) if m else None
print("  token extracted:", (token[:40] + "...") if token else "NONE FOUND")

r2 = client.post(
    "/admin/login",
    data={"csrf_token": token, "username": "wendy", "password": "wrong-on-purpose"},
    follow_redirects=False,
)
print("  POST status:", r2.status_code)
body = r2.get_data(as_text=True)
if r2.status_code == 400:
    reason = re.search(r"<p>(.*?)</p>", body, re.S)
    print("  400 REASON:", reason.group(1).strip() if reason else body[:300])
else:
    print("  CSRF accepted (no 400).")
    if "Invalid admin credentials" in body:
        print("  -> reached auth logic: 'Invalid admin credentials'")
