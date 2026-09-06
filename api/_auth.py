"""Shared auth core for register/login — stdlib only, pure WSGI.

Postgres access uses psycopg2 when available; if the driver or env vars
are missing the endpoints return a clean 503 JSON instead of crashing.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets

COOKIE = "ka_session"

try:
    import psycopg2  # type: ignore

    HAS_DB = True
except Exception:  # driver not installed in the runtime image
    psycopg2 = None
    HAS_DB = False


def configured():
    return HAS_DB and bool(os.environ.get("DATABASE_URL")) and bool(os.environ.get("AUTH_SECRET"))


STATUS_TEXT = {
    200: "200 OK",
    201: "201 Created",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    405: "405 Method Not Allowed",
    409: "409 Conflict",
    500: "500 Internal Server Error",
    503: "503 Service Unavailable",
}


def wsgi_response(start_response, payload, status=200, extra_headers=None):
    data = json.dumps(payload).encode()
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(data))),
        ("Cache-Control", "no-store"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(STATUS_TEXT.get(status, f"{status} Status"), headers)
    return [data]


def read_json_body(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        return json.loads(environ["wsgi.input"].read(length) or b"{}")
    except Exception:
        return {}


def not_configured_response():
    return (
        {"success": False, "message": "Auth service is being set up — please try again in a few minutes."},
        503,
    )


def hash_password(password, salt_hex):
    return hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1
    ).hex()


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")


SCHEMA = (
    "CREATE TABLE IF NOT EXISTS users ("
    "id SERIAL PRIMARY KEY,"
    "username TEXT UNIQUE NOT NULL,"
    "email TEXT NOT NULL,"
    "salt TEXT NOT NULL,"
    "password_hash TEXT NOT NULL,"
    "created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
)


# ---------- signed session cookie (stdlib HMAC) ----------

def _sign(value, secret):
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def make_session_token(username, secret):
    payload = base64.urlsafe_b64encode(
        json.dumps({"u": username}).encode()
    ).decode().rstrip("=")
    return f"{payload}.{_sign(payload, secret)}"


def session_user(environ, secret=None):
    secret = secret or os.environ.get("AUTH_SECRET")
    if not secret:
        return None
    token = None
    for part in environ.get("HTTP_COOKIE", "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            if k == COOKIE:
                token = v
                break
    if not token or "." not in token:
        return None
    payload_b64, sig = token.rsplit(".", 1)
    try:
        if not hmac.compare_digest(sig, _sign(payload_b64, secret)):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        return data.get("u")
    except Exception:
        return None


def session_cookie_header(token):
    return (
        f"Set-Cookie: {COOKIE}={token}; Path=/; Max-Age=604800; "
        "HttpOnly; SameSite=Lax; Secure"
    )


def clear_cookie_header():
    return f"Set-Cookie: {COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure"
