"""Projektordner, Config und sichere Dateinamen."""
from __future__ import annotations

import json
import re
import socket
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from server.context import get_current_project
from server.defaults import DEFAULT_CONFIG, STORAGE_MODES, migrate_config
from server.paths import PROJECTS_DIR
from server.restart import listen_port
from server.runtime import load_runtime, parse_port, update_runtime

SETUP_OWNED_KEYS = frozenset({
    "network_mode", "public_host", "public_https", "public_base_url",
    "storage_mode", "storage_path", "port",
})

PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
VIDEO_EXT = {".mp4", ".mov", ".webm"}
DISPLAY_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DISPLAY_VIDEO_EXT = {".mp4", ".mov", ".webm"}


class ProjectPaths:
    def __init__(self, name: str):
        self.name = name
        self.root = PROJECTS_DIR / name
        self.config_file = self.root / "config.json"
        self.header = self.root / "header"
        self.background = self.root / "background"
        self.derived = self.root / "derived"
        self.access_file = self.root / "access.json"

    def _storage_config(self) -> dict[str, Any]:
        if not self.config_file.is_file():
            return {}
        try:
            with self.config_file.open(encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @property
    def media(self) -> Path:
        cfg = self._storage_config()
        if (cfg.get("storage_mode") or "project") == "folder":
            raw = str(cfg.get("storage_path") or "").strip()
            if raw:
                return Path(raw)
        return self.root / "media"

    def ensure(self) -> None:
        for folder in (self.root, self.header, self.background, self.derived):
            folder.mkdir(parents=True, exist_ok=True)
        try:
            self.media.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


def validate_project_name(name: str) -> str:
    name = (name or "").strip()
    if not PROJECT_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Projektname: Buchstaben, Zahlen, Punkt, Unterstrich, Bindestrich. Max. 63 Zeichen.",
        )
    return name


def list_projects() -> list[str]:
    if not PROJECTS_DIR.is_dir():
        return []
    names = []
    for child in sorted(PROJECTS_DIR.iterdir()):
        if child.is_dir() and (child / "config.json").is_file():
            names.append(child.name)
    return names


def create_project(name: str) -> ProjectPaths:
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if paths.config_file.exists():
        raise HTTPException(status_code=409, detail="Projekt existiert bereits.")
    paths.ensure()
    config = DEFAULT_CONFIG.copy()
    config["port"] = allocate_project_port()
    save_project_config(paths, config)
    from server.pin import ensure_project_pin
    ensure_project_pin(paths)
    return paths


def apply_imported_config(paths: ProjectPaths, incoming: dict[str, Any]) -> dict[str, Any]:
    cfg = load_project_config(paths)
    if not isinstance(incoming, dict):
        raise HTTPException(status_code=400, detail="Keine gültige Config.")
    for key, default in DEFAULT_CONFIG.items():
        if key not in incoming or key in SETUP_OWNED_KEYS:
            continue
        value = incoming[key]
        if isinstance(default, bool):
            cfg[key] = bool(value)
        elif isinstance(default, int) and not isinstance(default, bool):
            try:
                cfg[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif isinstance(default, float):
            try:
                cfg[key] = float(value)
            except (TypeError, ValueError):
                continue
        elif isinstance(default, str):
            cfg[key] = "" if value is None else str(value)
        else:
            cfg[key] = value
    cfg, _ = migrate_config(cfg)
    save_project_config(paths, cfg)
    return cfg


def write_imported_asset(paths: ProjectPaths, folder: str, filename: str, data: bytes) -> None:
    if folder not in ("background", "header"):
        return
    if Path(filename).suffix.lower() not in IMAGE_EXT:
        return
    dest_dir = paths.background if folder == "background" else paths.header
    dest = safe_join(dest_dir, filename)
    if dest is None:
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)



def project_listen_port(paths: ProjectPaths | None = None, config: dict[str, Any] | None = None) -> int:
    if config is None:
        config = load_project_config(paths) if paths else {}
    try:
        return parse_port(config.get("port", 8000))
    except ValueError:
        return 8000


