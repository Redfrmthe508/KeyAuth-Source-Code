"""POST /api/forgot — acknowledge a password-reset request.

Fully self-contained (no sibling imports) so serverless bundlers
include everything needed. Returns a generic response without
revealing whether the account exists.
"""
import json


def handler(environ, start_response):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body = json.loads(environ["wsgi.input"].read(length) or b"{}")
        email = str(body.get("email", "")).strip()
    except Exception:
        email = ""

    if "@" not in email or "." not in email:
        payload = {"success": False, "message": "Enter a valid email address."}
        status = "400 Bad Request"
    else:
        payload = {
            "success": True,
            "message": "If that account exists, a reset link is on its way. Check your inbox.",
        }
        status = "200 OK"

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


# Vercel-style ASGI/WSGI app export
class _App:
    def __call__(self, environ, start_response):
        return handler(environ, start_response)


app = _App()
