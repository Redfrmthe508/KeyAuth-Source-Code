"""POST /api/login — verify credentials and start a session."""
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
@app.route("/api/login", methods=["POST"])
def login():
    if not configured():
        return error_response(
            "Auth service is being set up — please try again in a few minutes.", 503
        )
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            ensure_schema(cur)
            cur.execute("SELECT salt, password_hash FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or hash_password(password, row[0]) != row[1]:
        return error_response("Invalid username or password.", 401)

    resp = json_response({"success": True, "message": "Logged in successfully!", "username": username})
    return issue_session(resp, username)
