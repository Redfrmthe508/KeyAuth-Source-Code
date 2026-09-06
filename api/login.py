"""POST /api/login — verify credentials. Pure-WSGI + Postgres (graceful)."""
import os

from _auth import (
    SCHEMA,
    configured,
    get_conn,
    hash_password,
    make_session_token,
    not_configured_response,
    read_json_body,
    session_cookie_header,
    wsgi_response,
)


def handler(environ, start_response):
    if environ.get("REQUEST_METHOD") not in ("POST",):
        return wsgi_response(start_response, {"success": False, "message": "Method not allowed."}, 405)
    if not configured():
        payload, status = not_configured_response()
        return wsgi_response(start_response, payload, status)

    data = read_json_body(environ)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    try:
        conn = get_conn()
    except Exception:
        return wsgi_response(start_response, {"success": False, "message": "Database unavailable — please try again shortly."}, 503)

    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute("SELECT salt, password_hash FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or hash_password(password, row[0]) != row[1]:
        return wsgi_response(start_response, {"success": False, "message": "Invalid username or password."}, 401)

    token = make_session_token(username, os.environ["AUTH_SECRET"])
    return wsgi_response(
        start_response,
        {"success": True, "message": "Logged in successfully!", "username": username},
        200,
        [session_cookie_header(token)],
    )


class _App:
    def __call__(self, environ, start_response):
        return handler(environ, start_response)


app = _App()
