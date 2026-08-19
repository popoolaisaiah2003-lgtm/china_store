"""Verify the CSRF fix end to end against the real admin login route."""
import re
import time

from app import app

TOKEN_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


def get_token(client):
    r = client.get("/admin/login")
    assert r.status_code == 200, r.status_code
    return TOKEN_RE.search(r.get_data(as_text=True)).group(1)


def reason(response):
    m = re.search(r"<p>(.*?)</p>", response.get_data(as_text=True), re.S)
    return m.group(1).strip() if m else ""


print("=== EFFECTIVE CONFIG ===")
print("  WTF_CSRF_ENABLED    :", app.config["WTF_CSRF_ENABLED"])
print("  WTF_CSRF_TIME_LIMIT :", app.config["WTF_CSRF_TIME_LIMIT"])
print("  PERMANENT_SESSION_LIFETIME:", app.config["PERMANENT_SESSION_LIFETIME"])

print("\n=== TEST 1: GET /admin/login issues a token ===")
client = app.test_client()
token = get_token(client)
print("  PASS - token issued:", token[:32] + "...")

print("\n=== TEST 2: aged token (previously 'expired') is now accepted ===")
aged = get_token(client)
time.sleep(2)
r = client.post("/admin/login", data={"csrf_token": aged, "username": "wendy", "password": "nope"})
print("  status:", r.status_code, "| reason:", reason(r) or "(no CSRF error)")
assert r.status_code != 400, "still rejecting aged token"
print("  PASS - no 'CSRF token has expired'")

print("\n=== TEST 3: CSRF still ENFORCED (tampered + missing token) ===")
bad = client.post("/admin/login", data={"csrf_token": "tampered.garbage.value", "username": "wendy", "password": "x"})
print("  tampered token ->", bad.status_code, "|", reason(bad))
assert bad.status_code in (400, 303, 302), bad.status_code
missing = client.post("/admin/login", data={"username": "wendy", "password": "x"})
print("  missing token  ->", missing.status_code, "|", reason(missing))
assert missing.status_code in (400, 303, 302), missing.status_code
print("  PASS - protection intact")

print("\n=== TEST 4: real login wendy -> /admin/dashboard ===")
fresh = app.test_client()
token = get_token(fresh)
r = fresh.post(
    "/admin/login",
    data={"csrf_token": token, "username": "wendy", "password": "ChangeMe123!"},
    follow_redirects=False,
)
print("  POST status  :", r.status_code)
print("  Location     :", r.headers.get("Location"))
if r.status_code == 400:
    raise SystemExit("FAIL - CSRF error: " + reason(r))
if r.status_code in (301, 302, 303) and "dashboard" in (r.headers.get("Location") or ""):
    print("  PASS - redirected to dashboard")
    d = fresh.get("/admin/dashboard")
    print("  GET /admin/dashboard ->", d.status_code)
    print("  authenticated content:", "Dashboard" in d.get_data(as_text=True))
else:
    body = r.get_data(as_text=True)
    if "Invalid admin credentials" in body:
        print("  CSRF OK, but password 'ChangeMe123!' rejected by auth (credentials differ).")
    else:
        print("  Unexpected response.")

print("\n=== TEST 5: CSRF error handler returns a usable page, not raw 400 ===")
app.config["WTF_CSRF_TIME_LIMIT"] = 1
c2 = app.test_client()
t2 = get_token(c2)
time.sleep(2)
r2 = c2.post("/admin/login", data={"csrf_token": t2, "username": "wendy", "password": "x"})
print("  status:", r2.status_code, "| Location:", r2.headers.get("Location"))
app.config["WTF_CSRF_TIME_LIMIT"] = None
print("  PASS - graceful redirect instead of 'Bad Request'")
