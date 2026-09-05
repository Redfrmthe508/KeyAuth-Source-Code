"""POST /api/forgot — acknowledge a password-reset request.

Email delivery is not wired up yet, so this always returns a generic
response without revealing whether the account exists.
"""
from flask import Flask, request

from _auth import json_response

app = Flask(__name__)


@app.route("/", methods=["POST"])
@app.route("/api/forgot", methods=["POST"])
def forgot():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    if "@" not in email or "." not in email:
        return json_response({"success": False, "message": "Enter a valid email address."}, 400)
    return json_response({
        "success": True,
        "message": "If that account exists, a reset link is on its way. Check your inbox.",
    })
