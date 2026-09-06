"""GET /api/me — return the signed-in user from the session cookie.

Self-contained pure-WSGI function. Session is a signed cookie
(HMAC-SHA256 over the payload) verified with AUTH_SECRET.
"""
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qs


def _sign(value, secret):
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _session_user(environ):
    secret = os.environ.get("AUTH_SECRET")
    if not secret:
        return None
    raw = environ.get("HTTP_COOKIE", "")
    token = None
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            if k == "ka_session":
                token = v
                break
    if not token or "." not in token:
        return None
    payload_b64, sig = token.rsplit(".", 1)
    try:
        expected = _sign(payload_b64, secret)
        if not hmac.compare_digest(sig, expected):
            return None
        import base64

        data = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        return data.get("u")
    except Exception:
        return None


def handler(environ, start_response):
    username = _session_user(environ)
    if username:
        payload, status = {"success": True, "username": username}, "200 OK"
    else:
        payload, status = {"success": False}, "401 Unauthorized"

    data = json.dumps(payload).encode()
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(data))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [data]


class _App:
    def __call__(self, environ, start_response):
        return handler(environ, start_response)


app = _App()
