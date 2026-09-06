"""Neustart nach Änderung des Listen-Ports."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

from fastapi import Request

from server.firewall import close_firewall_port
from server.paths import BASE_DIR

WAIT_SECONDS = 10
_RESTART_DELAY_SEC = 1.2

_listen_host = "0.0.0.0"
_listen_port = 8000
_cli_host: str | None = None


def set_listen(host: str, port: int, cli_host: str | None = None) -> None:
    global _listen_host, _listen_port, _cli_host
    _listen_host = host
    _listen_port = int(port)
    _cli_host = cli_host


def listen_port() -> int:
    return _listen_port


def listen_host() -> str:
    return _listen_host


def under_systemd() -> bool:
    return bool(os.environ.get("INVOCATION_ID"))


def skip_restart() -> bool:
    return os.environ.get("PHOTO_FRAME_SKIP_RESTART") == "1"


def clear_skip_restart() -> None:
    """Beim echten Serverstart niemals den Neustart unterdrücken."""
    if os.environ.pop("PHOTO_FRAME_SKIP_RESTART", None):
        print("[Restart] PHOTO_FRAME_SKIP_RESTART ignoriert (Serverstart).")


def setup_url_for_port(request: Request, port: int) -> str:
    hostname = request.url.hostname or "127.0.0.1"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    scheme = request.url.scheme or "http"
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{hostname}/setup"
    return f"{scheme}://{hostname}:{port}/setup"


def restart_fields(request: Request, new_port: int, changed: bool) -> dict:
    if not changed:
        return {"restart": False, "setup_url": None, "wait_seconds": WAIT_SECONDS}
    return {
        "restart": True,
        "setup_url": setup_url_for_port(request, new_port),
        "wait_seconds": WAIT_SECONDS,
    }


def schedule_restart() -> None:
    if skip_restart():
        print("[Restart] Übersprungen (PHOTO_FRAME_SKIP_RESTART).")
        return
    threading.Thread(target=_restart_worker, daemon=True, name="pf-restart").start()


def _spawn_replacement(cmd: list[str]) -> None:
    kwargs: dict = {
        "cwd": str(BASE_DIR),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform != "win32":
        kwargs["close_fds"] = True
        kwargs["start_new_session"] = True
        subprocess.Popen(cmd, **kwargs)
        return
    kwargs["close_fds"] = False
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    create_breakaway = 0x01000000
    flag_sets = (
        subprocess.CREATE_NEW_PROCESS_GROUP | create_breakaway | create_no_window,
        subprocess.CREATE_NEW_PROCESS_GROUP | create_no_window,
        subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    last_error: Exception | None = None
    for flags in flag_sets:
        try:
            subprocess.Popen(cmd, creationflags=flags, **kwargs)
            return
        except OSError as e:
            last_error = e
    if last_error:
        raise last_error


def _restart_worker() -> None:
    old_port = _listen_port
    time.sleep(_RESTART_DELAY_SEC)
    try:
        close_firewall_port(old_port)
    except Exception:
        pass
    if under_systemd():
        print("[Restart] Beende Prozess, systemd startet neu.")
        os._exit(0)
    cmd = [sys.executable, "-m", "server"]
    if _cli_host:
        cmd.extend(["--host", _cli_host])
    print("[Restart] Starte Prozess neu:", " ".join(cmd))
    try:
        _spawn_replacement(cmd)
    except Exception as e:
        print("[Restart] Neustart fehlgeschlagen:", e)
        return
    os._exit(0)
