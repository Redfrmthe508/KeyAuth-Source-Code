"""GET /api/me — return the signed-in user from the session cookie."""
from flask import Flask

from _auth import current_user, json_response

app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/api/me", methods=["GET"])
def me():
    username = current_user()
    if not username:
        return json_response({"success": False}, 401)
    return json_response({"success": True, "username": username})
