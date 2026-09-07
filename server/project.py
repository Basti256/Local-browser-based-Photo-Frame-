"""Projektordner, Config und sichere Dateinamen."""
from __future__ import annotations

import json
import re
import socket
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from server.context import get_current_project
from server.defaults import DEFAULT_CONFIG, migrate_config
from server.paths import PROJECTS_DIR
from server.runtime import load_runtime, update_runtime
from server.slugs import is_reserved_segment

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
        from server.runtime import load_runtime
        root = str(load_runtime().get("media_root") or "").strip()
        if root:
            return Path(root) / self.name
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
    if is_reserved_segment(name):
        raise HTTPException(
            status_code=400,
            detail="Dieser Name ist für Systempfade reserviert.",
        )
    return name


def find_project_by_slug(segment: str) -> str | None:
    segment = (segment or "").strip()
    if not segment or is_reserved_segment(segment):
        return None
    names = list_projects()
    for name in names:
        if name == segment:
            return name
    lowered = segment.lower()
    hits = [name for name in names if name.lower() == lowered]
    if len(hits) == 1:
        return hits[0]
    return None


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



def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def get_paths(name: str | None = None) -> ProjectPaths | None:
    if name is None:
        name = get_current_project() or ""
    if not name:
        return None
    paths = ProjectPaths(name)
    if not paths.root.is_dir():
        return None
    from server.context import get_url_prefix
    from server.project_runner import runner
    if get_url_prefix() and not runner.is_running(name):
        return None
    paths.ensure()
    return paths


def require_paths() -> ProjectPaths:
    paths = get_paths()
    if paths is None:
        raise HTTPException(status_code=409, detail="Kein laufendes Projekt.")
    from server.context import get_url_prefix
    from server.project_runner import runner
    if get_url_prefix() and not runner.is_running(paths.name):
        raise HTTPException(status_code=409, detail="Projekt ist gestoppt.")
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


def apply_media_root(raw: str) -> str:
    root = (raw or "").strip().strip('"')
    if not root:
        update_runtime(media_root="")
        return ""
    target = Path(root)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail="Medienordner nicht nutzbar.") from e
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Pfad ist kein Ordner.")
    update_runtime(media_root=str(target))
    for name in list_projects():
        ProjectPaths(name).ensure()
    return str(target)


def delete_project(name: str) -> None:
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    media = paths.media
    project_media = (paths.root / "media").resolve()
    try:
        import shutil
        shutil.rmtree(paths.root)
    except OSError as e:
        raise HTTPException(status_code=500, detail="Projektordner konnte nicht gelöscht werden.") from e
    try:
        extra = media.resolve()
    except OSError:
        return
    if extra == project_media or not extra.exists():
        return
    root = str(load_runtime().get("media_root") or "").strip()
    if not root:
        return
    try:
        expected = (Path(root) / name).resolve()
    except OSError:
        return
    if extra == expected:
        try:
            import shutil
            shutil.rmtree(extra)
        except OSError:
            pass


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
