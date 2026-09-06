"""POST /api/register — create an account. Pure-WSGI + Postgres (graceful)."""
import secrets

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
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(username) < 3:
        return wsgi_response(start_response, {"success": False, "message": "Username must be at least 3 characters."}, 400)
    if "@" not in email or "." not in email:
        return wsgi_response(start_response, {"success": False, "message": "Enter a valid email address."}, 400)
    if len(password) < 12:
        return wsgi_response(start_response, {"success": False, "message": "Password must be at least 12 characters."}, 400)

    try:
        conn = get_conn()
    except Exception:
        return wsgi_response(start_response, {"success": False, "message": "Database unavailable — please try again shortly."}, 503)

    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return wsgi_response(start_response, {"success": False, "message": "Username already taken."}, 409)
            cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return wsgi_response(start_response, {"success": False, "message": "An account with that email already exists."}, 409)
            salt = secrets.token_hex(16)
            cur.execute(
                "INSERT INTO users (username, email, salt, password_hash) VALUES (%s, %s, %s, %s)",
                (username, email, salt, hash_password(password, salt)),
            )
        conn.commit()
    finally:
        conn.close()

    token = make_session_token(username, __import__("os").environ["AUTH_SECRET"])
    return wsgi_response(
        start_response,
        {"success": True, "message": "Account created — welcome to KeyAuth!", "username": username},
        201,
        [session_cookie_header(token)],
    )


class _App:
    def __call__(self, environ, start_response):
        return handler(environ, start_response)


app = _App()
