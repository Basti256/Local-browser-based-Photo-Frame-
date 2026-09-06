"""Authentifizierung: Argon2id-Hash, Session-Cookie, Login-Rate-Limit."""
from __future__ import annotations

import json
import secrets
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from server.paths import AUTH_FILE, SECRET_FILE, ensure_data_dir

COOKIE_NAME = "pf_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7
SESSION_SALT = "photo-frame-session"
SETUP_USERNAME = "Admin"
MIN_PASSWORD_LEN = 10
LOGIN_WINDOW_SEC = 15 * 60
LOGIN_MAX_FAILURES = 5

_hasher = PasswordHasher()
_failures: dict[str, list[float]] = {}


def _secret() -> str:
    ensure_data_dir()
    if SECRET_FILE.is_file():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    value = secrets.token_hex(32)
    SECRET_FILE.write_text(value + "\n", encoding="utf-8")
    try:
        SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return value


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret(), salt=SESSION_SALT)


def load_auth() -> dict[str, Any] | None:
    if not AUTH_FILE.is_file():
        return None
    with AUTH_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    if not data.get("password_hash"):
        return None
    data["username"] = SETUP_USERNAME
    return data


def has_user() -> bool:
    return load_auth() is not None


def validate_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Passwort mindestens {MIN_PASSWORD_LEN} Zeichen.",
        )
    if password.lower() == SETUP_USERNAME.lower():
        raise HTTPException(status_code=400, detail="Passwort darf nicht dem Benutzernamen entsprechen.")
    return password


def create_user(password: str) -> None:
    if has_user():
        raise HTTPException(status_code=409, detail="Benutzer ist bereits eingerichtet.")
    password = validate_password(password)
    ensure_data_dir()
    payload = {
        "username": SETUP_USERNAME,
        "password_hash": _hasher.hash(password),
    }
    with AUTH_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    try:
        AUTH_FILE.chmod(0o600)
    except OSError:
        pass


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def login_allowed(request: Request) -> bool:
    key = _client_key(request)
    now = time.time()
    stamps = [t for t in _failures.get(key, []) if now - t < LOGIN_WINDOW_SEC]
    _failures[key] = stamps
    return len(stamps) < LOGIN_MAX_FAILURES


def record_login_failure(request: Request) -> None:
    key = _client_key(request)
    _failures.setdefault(key, []).append(time.time())


def clear_login_failures(request: Request) -> None:
    _failures.pop(_client_key(request), None)


def set_session(response: Response, request: Request) -> None:
    token = _serializer().dumps({"u": SETUP_USERNAME})
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "") == "https"
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def session_username(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or not load_auth():
        return None
    return SETUP_USERNAME


def same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    base = str(request.base_url).rstrip("/")
    return origin.rstrip("/") == base
