"""Admin-PIN je Projekt. Hash, versiegelte Anzeige, Session-Cookie, Wartezeit."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from server.auth import _secret, same_origin

COOKIE_NAME = "pf_admin"
COOKIE_MAX_AGE = 60 * 60 * 12
SESSION_SALT = "photo-frame-admin-pin"
PIN_MIN_LEN = 4
PIN_MAX_LEN = 10
GENERATED_PIN_LEN = 4
WAIT_CAP_SEC = 3600

_hasher = PasswordHasher()


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret(), salt=SESSION_SALT)


def generate_random_pin() -> str:
    return f"{secrets.randbelow(10 ** GENERATED_PIN_LEN):0{GENERATED_PIN_LEN}d}"


def _seal_pin(pin: str) -> str:
    nonce = secrets.token_bytes(16)
    stream = hmac.new(_secret().encode(), nonce + b"pf-pin-display", hashlib.sha256).digest()
    raw = pin.encode("utf-8")
    if len(raw) > len(stream):
        raise ValueError("PIN zu lang für die Anzeigeversiegelung.")
    ct = bytes(a ^ b for a, b in zip(raw, stream))
    return base64.urlsafe_b64encode(nonce + bytes([len(raw)]) + ct).decode("ascii")


def _unseal_pin(blob: str) -> str | None:
    try:
        data = base64.urlsafe_b64decode((blob or "").encode("ascii"))
        nonce, length, ct = data[:16], data[16], data[17:]
        stream = hmac.new(_secret().encode(), nonce + b"pf-pin-display", hashlib.sha256).digest()
        raw = bytes(a ^ b for a, b in zip(ct[:length], stream[:length]))
        pin = raw.decode("utf-8")
    except Exception:
        return None
    if not pin.isdigit() or not (PIN_MIN_LEN <= len(pin) <= PIN_MAX_LEN):
        return None
    return pin


def validate_pin(pin: str) -> str:
    pin = (pin or "").strip()
    if not pin.isdigit() or not (PIN_MIN_LEN <= len(pin) <= PIN_MAX_LEN):
        raise HTTPException(
            status_code=400,
            detail=f"PIN: {PIN_MIN_LEN} bis {PIN_MAX_LEN} Ziffern.",
        )
    return pin


def load_access(paths) -> dict[str, Any]:
    if not paths.access_file.is_file():
        return {"pin_hash": "", "fail_count": 0, "lock_until": 0.0, "pin_sealed": ""}
    with paths.access_file.open(encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("pin_hash", "")
    data.setdefault("fail_count", 0)
    data.setdefault("lock_until", 0.0)
    data.setdefault("pin_sealed", "")
    return data


def save_access(paths, data: dict[str, Any]) -> None:
    paths.ensure()
    payload = {
        "pin_hash": data.get("pin_hash") or "",
        "fail_count": int(data.get("fail_count") or 0),
        "lock_until": float(data.get("lock_until") or 0),
        "pin_sealed": data.get("pin_sealed") or "",
    }
    with paths.access_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    try:
        paths.access_file.chmod(0o600)
    except OSError:
        pass


def has_pin(paths) -> bool:
    return bool(load_access(paths).get("pin_hash"))


def set_pin(paths, pin: str) -> None:
    pin = validate_pin(pin)
    data = load_access(paths)
    data["pin_hash"] = _hasher.hash(pin)
    data["pin_sealed"] = _seal_pin(pin)
    data["fail_count"] = 0
    data["lock_until"] = 0.0
    save_access(paths, data)


def display_pin(paths) -> str:
    data = load_access(paths)
    return _unseal_pin(data.get("pin_sealed") or "") or ""


def ensure_project_pin(paths) -> str:
    shown = display_pin(paths)
    if shown:
        return shown
    if has_pin(paths):
        return ""
    pin = generate_random_pin()
    set_pin(paths, pin)
    return pin


def wait_seconds_remaining(paths) -> float:
    data = load_access(paths)
    remaining = float(data.get("lock_until") or 0) - time.time()
    return max(0.0, remaining)


def _wait_for_fail_count(fail_count: int) -> float:
    if fail_count < 1:
        return 0.0
    return min(WAIT_CAP_SEC, float(2 ** fail_count))


def try_pin(paths, pin: str) -> None:
    data = load_access(paths)
    if not data.get("pin_hash"):
        raise HTTPException(status_code=409, detail="Kein PIN gesetzt. In der Einrichtung festlegen.")
    remaining = wait_seconds_remaining(paths)
    if remaining > 0:
        from server.applog import log
        log("WARNING", f"PIN-Anmeldung gesperrt ({paths.name})")
        raise HTTPException(
            status_code=429,
            detail={"message": "Warten vor dem nächsten Versuch.", "wait_seconds": round(remaining, 1)},
        )
    pin = (pin or "").strip()
    try:
        ok = _hasher.verify(data["pin_hash"], pin)
    except (VerifyMismatchError, InvalidHash):
        ok = False
    if not ok:
        fail_count = int(data.get("fail_count") or 0) + 1
        wait = _wait_for_fail_count(fail_count)
        data["fail_count"] = fail_count
        data["lock_until"] = time.time() + wait
        save_access(paths, data)
        from server.applog import log
        log("WARNING", f"PIN falsch ({paths.name})")
        raise HTTPException(
            status_code=401,
            detail={"message": "PIN falsch.", "wait_seconds": wait, "fail_count": fail_count},
        )
    data["fail_count"] = 0
    data["lock_until"] = 0.0
    save_access(paths, data)
    from server.applog import log
    log("INFO", f"PIN-Anmeldung erfolgreich ({paths.name})")


def set_admin_session(response: Response, project: str, request: Request) -> None:
    token = _serializer().dumps({"p": project})
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "") == "https"
    from server.routing import with_prefix
    cookie_path = with_prefix("/") or "/"
    if cookie_path != "/":
        cookie_path = cookie_path.rstrip("/") or "/"
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path=cookie_path,
    )


def clear_admin_session(response: Response) -> None:
    from server.routing import with_prefix
    cookie_path = with_prefix("/") or "/"
    if cookie_path != "/":
        cookie_path = cookie_path.rstrip("/") or "/"
    response.delete_cookie(COOKIE_NAME, path=cookie_path)
    if cookie_path != "/":
        response.delete_cookie(COOKIE_NAME, path="/")


def admin_project(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("p")


def require_pin_session(request: Request, project: str) -> None:
    if request.method not in ("GET", "HEAD", "OPTIONS") and not same_origin(request):
        raise HTTPException(status_code=403, detail="Ungültige Herkunft.")
    if admin_project(request) != project:
        raise HTTPException(status_code=401, detail="PIN-Anmeldung erforderlich.")
