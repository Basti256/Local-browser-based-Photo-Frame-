"""Anmelde-Sperren für Setup-Login und Erstkonfiguration. Keine Geheimnisse."""
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import HTTPException

from server.paths import DATA_DIR, ensure_data_dir

WAIT_CAP_SEC = 3600
KEYS = ("setup", "init")


def _lock_file():
    return DATA_DIR / "login_lock.json"


def _wait_for_fail_count(fail_count: int) -> float:
    if fail_count < 1:
        return 0.0
    return min(WAIT_CAP_SEC, float(2 ** fail_count))


def _load() -> dict[str, Any]:
    ensure_data_dir()
    path = _lock_file()
    if not path.is_file():
        return {k: {"fail_count": 0, "lock_until": 0.0} for k in KEYS}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    out = {}
    for key in KEYS:
        row = data.get(key) if isinstance(data.get(key), dict) else {}
        out[key] = {
            "fail_count": int(row.get("fail_count") or 0),
            "lock_until": float(row.get("lock_until") or 0),
        }
    return out


def _save(data: dict[str, Any]) -> None:
    ensure_data_dir()
    payload = {}
    for key in KEYS:
        row = data.get(key) or {}
        payload[key] = {
            "fail_count": int(row.get("fail_count") or 0),
            "lock_until": float(row.get("lock_until") or 0),
        }
    path = _lock_file()
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def wait_seconds(key: str) -> float:
    row = _load().get(key) or {}
    remaining = float(row.get("lock_until") or 0) - time.time()
    return max(0.0, remaining)


def status(key: str, path: str) -> dict[str, Any]:
    wait = round(wait_seconds(key), 1)
    return {
        "key": key,
        "path": path,
        "locked": wait > 0,
        "wait_seconds": wait,
    }


def refuse_if_locked(key: str, path: str) -> None:
    wait = wait_seconds(key)
    if wait <= 0:
        return
    raise HTTPException(
        status_code=429,
        detail={
            "message": f"Anmeldung unter {path} gesperrt.",
            "wait_seconds": round(wait, 1),
            "path": path,
        },
    )


def record_failure(key: str) -> float:
    data = _load()
    row = data.setdefault(key, {"fail_count": 0, "lock_until": 0.0})
    fail_count = int(row.get("fail_count") or 0) + 1
    wait = _wait_for_fail_count(fail_count)
    row["fail_count"] = fail_count
    row["lock_until"] = time.time() + wait
    data[key] = row
    _save(data)
    return wait


def clear_failures(key: str) -> None:
    data = _load()
    data[key] = {"fail_count": 0, "lock_until": 0.0}
    _save(data)
