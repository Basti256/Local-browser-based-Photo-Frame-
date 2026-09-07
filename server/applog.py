"""Anwendungslog: 72 Stunden, ohne Geheimnisse."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.paths import DATA_DIR, ensure_data_dir

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
KEEP = timedelta(hours=72)
_lock = threading.Lock()
_writes = 0


def log_path() -> Path:
    ensure_data_dir()
    return DATA_DIR / "app.log"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_level(value: str | None) -> int:
    return LEVELS.get(str(value or "INFO").upper(), 20)


def current_level_name() -> str:
    try:
        from server.runtime import load_runtime
        raw = str(load_runtime().get("log_level") or "INFO").upper()
    except Exception:
        raw = "INFO"
    return raw if raw in LEVELS else "INFO"


def _threshold() -> int:
    return _parse_level(current_level_name())


def _parse_ts(line: str) -> datetime | None:
    part = (line or "").split(" ", 1)[0].strip()
    if not part:
        return None
    try:
        return datetime.fromisoformat(part.replace("Z", "+00:00"))
    except ValueError:
        return None


def _prune_unlocked(path: Path) -> None:
    if not path.is_file():
        return
    cutoff = _now() - KEEP
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    kept: list[str] = []
    for line in text.splitlines():
        ts = _parse_ts(line)
        if ts is None or ts >= cutoff:
            kept.append(line)
    body = "\n".join(kept)
    if kept:
        body += "\n"
    try:
        path.write_text(body, encoding="utf-8")
    except OSError:
        pass


def log(level: str, message: str) -> None:
    level = str(level or "INFO").upper()
    if level not in LEVELS:
        level = "INFO"
    if LEVELS[level] < _threshold():
        return
    msg = " ".join(str(message or "").split())
    if not msg:
        return
    line = f"{_now().isoformat(timespec='seconds')} {level} {msg}\n"
    ensure_data_dir()
    global _writes
    path = log_path()
    with _lock:
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
            _writes += 1
            if _writes % 80 == 1:
                _prune_unlocked(path)
        except OSError:
            pass


def log_request(method: str, path: str, status: int) -> None:
    p = (path or "").split("?", 1)[0]
    if p.startswith("/static/") or p.startswith("/.well-known/"):
        return
    name = p.rsplit("/", 1)[-1]
    if "/media/" in p and name.lower().endswith(".txt") and status in (204, 404):
        return
    level = "DEBUG"
    if status >= 500:
        level = "ERROR"
    elif status >= 400:
        level = "WARNING"
    elif p.startswith("/api/login") or p.startswith("/api/admin/unlock") or p.startswith("/api/setup/init"):
        level = "INFO"
    log(level, f"{method} {p} {status}")


def read_log() -> str:
    ensure_data_dir()
    path = log_path()
    with _lock:
        _prune_unlocked(path)
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


def clear_log() -> None:
    ensure_data_dir()
    path = log_path()
    with _lock:
        try:
            path.write_text("", encoding="utf-8")
        except OSError:
            pass
    log("INFO", "Protokoll geleert")
