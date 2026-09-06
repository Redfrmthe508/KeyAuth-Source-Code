"""POST /api/logout — clear the session cookie. Self-contained pure-WSGI."""
import json


def handler(environ, start_response):
    data = json.dumps({"success": True}).encode()
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(data))),
            ("Cache-Control", "no-store"),
            (
                "Set-Cookie",
                "ka_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure",
            ),
        ],
    )
    return [data]


class _App:
    def __call__(self, environ, start_response):
        return handler(environ, start_response)


app = _App()
