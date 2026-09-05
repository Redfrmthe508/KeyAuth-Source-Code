"""POST /api/logout — clear the session cookie."""
from flask import Flask

from _auth import clear_session, json_response

app = Flask(__name__)


@app.route("/", methods=["POST"])
@app.route("/api/logout", methods=["POST"])
def logout():
    return clear_session(json_response({"success": True}))
