"""Serverweite Config-Vorlagen und Standardhintergründe unter data/."""
from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from server.defaults import apply_incoming_values
from server.paths import DATA_DIR
from server.project import (
    IMAGE_EXT,
    SETUP_OWNED_KEYS,
    apply_imported_config,
    safe_join,
    write_imported_asset,
)

SHARED_PREFIX = "shared:"
BG_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
NAME_MAX = 80
DESC_MAX = 500
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


def templates_dir() -> Path:
    return DATA_DIR / "templates"


def shared_bg_dir() -> Path:
    return DATA_DIR / "shared_backgrounds"


def ensure_catalog_dirs() -> None:
    templates_dir().mkdir(parents=True, exist_ok=True)
    shared_bg_dir().mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_text(value: str, max_len: int, *, required: bool) -> str:
    text = " ".join(str(value or "").replace("\x00", "").split())
    if required and not text:
        raise HTTPException(status_code=400, detail="Name fehlt.")
    if len(text) > max_len:
        raise HTTPException(status_code=400, detail=f"Text zu lang (max. {max_len} Zeichen).")
    return text


WALL_KEYS = frozenset({
    "wall_view_mode",
    "wall_display_rotation",
    "grid_columns",
    "grid_animation_duration",
    "grid_show_frames",
    "grid_spacing_rows",
    "grid_spacing_columns",
    "frame_padding_top",
    "frame_padding_side",
    "frame_padding_bottom",
    "image_spawn_interval",
    "spawn_mode",
    "spawn_lane_count",
    "spawn_lane_order",
    "spawn_burst_period",
    "max_images_on_screen",
    "image_min_size",
    "image_max_size",
    "max_videos_on_screen",
    "video_playback_mode",
    "video_spawn_interval",
    "video_min_size",
    "video_max_size",
    "image_rotation_strength",
    "image_drift_strength",
    "image_rotation_direction_mode",
    "image_flight_path_mode",
    "image_animation_duration",
    "image_speed_variation_enabled",
    "image_speed_variation_strength",
    "image_highlight_new",
    "image_highlight_duration",
    "image_highlight_color",
    "image_max_simultaneous_highlights",
    "video_rotation_strength",
    "video_drift_strength",
    "video_rotation_direction_mode",
    "video_flight_path_mode",
    "video_animation_duration",
    "video_speed_variation_enabled",
    "video_speed_variation_strength",
    "video_highlight_new",
    "video_highlight_duration",
    "video_highlight_color",
    "video_max_simultaneous_highlights",
    "center_highlight_enabled",
    "center_highlight_duration",
    "center_highlight_mode",
    "center_highlight_entry_speed",
    "center_highlight_exit_speed",
    "center_highlight_screen_percent",
    "center_highlight_max_simultaneous",
    "center_highlight_position_variation",
    "show_qr_code",
    "qr_text",
    "qr_size",
    "qr_text_size",
    "qr_position",
    "qr_text_color",
    "qr_dynamic_enabled",
    "qr_show_duration",
    "qr_hide_duration",
    "banner_enabled",
    "banner_text",
    "banner_position",
    "banner_height",
    "banner_color",
    "banner_text_color",
    "banner_show_duration",
    "banner_hide_duration",
    "banner_align",
    "banner_font",
    "cache_enabled",
    "cache_ttl_minutes",
    "cache_max_images",
    "cache_max_videos",
    "cache_max_size_mb",
    "comments_enabled",
    "comment_font",
    "comment_color",
    "comment_size",
    "comment_bold",
    "comment_underline",
    "background_mode",
    "background_color",
    "background_image",
    "background_rotation",
    "background_brightness",
    "background_contrast",
    "background_position",
    "background_scale",
    "background_opacity",
})


