"""Live-Update: Stand von origin/main prüfen und per fast-forward einspielen."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from typing import Any

from fastapi import HTTPException

from server.paths import BASE_DIR
from server.version import __version__

REMOTE = "origin"
BRANCH = "main"
_lock = threading.Lock()


def _clean(text: str) -> str:
    text = " ".join(str(text or "").split())
    return re.sub(r"https?://[^/\s]*:[^@/\s]+@", "https://", text)


def parse_version(text: str) -> str:
    for line in (text or "").splitlines():
        if "__version__" in line and "=" in line:
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    kwargs: dict[str, Any] = {
        "cwd": str(BASE_DIR),
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(["git", *args], **kwargs)


def _git_out(*args: str, timeout: int = 60, fail: str = "Git-Befehl fehlgeschlagen.") -> str:
    try:
        proc = _git(*args, timeout=timeout)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail="Git ist nicht installiert.") from e
    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail=fail + " Zeitüberschreitung.") from e
    if proc.returncode != 0:
        err = _clean(proc.stderr or proc.stdout or fail)
        raise HTTPException(status_code=409, detail=err or fail)
    return (proc.stdout or "").strip()


def _ensure_repo() -> None:
    try:
        proc = _git("rev-parse", "--is-inside-work-tree", timeout=10)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail="Git ist nicht installiert.") from e
    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail="Git antwortet nicht.") from e
    if proc.returncode != 0 or (proc.stdout or "").strip() != "true":
        raise HTTPException(status_code=409, detail="Kein Git-Arbeitsverzeichnis.")


def _short(rev: str) -> str:
    rev = (rev or "").strip()
    return rev[:7] if rev else ""


def _object_exists(rev: str) -> bool:
    if not rev:
        return False
    try:
        proc = _git("cat-file", "-e", rev + "^{commit}", timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _is_ancestor(maybe_ancestor: str, rev: str) -> bool:
    try:
        proc = _git("merge-base", "--is-ancestor", maybe_ancestor, rev, timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _remote_version(rev: str) -> str:
    if not rev:
        return ""
    try:
        proc = _git("show", f"{rev}:server/version.py", timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return parse_version(proc.stdout or "")


def _tracked_dirty() -> bool:
    try:
        proc = _git("status", "--porcelain", "--untracked-files=no", timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    if proc.returncode != 0:
        return True
    return bool((proc.stdout or "").strip())


def _remote_head() -> str:
    _git_out("fetch", REMOTE, timeout=90, fail="Remote-Stand nicht lesbar.")
    try:
        return _git_out(
            "rev-parse",
            f"{REMOTE}/{BRANCH}",
            timeout=10,
            fail="Remote-Stand von main nicht gefunden.",
        )
    except HTTPException:
        return _git_out("rev-parse", "FETCH_HEAD", timeout=10, fail="Remote-Stand von main nicht gefunden.")


def check_update() -> dict[str, Any]:
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ein Update läuft bereits.")
    try:
        _ensure_repo()
        local = _git_out("rev-parse", "HEAD", timeout=10, fail="Lokaler Stand nicht lesbar.")
        remote = _remote_head()
        current = local == remote
        available = False
        blocked = False
        if current:
            message = "Kein Update. Dieser Stand ist origin/main."
        elif _object_exists(remote) and _is_ancestor(remote, local):
            blocked = True
            message = "Lokale Commits liegen vor origin/main. Fast-forward ist nicht möglich."
        elif (not _object_exists(remote)) or _is_ancestor(local, remote):
            available = True
            message = "Update verfügbar auf origin/main."
        else:
            blocked = True
            message = "Lokaler Stand und origin/main sind auseinandergelaufen. Fast-forward ist nicht möglich."
        remote_ver = _remote_version(remote) if _object_exists(remote) else ""
        return {
            "ok": True,
            "current": current,
            "available": available,
            "blocked": blocked,
            "current_version": __version__,
            "remote_version": remote_ver,
            "current_rev": _short(local),
            "remote_rev": _short(remote),
            "message": message,
        }
    finally:
        _lock.release()


def _pip_cmd() -> list[str]:
    if sys.platform == "win32":
        pip = BASE_DIR / "venv" / "Scripts" / "pip.exe"
    else:
        pip = BASE_DIR / "venv" / "bin" / "pip"
        if not pip.is_file():
            pip = BASE_DIR / "venv" / "bin" / "pip3"
    if not pip.is_file():
        raise HTTPException(status_code=409, detail="venv nicht gefunden.")
    return [str(pip), "install", "-r", str(BASE_DIR / "requirements.txt")]


def apply_update() -> dict[str, Any]:
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ein Update läuft bereits.")
    try:
        _ensure_repo()
        if _tracked_dirty():
            raise HTTPException(
                status_code=409,
                detail="Lokale Änderungen an versionierten Dateien. Zuerst zurücksetzen oder auf einem Entwicklungsrechner arbeiten.",
            )
        before = _git_out("rev-parse", "HEAD", timeout=10, fail="Lokaler Stand nicht lesbar.")
        _git_out("fetch", REMOTE, BRANCH, timeout=90, fail="git fetch fehlgeschlagen.")
        branch = _git_out("rev-parse", "--abbrev-ref", "HEAD", timeout=10, fail="Branch nicht lesbar.")
        if branch != BRANCH:
            _git_out("checkout", BRANCH, timeout=20, fail="Wechsel auf main fehlgeschlagen.")
        _git_out("pull", "--ff-only", REMOTE, BRANCH, timeout=90, fail="git pull fehlgeschlagen.")
        after = _git_out("rev-parse", "HEAD", timeout=10, fail="Lokaler Stand nicht lesbar.")
        changed = before != after
        pip = _pip_cmd()
        try:
            kwargs: dict[str, Any] = {
                "cwd": str(BASE_DIR),
                "capture_output": True,
                "text": True,
                "timeout": 180,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.run(pip, **kwargs)
        except FileNotFoundError as e:
            raise HTTPException(status_code=409, detail="venv nicht gefunden.") from e
        except subprocess.TimeoutExpired as e:
            raise HTTPException(status_code=504, detail="pip install Zeitüberschreitung.") from e
        if proc.returncode != 0:
            err = _clean(proc.stderr or proc.stdout or "pip install fehlgeschlagen.")
            raise HTTPException(status_code=409, detail=err)
        new_ver = __version__
        shown = _git_out("show", "HEAD:server/version.py", timeout=10, fail="Version nicht lesbar.")
        parsed = parse_version(shown)
        if parsed:
            new_ver = parsed
        if not changed:
            return {
                "ok": True,
                "changed": False,
                "restart": False,
                "current_version": __version__,
                "new_version": new_ver,
                "current_rev": _short(after),
                "message": "Kein Update. Dieser Stand ist origin/main.",
            }
        return {
            "ok": True,
            "changed": True,
            "restart": True,
            "current_version": __version__,
            "new_version": new_ver,
            "current_rev": _short(after),
            "message": "Update eingespielt. Der Server startet neu.",
        }
    finally:
        _lock.release()
