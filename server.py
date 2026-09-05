#!/usr/bin/env python3
"""Static file server + working demo auth for the Freebuff preview.

Serves the site exactly like `python3 -m http.server`, plus JSON auth
endpoints backed by a small JSON store (passwords hashed with scrypt).

On a real PHP + MySQL host, the original index.php files take priority
over the .html pages and this server is not used.
"""
import hashlib
import json
import os
import secrets
import threading
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", "8080"))
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
LOCK = threading.Lock()


def _transpile_tsx(rel_path):
    """Compile a TSX entry to JS with esbuild (ships with Vite)."""
    import subprocess

    src = os.path.join(ROOT, rel_path.lstrip("/"))
    if not os.path.exists(src):
        return None, "// not found"
    out = src + ".out.js"
    cache = src + ".esbuild-cache"
    mtime = os.path.getmtime(src)
    if os.path.exists(cache):
        try:
            with open(cache) as fh:
                cached_mtime = float(fh.read().strip())
            if cached_mtime == mtime and os.path.exists(out):
                with open(out) as fh:
                    return out, None
        except Exception:
            pass
    result = subprocess.run(
        [
            os.path.join(ROOT, "node_modules", ".bin", "esbuild"),
            src,
            "--bundle",
            "--format=esm",
            "--target=es2020",
            "--jsx=automatic",
            f"--outfile={out}",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        return None, "//" + result.stderr[:2000]
    with open(cache, "w") as fh:
        fh.write(str(mtime))
    return out, None

os.makedirs(DATA_DIR, exist_ok=True)
for _f in (USERS_FILE, SESSIONS_FILE):
    if not os.path.exists(_f):
        with open(_f, "w") as _fh:
            json.dump({}, _fh)


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def _hash_password(password, salt_hex):
    return hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1
    ).hex()


class Handler(SimpleHTTPRequestHandler):

    # ---------- helpers ----------

    def _json(self, payload, status=200, set_cookie=None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)

    def _session_user(self):
        raw = self.headers.get("Cookie", "")
        try:
            jar = cookies.SimpleCookie(raw)
        except Exception:
            return None
        if "ka_session" not in jar:
            return None
        with LOCK:
            sessions = _load(SESSIONS_FILE)
        info = sessions.get(jar["ka_session"].value)
        return info.get("username") if info else None

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return None

    # ---------- routes ----------

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/me":
            user = self._session_user()
            if user:
                self._json({"success": True, "username": user})
            else:
                self._json({"success": False}, 401)
            return
        if path in ("/app/", "/app/index.html") and not self._session_user():
            self.send_response(302)
            self.send_header("Location", "/login/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        # Serve compiled JS for TSX module requests (preview only).
        if path.startswith("/src/react/") and path.endswith(".tsx"):
            out, err = _transpile_tsx(path)
            if out is None:
                body = (err or "// transpile error").encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/javascript")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                with open(out, "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                pass
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        # Legacy form posts (e.g. /login/index.php): redirect to the styled
        # static page instead of returning an ugly 501 error.
        if not path.startswith("/api/"):
            self._read_json()  # drain body so the connection stays healthy
            target = path.rsplit("/", 1)[0] + "/"
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        payload = self._read_json()
        if payload is None:
            return self._json({"success": False, "message": "Invalid JSON."}, 400)

        if path == "/api/register":
            username = str(payload.get("username", "")).strip()
            email = str(payload.get("email", "")).strip().lower()
            password = str(payload.get("password", ""))
            if len(username) < 3:
                return self._json({"success": False, "message": "Username must be at least 3 characters."}, 400)
            if "@" not in email or "." not in email:
                return self._json({"success": False, "message": "Enter a valid email address."}, 400)
            if len(password) < 12:
                return self._json({"success": False, "message": "Password must be at least 12 characters."}, 400)
            with LOCK:
                users = _load(USERS_FILE)
                if username in users:
                    return self._json({"success": False, "message": "Username already taken."}, 409)
                salt = secrets.token_hex(16)
                users[username] = {
                    "email": hashlib.sha256(email.encode()).hexdigest(),
                    "salt": salt,
                    "password": _hash_password(password, salt),
                }
                _save(USERS_FILE, users)
            return self._set_session(username, 201, "Account created — welcome to KeyAuth!")

        if path == "/api/login":
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            with LOCK:
                users = _load(USERS_FILE)
            record = users.get(username)
            if not record or _hash_password(password, record["salt"]) != record["password"]:
                return self._json({"success": False, "message": "Invalid username or password."}, 401)
            return self._set_session(username, 200, "Logged in successfully!")

        if path == "/api/forgot":
            return self._json({
                "success": True,
                "message": "If that account exists, a reset link is on its way. Check your inbox.",
            })

        if path == "/api/logout":
            try:
                jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
                token = jar["ka_session"].value
                with LOCK:
                    sessions = _load(SESSIONS_FILE)
                    sessions.pop(token, None)
                    _save(SESSIONS_FILE, sessions)
            except Exception:
                pass
            return self._json({"success": True}, set_cookie="ka_session=; Path=/; Max-Age=0")

        return self._json({"success": False, "message": "Unknown endpoint."}, 404)

    def _set_session(self, username, status, message):
        token = secrets.token_hex(32)
        with LOCK:
            sessions = _load(SESSIONS_FILE)
            sessions[token] = {"username": username}
            _save(SESSIONS_FILE, sessions)
        self._json(
            {"success": True, "message": message, "username": username},
            status,
            set_cookie=f"ka_session={token}; Path=/; HttpOnly; SameSite=Lax",
        )

    def log_message(self, fmt, *args):
        pass  # keep preview logs clean


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
