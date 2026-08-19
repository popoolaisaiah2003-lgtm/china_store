"""Prove the exact mechanism behind 'The CSRF token has expired.' Read-only."""
import re
import time

from app import app

app.config["WTF_CSRF_TIME_LIMIT"] = 1  # simulate an aged token quickly

client = app.test_client()
r = client.get("/admin/login")
token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.get_data(as_text=True)).group(1)
print("GET ok, token acquired.")

time.sleep(2)  # token now older than the 1s limit

r2 = client.post(
    "/admin/login",
    data={"csrf_token": token, "username": "wendy", "password": "x"},
)
print("POST status:", r2.status_code)
body = r2.get_data(as_text=True)
msg = re.search(r"<p>(.*?)</p>", body, re.S)
print("Reason:", msg.group(1).strip() if msg else body[:200])