def wall_config_from_incoming(incoming: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(incoming, dict):
        raise HTTPException(status_code=400, detail="Keine gültige Config.")
    cfg: dict[str, Any] = {}
    apply_incoming_values(cfg, incoming, SETUP_OWNED_KEYS)
    return cfg


def wall_keys_only(incoming: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in wall_config_from_incoming(incoming).items() if key in WALL_KEYS}


def wall_summary(cfg: dict[str, Any]) -> str:
    view = "Grid" if str(cfg.get("wall_view_mode") or "fly") == "grid" else "Fly"
    spawn = {"lanes": "Bahnen", "burst": "Burst", "random": "Zufall"}.get(
        str(cfg.get("spawn_mode") or "lanes"), "Bahnen"
    )
    qr = "QR an" if cfg.get("show_qr_code") else "QR aus"
    banner = "Banner an" if cfg.get("banner_enabled") else "Banner aus"
    if view == "Grid":
        try:
            cols = int(cfg.get("grid_columns") or 4)
        except (TypeError, ValueError):
            cols = 4
        return f"Grid {cols} Spalten · {qr} · {banner}"
    return f"{view} · {spawn} · {qr} · {banner}"


def _config_from_folder(folder: Path) -> dict[str, Any]:
    cfg_file = folder / "config.json"
    if not cfg_file.is_file():
        return {}
    try:
        with cfg_file.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _template_dir(tid: str) -> Path:
    if not FILE_RE.match(tid or ""):
        raise HTTPException(status_code=400, detail="Ungültige Vorlage.")
    return templates_dir() / tid


def _read_meta(folder: Path) -> dict[str, Any] | None:
    meta_file = folder / "meta.json"
    if not meta_file.is_file():
        return None
    try:
        with meta_file.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return {
        "id": folder.name,
        "name": str(data.get("name") or folder.name),
        "description": str(data.get("description") or ""),
        "created": str(data.get("created") or ""),
    }


def list_templates(*, with_summary: bool = False) -> list[dict[str, Any]]:
    ensure_catalog_dirs()
    items = []
    for folder in sorted(templates_dir().iterdir(), key=lambda p: p.name):
        if not folder.is_dir():
            continue
        meta = _read_meta(folder)
        if not meta:
            continue
        if with_summary:
            meta["summary"] = wall_summary(_config_from_folder(folder))
        items.append(meta)
    items.sort(key=lambda m: (m["name"].lower(), m["id"]))
    return items


def get_template(tid: str) -> dict[str, Any]:
    ensure_catalog_dirs()
    folder = _template_dir(tid)
    meta = _read_meta(folder)
    cfg_file = folder / "config.json"
    if meta is None or not cfg_file.is_file():
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    try:
        with cfg_file.open(encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail="Vorlagen-Config ungültig.") from e
    meta["config"] = wall_config_from_incoming(cfg if isinstance(cfg, dict) else {})
    meta["folder"] = folder
    return meta


def save_template(
    name: str,
    description: str,
    incoming: dict[str, Any],
    assets: list[tuple[str, str, bytes]],
) -> dict[str, Any]:
    ensure_catalog_dirs()
    name = _clean_text(name, NAME_MAX, required=True)
    description = _clean_text(description, DESC_MAX, required=False)
    tid = uuid.uuid4().hex[:12]
    folder = templates_dir() / tid
    folder.mkdir(parents=True, exist_ok=True)
    cfg = wall_config_from_incoming(incoming)
    with (folder / "config.json").open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    meta = {"id": tid, "name": name, "description": description, "created": _now()}
    with (folder / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    for kind, filename, blob in assets:
        if kind not in ("background", "header"):
            continue
        dest_dir = folder / kind
        dest = safe_join(dest_dir, filename)
        if dest is None:
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
    return meta


def update_template_meta(tid: str, name: str | None, description: str | None) -> dict[str, Any]:
    tpl = get_template(tid)
    folder = tpl["folder"]
    meta = {
        "id": tid,
        "name": _clean_text(name, NAME_MAX, required=True) if name is not None else tpl["name"],
        "description": _clean_text(description, DESC_MAX, required=False) if description is not None else tpl["description"],
        "created": tpl["created"],
    }
    with (folder / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    return {k: meta[k] for k in ("id", "name", "description", "created")}


def delete_template(tid: str) -> None:
    folder = _template_dir(tid)
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    shutil.rmtree(folder)


def apply_template(paths, tid: str) -> dict[str, Any]:
    tpl = get_template(tid)
    folder: Path = tpl["folder"]
    cfg = apply_imported_config(paths, tpl["config"])
    for kind in ("background", "header"):
        src = folder / kind
        if not src.is_dir():
            continue
        for item in src.iterdir():
            if not item.is_file():
                continue
            write_imported_asset(paths, kind, item.name, item.read_bytes())
    return cfg


def apply_wall_template(paths, tid: str) -> dict[str, Any]:
    tpl = get_template(tid)
    folder: Path = tpl["folder"]
    cfg = apply_imported_config(paths, wall_keys_only(tpl["config"]))
    src = folder / "background"
    if src.is_dir():
        for item in src.iterdir():
            if item.is_file():
                write_imported_asset(paths, "background", item.name, item.read_bytes())
    return cfg


def save_template_from_project(paths, name: str, description: str) -> dict[str, Any]:
    from server.project import load_project_config

    cfg = wall_keys_only(load_project_config(paths))
    assets: list[tuple[str, str, bytes]] = []
    bg = str(cfg.get("background_image") or "")
    if bg and not is_shared_background(bg):
        src = safe_join(paths.background, bg)
        if src is not None and src.is_file():
            assets.append(("background", src.name, src.read_bytes()))
    return save_template(name, description, cfg, assets)


def _safe_bg_name(original: str) -> str:
    ext = Path(original or "").suffix.lower()
    if ext not in BG_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Nur Bilder (jpg, png, webp, gif).")
    stem = Path(original).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")[:60]
    if not stem:
        stem = "bg"
    name = stem + ext
    if not FILE_RE.match(name):
        name = "bg_" + uuid.uuid4().hex[:10] + ext
    ensure_catalog_dirs()
    dest = shared_bg_dir() / name
    if dest.exists():
        name = stem + "-" + uuid.uuid4().hex[:6] + ext
    return name


def list_shared_backgrounds() -> list[str]:
    ensure_catalog_dirs()
    names = []
    for item in sorted(shared_bg_dir().iterdir(), key=lambda p: p.name.lower()):
        if item.is_file() and item.suffix.lower() in BG_IMAGE_EXT:
            names.append(item.name)
    return names


def shared_value(filename: str) -> str:
    return SHARED_PREFIX + filename


def is_shared_background(value: str) -> bool:
    return str(value or "").startswith(SHARED_PREFIX)


def shared_filename(value: str) -> str:
    raw = str(value or "")
    if raw.startswith(SHARED_PREFIX):
        return raw[len(SHARED_PREFIX):]
    return raw


def shared_background_path(filename: str) -> Path | None:
    name = shared_filename(filename)
    if not FILE_RE.match(name):
        return None
    path = safe_join(shared_bg_dir(), name)
    if path and path.is_file():
        return path
    return None


def save_shared_background(original_name: str, data: bytes) -> str:
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 20 MB).")
    name = _safe_bg_name(original_name)
    ensure_catalog_dirs()
    dest = shared_bg_dir() / name
    dest.write_bytes(data)
    return name


def delete_shared_background(filename: str) -> None:
    path = shared_background_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Hintergrund nicht gefunden.")
    path.unlink()
