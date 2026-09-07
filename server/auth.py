"""Authentifizierung: Argon2id-Hash, Session-Cookie. Sperre nach Fehlversuchen in lockout."""
from __future__ import annotations

import json
import secrets
from typing import Any
from urllib.parse import urlparse

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

_hasher = PasswordHasher()


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


def _host_key(netloc: str) -> tuple[str, str]:
    host = (netloc or "").strip().lower().rstrip(".")
    if host.startswith("["):
        end = host.find("]")
        name = host[: end + 1] if end != -1 else host
        return name, host
    if host.count(":") == 1:
        return host.split(":", 1)[0], host
    return host, host


def same_origin(request: Request) -> bool:
    """CSRF: Origin-Host muss zum Host der Anfrage passen. Schema darf durch Reverse-Proxy abweichen."""
    origin = request.headers.get("origin")
    if not origin:
        return True
    origin_host = (urlparse(origin).netloc or "").strip()
    if not origin_host:
        return False
    origin_name, origin_full = _host_key(origin_host)
    candidates: list[str] = []
    for raw in (
        request.headers.get("x-forwarded-host"),
        request.headers.get("host"),
        urlparse(str(request.base_url)).netloc,
    ):
        if not raw:
            continue
        host = raw.split(",")[0].strip()
        if host:
            candidates.append(host)
    names = set()
    fulls = set()
    for item in candidates:
        name, full = _host_key(item)
        names.add(name)
        fulls.add(full)
    return origin_full in fulls or origin_name in names
