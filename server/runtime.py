"""Serverweite Runtime: Port, Bind, aktives Projekt. Keine Zugangsdaten."""
import json
from typing import Any

from server.paths import RUNTIME_FILE, ensure_data_dir


def _clean_running(names: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(names, list):
        return out
    for raw in names:
        name = str(raw or "").strip()
        if name and name not in out:
            out.append(name)
    return out

DEFAULT_RUNTIME = {
    "port": 8000,
    "bind_host": "0.0.0.0",
    "active_project": "",
    "running_projects": [],
    "public_host": "",
    "public_https": False,
    "log_level": "INFO",
}


def parse_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise ValueError("Port muss eine Zahl sein.") from None
    if port < 1 or port > 65535:
        raise ValueError("Port: 1 bis 65535.")
    return port


def load_runtime() -> dict[str, Any]:
    ensure_data_dir()
    if not RUNTIME_FILE.is_file():
        save_runtime(DEFAULT_RUNTIME.copy())
        return DEFAULT_RUNTIME.copy()
    with RUNTIME_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    changed = False
    if "running_projects" not in data:
        data["running_projects"] = [str(data.get("active_project") or "")] if data.get("active_project") else []
        data["running_projects"] = [n for n in data["running_projects"] if n]
        changed = True
    for key, value in DEFAULT_RUNTIME.items():
        if key not in data:
            data[key] = value
            changed = True
    if data.get("bind_host") not in ("0.0.0.0", "127.0.0.1"):
        data["bind_host"] = "0.0.0.0"
        changed = True
    try:
        data["port"] = parse_port(data.get("port", 8000))
    except ValueError:
        data["port"] = 8000
        changed = True
    data["active_project"] = str(data.get("active_project") or "")
    data["running_projects"] = _clean_running(data.get("running_projects"))
    data["public_host"] = str(data.get("public_host") or "").strip()
    data["public_https"] = bool(data.get("public_https"))
    level = str(data.get("log_level") or "INFO").upper()
    if level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        level = "INFO"
        changed = True
    data["log_level"] = level
    if changed:
        save_runtime(data)
    return {
        "port": data["port"],
        "bind_host": data["bind_host"],
        "active_project": data["active_project"],
        "running_projects": list(data["running_projects"]),
        "public_host": data["public_host"],
        "public_https": data["public_https"],
        "log_level": data["log_level"],
    }


def save_runtime(data: dict[str, Any]) -> None:
    ensure_data_dir()
    try:
        port = parse_port(data.get("port") or 8000)
    except ValueError:
        port = 8000
    payload = {
        "port": port,
        "bind_host": data.get("bind_host") or "0.0.0.0",
        "active_project": str(data.get("active_project") or ""),
        "running_projects": _clean_running(data.get("running_projects")),
        "public_host": str(data.get("public_host") or "").strip(),
        "public_https": bool(data.get("public_https")),
        "log_level": str(data.get("log_level") or "INFO").upper(),
    }
    if payload["bind_host"] not in ("0.0.0.0", "127.0.0.1"):
        payload["bind_host"] = "0.0.0.0"
    if payload["log_level"] not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        payload["log_level"] = "INFO"
    with RUNTIME_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def update_runtime(**kwargs: Any) -> dict[str, Any]:
    data = load_runtime()
    data.update(kwargs)
    save_runtime(data)
    return load_runtime()