def used_project_ports(exclude: str | None = None) -> set[int]:
    used = {listen_port()}
    for name in list_projects():
        if exclude and name == exclude:
            continue
        used.add(project_listen_port(ProjectPaths(name)))
    return used


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def allocate_project_port() -> int:
    used = used_project_ports()
    port = 8000
    while port in used or port_in_use(port):
        port += 1
        if port > 65535:
            raise HTTPException(status_code=500, detail="Kein freier Projekt-Port.")
    return port


def apply_listen_port(paths: ProjectPaths, port: int) -> dict[str, Any]:
    try:
        port = parse_port(port)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if port == listen_port():
        raise HTTPException(status_code=400, detail="Port ist der Einrichtungs-Port.")
    if port in used_project_ports(exclude=paths.name):
        raise HTTPException(status_code=409, detail="Port ist einem anderen Projekt zugeordnet.")
    cfg = load_project_config(paths)
    cfg["port"] = port
    save_project_config(paths, cfg)
    return cfg


def get_paths(name: str | None = None) -> ProjectPaths | None:
    if name is None:
        name = get_current_project() or ""
    if not name:
        return None
    paths = ProjectPaths(name)
    if not paths.root.is_dir():
        return None
    paths.ensure()
    return paths


def require_paths() -> ProjectPaths:
    paths = get_paths()
    if paths is None:
        raise HTTPException(status_code=409, detail="Kein laufendes Projekt.")
    return paths


def set_active_project(name: str) -> None:
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    paths.ensure()
    update_runtime(active_project=name)


def clear_active_project(name: str | None = None) -> None:
    rt = load_runtime()
    if name is None or rt.get("active_project") == name:
        update_runtime(active_project="")


def load_project_config(paths: ProjectPaths | None = None) -> dict[str, Any]:
    if paths is None:
        paths = get_paths()
    if paths is None:
        return DEFAULT_CONFIG.copy()
    paths.ensure()
    if not paths.config_file.is_file():
        config = DEFAULT_CONFIG.copy()
        save_project_config(paths, config)
        return config
    with paths.config_file.open(encoding="utf-8") as f:
        config = json.load(f)
    config, changed = migrate_config(config)
    if changed:
        save_project_config(paths, config)
    return config


def save_project_config(paths: ProjectPaths, config: dict[str, Any]) -> None:
    paths.ensure()
    with paths.config_file.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
        f.write("\n")


def apply_storage(paths: ProjectPaths, mode: str, storage_path: str) -> dict[str, Any]:
    mode = (mode or "project").strip()
    if mode not in STORAGE_MODES:
        raise HTTPException(status_code=400, detail="Speicher: project oder folder.")
    cfg = load_project_config(paths)
    cfg["storage_mode"] = mode
    raw = (storage_path or "").strip().strip('"')
    if mode == "folder":
        if not raw:
            raise HTTPException(status_code=400, detail="Ordnerpfad angeben (lokal, UNC oder Mount).")
        target = Path(raw)
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise HTTPException(status_code=400, detail="Ordner nicht nutzbar.") from e
        if not target.is_dir():
            raise HTTPException(status_code=400, detail="Pfad ist kein Ordner.")
        cfg["storage_path"] = str(target)
    else:
        cfg["storage_path"] = ""
    save_project_config(paths, cfg)
    paths.ensure()
    return cfg


def merge_project_config(incoming: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    paths = require_paths()
    current = load_project_config(paths)
    old_view = current.get("wall_view_mode")
    merged = current.copy()
    for key, default in DEFAULT_CONFIG.items():
        if key not in incoming or key in SETUP_OWNED_KEYS:
            continue
        value = incoming[key]
        if isinstance(default, bool):
            merged[key] = bool(value)
        elif isinstance(default, int) and not isinstance(default, bool):
            try:
                merged[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif isinstance(default, float):
            try:
                merged[key] = float(value)
            except (TypeError, ValueError):
                continue
        elif isinstance(default, str):
            merged[key] = "" if value is None else str(value)
        else:
            merged[key] = value
    view_changed = old_view != merged.get("wall_view_mode")
    save_project_config(paths, merged)
    return merged, view_changed


def safe_join(folder: Path, filename: str) -> Path | None:
    if not filename or filename != Path(filename).name:
        return None
    if filename in (".", ".."):
        return None
    path = (folder / filename).resolve()
    try:
        path.relative_to(folder.resolve())
    except ValueError:
        return None
    return path
