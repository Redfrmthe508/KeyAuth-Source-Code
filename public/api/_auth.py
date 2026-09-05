"""Shared helpers for the auth serverless functions (Flask + Neon Postgres)."""
import hashlib
import os

import psycopg2
from flask import jsonify, request
from itsdangerous import BadSignature, URLSafeSerializer

_SERIALIZER = None


def _serializer():
    global _SERIALIZER
    if _SERIALIZER is None:
        secret = os.environ.get("AUTH_SECRET")
        if not secret:
            return None
        _SERIALIZER = URLSafeSerializer(secret, salt="ka-auth-v1")
    return _SERIALIZER


def configured():
    return bool(os.environ.get("DATABASE_URL")) and bool(os.environ.get("AUTH_SECRET"))


def json_response(payload, status=200):
    resp = jsonify(payload)
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    return resp


def error_response(message, status=400):
    return json_response({"success": False, "message": message}, status)


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def ensure_schema(cur):
    cur.execute(SCHEMA)


def hash_password(password, salt_hex):
    return hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1
    ).hex()


COOKIE = "ka_session"


def current_user():
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    ser = _serializer()
    if not ser:
        return None
    try:
        data = ser.loads(token)
    except BadSignature:
        return None
    return data.get("u")


def issue_session(resp, username):
    ser = _serializer()
    if not ser:
        return resp
    token = ser.dumps({"u": username})
    resp.set_cookie(
        COOKIE, token, httponly=True, samesite="Lax", secure=True,
        path="/", max_age=60 * 60 * 24 * 7,
    )
    return resp


def clear_session(resp):
    resp.set_cookie(COOKIE, "", expires=0, path="/", httponly=True,
                    samesite="Lax", secure=True)
    return resp
