"""POST /api/register — create an account in Neon Postgres."""
import secrets

from flask import Flask, request

from _auth import (
    configured,
    ensure_schema,
    error_response,
    get_conn,
    hash_password,
    issue_session,
    json_response,
)

app = Flask(__name__)


@app.route("/", methods=["POST"])
@app.route("/api/register", methods=["POST"])
def register():
    if not configured():
        return error_response(
            "Auth service is being set up — please try again in a few minutes.", 503
        )
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(username) < 3:
        return error_response("Username must be at least 3 characters.")
    if "@" not in email or "." not in email:
        return error_response("Enter a valid email address.")
    if len(password) < 12:
        return error_response("Password must be at least 12 characters.")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            ensure_schema(cur)
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return error_response("Username already taken.", 409)
            cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return error_response("An account with that email already exists.", 409)
            salt = secrets.token_hex(16)
            cur.execute(
                "INSERT INTO users (username, email, salt, password_hash) VALUES (%s, %s, %s, %s)",
                (username, email, salt, hash_password(password, salt)),
            )
        conn.commit()
    finally:
        conn.close()

    resp = json_response(
        {"success": True, "message": "Account created — welcome to KeyAuth!", "username": username},
        201,
    )
    return issue_session(resp, username)
