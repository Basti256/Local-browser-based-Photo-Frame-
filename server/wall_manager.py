"""Wall Manager: Clips und Playlist, getrennt von Gäste-Medien."""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from server.project import IMAGE_EXT, VIDEO_EXT, ProjectPaths, safe_join
from server.transcode import (
    ffmpeg_bin,
    make_program_thumb,
    probe_media,
    recommend_program_transcode,
    transcode_program_image,
    transcode_program_video,
)

KINDS = ("photowall", "video", "image", "effect")
MEDIA_KINDS = ("photowall", "video", "image")
PLAYBACK = ("once", "loop", "repeat")
ENTER = ("start", "resume")
EXIT = ("pause", "stop")
EFFECTS = ("fade", "pop", "cut", "dissolve", "wipe")
WIPE_DIRS = ("ltr", "rtl", "ttb", "btt")
TRANSITIONS = ("none", "fade", "pop")
PREFETCH = ("next", "all")
MAX_UPLOAD_MB = 2048

DEFAULT_DOC: dict[str, Any] = {
    "enabled": False,
    "prefetch": "next",
    "mute_all": False,
    "assets": [],
    "playlist": [],
    "playhead": {"index": 0, "started": 0.0},
}

_transcode_lock = threading.Lock()
_play_lock = threading.Lock()


def wm_file(paths: ProjectPaths) -> Path:
    return paths.root / "wall_manager.json"


def ensure_dirs(paths: ProjectPaths) -> None:
    paths.wall_manager.mkdir(parents=True, exist_ok=True)
    paths.wall_manager_derived.mkdir(parents=True, exist_ok=True)


def load_doc(paths: ProjectPaths) -> dict[str, Any]:
    ensure_dirs(paths)
    path = wm_file(paths)
    if not path.is_file():
        return json.loads(json.dumps(DEFAULT_DOC))
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT_DOC))
    if not isinstance(data, dict):
        return json.loads(json.dumps(DEFAULT_DOC))
    out = json.loads(json.dumps(DEFAULT_DOC))
    out["enabled"] = bool(data.get("enabled"))
    pref = str(data.get("prefetch") or "next")
    out["prefetch"] = pref if pref in PREFETCH else "next"
    out["mute_all"] = bool(data.get("mute_all"))
    assets = data.get("assets")
    out["assets"] = [a for a in assets if isinstance(a, dict)] if isinstance(assets, list) else []
    playlist = data.get("playlist")
    out["playlist"] = [p for p in playlist if isinstance(p, dict)] if isinstance(playlist, list) else []
    ph = data.get("playhead")
    if isinstance(ph, dict):
        try:
            out["playhead"] = {
                "index": int(ph.get("index") or 0),
                "started": float(ph.get("started") or 0),
            }
        except (TypeError, ValueError):
            out["playhead"] = {"index": 0, "started": 0.0}
    else:
        out["playhead"] = {"index": 0, "started": 0.0}
    migrated = [compact_item(p) for p in recover_converted_effects(out["playlist"])]
    if _stored_playlist_dirty(out["playlist"], migrated):
        out["playlist"] = migrated
        save_doc(paths, out)
    return out


def save_doc(paths: ProjectPaths, doc: dict[str, Any]) -> None:
    ensure_dirs(paths)
    payload = {
        "enabled": bool(doc.get("enabled")),
        "prefetch": doc.get("prefetch") if doc.get("prefetch") in PREFETCH else "next",
        "mute_all": bool(doc.get("mute_all")),
        "assets": doc.get("assets") if isinstance(doc.get("assets"), list) else [],
        "playlist": doc.get("playlist") if isinstance(doc.get("playlist"), list) else [],
        "playhead": doc.get("playhead") if isinstance(doc.get("playhead"), dict) else {"index": 0, "started": 0.0},
    }
    with wm_file(paths).open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def public_view(doc: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    assets = []
    for raw in doc.get("assets") or []:
        if not isinstance(raw, dict):
            continue
        display = str(raw.get("display") or raw.get("original") or "")
        thumb = str(raw.get("thumb") or "")
        assets.append({
            "id": raw.get("id"),
            "type": raw.get("type"),
            "title": raw.get("title") or display,
            "display": display,
            "thumb": thumb,
            "width": int(raw.get("width") or 0),
            "height": int(raw.get("height") or 0),
            "duration_sec": float(raw.get("duration_sec") or 0),
            "transcode_status": raw.get("transcode_status") or "ready",
            "recommend_transcode": bool(raw.get("recommend_transcode")),
            "url": f"/wm/{display}" if display else "",
            "thumb_url": f"/wm/{thumb}" if thumb else "",
        })
    view_playlist = [normalize_item(p) for p in with_legacy_effects(doc.get("playlist") or [])]
    return {
        "enabled": bool(doc.get("enabled")),
        "prefetch": doc.get("prefetch") if doc.get("prefetch") in PREFETCH else "next",
        "mute_all": bool(doc.get("mute_all")),
        "ffmpeg": ffmpeg_bin() is not None,
        "assets": assets,
        "playlist": view_playlist,
        "playhead": playhead_snapshot(doc, view_playlist, now),
    }


def recover_converted_effects(playlist: list[Any]) -> list[dict[str, Any]]:
    """Alte Saves haben Effekt-Zeilen als Photowall 12 min mit transition=fade geschrieben."""
    out: list[dict[str, Any]] = []
    for raw in playlist:
        if not isinstance(raw, dict):
            continue
        if _is_converted_effect(raw):
            trans = str(raw.get("effect") or raw.get("transition") or "fade").strip().lower()
            if trans not in EFFECTS:
                trans = "fade"
            out.append({
                "id": str(raw.get("id") or uuid.uuid4().hex),
                "kind": "effect",
                "effect": trans,
                "duration_sec": _clip_float(raw.get("duration_sec"), 5, 0.2, 60),
            })
            continue
        out.append(raw)
    return out


def _is_converted_effect(raw: dict[str, Any]) -> bool:
    kind = str(raw.get("kind") or "").strip().lower()
    if kind == "effect" or kind in EFFECTS:
        return False
    if kind != "photowall":
        return False
    trans = str(raw.get("transition") or raw.get("effect") or "").strip().lower()
    if trans not in ("fade", "pop"):
        return False
    try:
        minutes = float(raw.get("photowall_minutes") if raw.get("photowall_minutes") is not None else 12)
    except (TypeError, ValueError):
        minutes = 12.0
    if abs(minutes - 12.0) > 0.001:
        return False
    if str(raw.get("enter") or "start") != "start":
        return False
    if str(raw.get("exit") or "pause") != "pause":
        return False
    return True


def _stored_playlist_dirty(raw_list: list[dict[str, Any]], migrated: list[dict[str, Any]]) -> bool:
    for raw in raw_list:
        if _is_converted_effect(raw):
            return True
        if str(raw.get("kind") or "") == "effect" and ("photowall_minutes" in raw or "transition" in raw):
            return True
    return False


def with_legacy_effects(playlist: list[Any]) -> list[dict[str, Any]]:
    items = recover_converted_effects(playlist)
    if any(str(p.get("kind")) == "effect" for p in items):
        return items
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(items):
        if i > 0:
            trans = str(raw.get("transition") or items[i - 1].get("transition") or "")
            if trans in ("fade", "pop"):
                out.append({
                    "id": uuid.uuid4().hex,
                    "kind": "effect",
                    "effect": trans,
                    "duration_sec": 5,
                })
        out.append(raw)
    return out


def _item_kind(raw: dict[str, Any]) -> str:
    kind = str(raw.get("kind") or "").strip().lower()
    if kind in EFFECTS or kind == "effect":
        return "effect"
    if _is_converted_effect(raw):
        return "effect"
    if kind in MEDIA_KINDS:
        return kind
    effect = str(raw.get("effect") or "").strip().lower()
    if effect in EFFECTS and kind not in MEDIA_KINDS:
        return "effect"
    return "photowall"


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    kind = _item_kind(raw)
    playback = str(raw.get("playback") or "once")
    if playback not in PLAYBACK:
        playback = "once"
    enter = str(raw.get("enter") or "start")
    if enter not in ENTER:
        enter = "start"
    exit_mode = str(raw.get("exit") or "pause")
    if exit_mode not in EXIT:
        exit_mode = "pause"
    if kind == "effect":
        effect = str(raw.get("effect") or raw.get("kind") or "fade").strip().lower()
        if effect in ("effect",):
            effect = "fade"
        if effect not in EFFECTS:
            effect = "fade"
        out: dict[str, Any] = {
            "id": str(raw.get("id") or uuid.uuid4().hex),
            "kind": "effect",
            "effect": effect,
            "duration_sec": _clip_float(raw.get("duration_sec"), 5, 0.2, 60),
        }
        if effect == "wipe":
            direction = str(raw.get("direction") or "ltr").strip().lower()
            if direction not in WIPE_DIRS:
                direction = "ltr"
            out["direction"] = direction
        return out
    asset_id = str(raw.get("asset_id") or "").strip() or None
    item: dict[str, Any] = {
        "id": str(raw.get("id") or uuid.uuid4().hex),
        "kind": kind,
        "asset_id": asset_id,
        "playback": playback,
        "show_banner": bool(raw.get("show_banner", True)),
        "show_qr": bool(raw.get("show_qr", True)),
        "mute": bool(raw.get("mute")),
    }
    if kind == "photowall":
        item["photowall_minutes"] = _clip_float(raw.get("photowall_minutes"), 12, 0.1, 24 * 60)
        item["photowall_preload_sec"] = _clip_float(raw.get("photowall_preload_sec"), 15, 0, 300)
        item["enter"] = enter
        item["exit"] = exit_mode
        return item
    item["loop_minutes"] = _clip_float(raw.get("loop_minutes"), 5, 0.1, 24 * 60)
    item["repeat_count"] = _clip_int(raw.get("repeat_count"), 2, 1, 99)
    if kind == "image":
        item["image_seconds"] = _clip_float(raw.get("image_seconds"), 8, 0.5, 3600)
    return item


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return normalize_item(item)


def _clip_float(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        n = default
    if n != n:  # NaN
        n = default
    return max(lo, min(hi, n))


def _clip_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def validate_playlist(playlist: list[dict[str, Any]], assets: list[dict[str, Any]]) -> list[str]:
    """Warnungen/Fehler. Leere Liste = ok."""
    errors: list[str] = []
    by_id = {str(a.get("id")): a for a in assets if isinstance(a, dict) and a.get("id")}
    paused = False
    items = [normalize_item(p) for p in playlist]
    if not items:
        return errors
    for i, item in enumerate(items, start=1):
        if item["kind"] == "effect":
            continue
        if item["kind"] in ("video", "image"):
            aid = item.get("asset_id")
            if not aid or aid not in by_id:
                errors.append(f"Zeile {i}: Datei fehlt.")
                continue
            atype = str(by_id[aid].get("type") or "")
            if atype != item["kind"]:
                errors.append(f"Zeile {i}: Dateityp passt nicht ({atype}).")
            continue
        if item["enter"] == "resume" and not paused:
            errors.append(f"Zeile {i}: Photowall fortsetzen ohne vorheriges Pausieren.")
        if item["enter"] == "start":
            paused = False
        if item["exit"] == "pause":
            paused = True
        else:
            paused = False
    return errors


def _asset_by_id(assets: list[dict[str, Any]], asset_id: str | None) -> dict[str, Any] | None:
    if not asset_id:
        return None
    for asset in assets:
        if str(asset.get("id")) == str(asset_id):
            return asset
    return None


def item_duration_sec(item: dict[str, Any], assets: list[dict[str, Any]]) -> float:
    item = normalize_item(item)
    if item["kind"] == "effect":
        if item["effect"] == "fade":
            return max(0.4, float(item.get("duration_sec") or 5) * 2)
        if item["effect"] == "pop":
            return 0.85
        if item["effect"] in ("dissolve", "wipe"):
            return max(0.2, float(item.get("duration_sec") or 5))
        return 0.05
    if item["kind"] == "photowall":
        return max(1.0, float(item.get("photowall_minutes") or 12) * 60)
    asset = _asset_by_id(assets, item.get("asset_id"))
    playback = item.get("playback") or "once"
    if item["kind"] == "image":
        once = float(item.get("image_seconds") or 8)
        if playback == "loop":
            return max(1.0, float(item.get("loop_minutes") or 5) * 60)
        if playback == "repeat":
            return max(0.5, float(item.get("repeat_count") or 1) * once)
        return max(0.5, once)
    once = float((asset or {}).get("duration_sec") or 8)
    if once <= 0:
        once = 8.0
    if playback == "loop":
        return max(1.0, float(item.get("loop_minutes") or 5) * 60)
    if playback == "repeat":
        return max(0.5, float(item.get("repeat_count") or 1) * once)
    return max(0.5, once)


def playhead_snapshot(doc: dict[str, Any], playlist: list[dict[str, Any]] | None = None, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    items = playlist if playlist is not None else [normalize_item(p) for p in with_legacy_effects(doc.get("playlist") or [])]
    ph = doc.get("playhead") if isinstance(doc.get("playhead"), dict) else {}
    try:
        idx = int(ph.get("index") or 0)
    except (TypeError, ValueError):
        idx = 0
    try:
        started = float(ph.get("started") or 0)
    except (TypeError, ValueError):
        started = 0.0
    if not items or not doc.get("enabled"):
        return {
            "index": -1,
            "started": 0.0,
            "elapsed_sec": 0.0,
            "duration_sec": 0.0,
            "now": now,
            "item_id": None,
            "kind": None,
        }
    if idx < 0 or idx >= len(items):
        idx = 0
    dur = item_duration_sec(items[idx], doc.get("assets") or [])
    elapsed = max(0.0, now - started) if started else 0.0
    if dur > 0:
        elapsed = min(elapsed, dur)
    item = items[idx]
    return {
        "index": idx,
        "started": started,
        "elapsed_sec": round(elapsed, 3),
        "duration_sec": round(dur, 3),
        "now": now,
        "item_id": item.get("id"),
        "kind": item.get("kind"),
    }


def _advance_unlocked(doc: dict[str, Any], items: list[dict[str, Any]], now: float) -> bool:
    if not doc.get("enabled") or not items:
        return False
    ph = doc.get("playhead") if isinstance(doc.get("playhead"), dict) else {}
    try:
        idx = int(ph.get("index") or 0)
    except (TypeError, ValueError):
        idx = 0
    try:
        started = float(ph.get("started") or 0)
    except (TypeError, ValueError):
        started = 0.0
    if idx < 0 or idx >= len(items):
        idx = 0
    if started <= 0:
        doc["playhead"] = {"index": idx, "started": now}
        return True
    assets = doc.get("assets") or []
    hops = 0
    changed = False
    while hops <= len(items) + 1:
        dur = item_duration_sec(items[idx], assets)
        if dur <= 0:
            dur = 0.05
        if now - started < dur:
            break
        started += dur
        idx = (idx + 1) % len(items)
        hops += 1
        changed = True
        landed = items[idx]
        if landed.get("kind") == "effect" and landed.get("effect") in ("cut", "pop"):
            break
    if hops > len(items) + 1:
        idx = 0
        started = now
        changed = True
    old = doc.get("playhead") if isinstance(doc.get("playhead"), dict) else {}
    if int(old.get("index") or 0) != idx or abs(float(old.get("started") or 0) - started) > 0.001:
        changed = True
    doc["playhead"] = {"index": idx, "started": started}
    return changed


def tick_playhead(paths: ProjectPaths) -> tuple[dict[str, Any], bool]:
    with _play_lock:
        doc = load_doc(paths)
        items = [normalize_item(p) for p in with_legacy_effects(doc.get("playlist") or [])]
        now = time.time()
        changed = _advance_unlocked(doc, items, now)
        if changed:
            save_doc(paths, doc)
        return public_view(doc, now), changed


def playhead_only(paths: ProjectPaths) -> tuple[dict[str, Any], bool]:
    view, changed = tick_playhead(paths)
    return view["playhead"], changed


def jump_playhead(paths: ProjectPaths, index: int) -> dict[str, Any]:
    with _play_lock:
        doc = load_doc(paths)
        items = [normalize_item(p) for p in with_legacy_effects(doc.get("playlist") or [])]
        if not items:
            raise HTTPException(status_code=400, detail="Playlist ist leer.")
        if index < 0 or index >= len(items):
            raise HTTPException(status_code=400, detail="Ungültiger Playlist-Punkt.")
        now = time.time()
        doc["playhead"] = {"index": int(index), "started": now}
        save_doc(paths, doc)
        return public_view(doc, now)


def thumb_name(display: str) -> str:
    stem = Path(display).stem or "thumb"
    return f"{stem}_thumb.jpg"


def ensure_asset_thumb(paths: ProjectPaths, asset: dict[str, Any]) -> bool:
    thumb = str(asset.get("thumb") or "")
    if thumb:
        existing = safe_join(paths.wall_manager_derived, Path(thumb).name)
        if existing and existing.is_file():
            return False
    display = str(asset.get("display") or asset.get("original") or "")
    if not display:
        return False
    name = thumb_name(display)
    dest = paths.wall_manager_derived / name
    if dest.is_file():
        asset["thumb"] = name
        return True
    src = resolve_wm_file(paths, display)
    if src is None:
        src = safe_join(paths.wall_manager, str(asset.get("original") or ""))
    if src is None or not src.is_file():
        return False
    media_type = str(asset.get("type") or "image")
    if make_program_thumb(src, dest, media_type):
        asset["thumb"] = name
        return True
    return False


def ensure_thumbs(paths: ProjectPaths, doc: dict[str, Any]) -> bool:
    changed = False
    for asset in doc.get("assets") or []:
        if isinstance(asset, dict) and ensure_asset_thumb(paths, asset):
            changed = True
    return changed


def add_asset(paths: ProjectPaths, stored_name: str, title: str, media_type: str) -> dict[str, Any]:
    ensure_dirs(paths)
    src = safe_join(paths.wall_manager, stored_name)
    if src is None or not src.is_file():
        raise HTTPException(status_code=400, detail="Datei nicht gespeichert.")
    probe = probe_media(src)
    recommend = recommend_program_transcode(src, media_type, probe)
    asset = {
        "id": uuid.uuid4().hex,
        "type": media_type,
        "title": title or stored_name,
        "original": stored_name,
        "display": stored_name,
        "width": int(probe.get("width") or 0),
        "height": int(probe.get("height") or 0),
        "duration_sec": float(probe.get("duration_sec") or 0),
        "codec": probe.get("codec") or "",
        "transcode_status": "pending" if recommend else "ready",
        "recommend_transcode": recommend,
        "transcode_error": "",
    }
    if recommend:
        ok = _run_transcode(paths, asset)
        if not ok and not ffmpeg_bin() and media_type == "video":
            asset["transcode_status"] = "skipped"
            asset["transcode_error"] = "ffmpeg fehlt, Original wird verwendet."
        elif not ok and media_type == "image":
            asset["transcode_status"] = "ready"
            asset["recommend_transcode"] = False
        elif not ok:
            asset["transcode_status"] = "error"
            if not asset.get("transcode_error"):
                asset["transcode_error"] = "Umwandlung fehlgeschlagen."
    ensure_asset_thumb(paths, asset)
    doc = load_doc(paths)
    doc["assets"].append(asset)
    save_doc(paths, doc)
    return asset


def _run_transcode(paths: ProjectPaths, asset: dict[str, Any]) -> bool:
    src = safe_join(paths.wall_manager, str(asset.get("original") or ""))
    if src is None or not src.is_file():
        return False
    with _transcode_lock:
        if asset.get("type") == "image":
            dest_name = Path(str(asset["original"])).stem + ".jpg"
            dest = paths.wall_manager_derived / dest_name
            if transcode_program_image(src, dest):
                asset["display"] = dest_name
                probe = probe_media(dest)
                asset["width"] = int(probe.get("width") or asset.get("width") or 0)
                asset["height"] = int(probe.get("height") or asset.get("height") or 0)
                asset["transcode_status"] = "ready"
                asset["recommend_transcode"] = False
                return True
            return False
        dest_name = Path(str(asset["original"])).stem + ".mp4"
        dest = paths.wall_manager_derived / dest_name
        if transcode_program_video(src, dest):
            asset["display"] = dest_name
            probe = probe_media(dest)
            asset["width"] = int(probe.get("width") or asset.get("width") or 0)
            asset["height"] = int(probe.get("height") or asset.get("height") or 0)
            asset["duration_sec"] = float(probe.get("duration_sec") or asset.get("duration_sec") or 0)
            asset["codec"] = probe.get("codec") or "h264"
            asset["transcode_status"] = "ready"
            asset["recommend_transcode"] = False
            return True
        return False


def delete_asset(paths: ProjectPaths, asset_id: str) -> None:
    doc = load_doc(paths)
    asset = next((a for a in doc["assets"] if str(a.get("id")) == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    for key in ("original", "display", "thumb"):
        name = str(asset.get(key) or "")
        for folder in (paths.wall_manager, paths.wall_manager_derived):
            target = safe_join(folder, name)
            if target and target.is_file():
                try:
                    target.unlink()
                except OSError:
                    pass
    doc["assets"] = [a for a in doc["assets"] if str(a.get("id")) != asset_id]
    for item in doc["playlist"]:
        if str(item.get("asset_id")) == asset_id:
            item["asset_id"] = None
    save_doc(paths, doc)


def apply_playlist(paths: ProjectPaths, body: dict[str, Any]) -> dict[str, Any]:
    doc = load_doc(paths)
    playlist = body.get("playlist")
    if not isinstance(playlist, list):
        raise HTTPException(status_code=400, detail="Playlist fehlt.")
    items = [compact_item(p) for p in with_legacy_effects(playlist)]
    errors = validate_playlist(items, doc["assets"])
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))
    was_on = bool(doc.get("enabled"))
    doc["enabled"] = bool(body.get("enabled"))
    pref = str(body.get("prefetch") or doc.get("prefetch") or "next")
    doc["prefetch"] = pref if pref in PREFETCH else "next"
    doc["mute_all"] = bool(body.get("mute_all"))
    doc["playlist"] = items
    ph = doc.get("playhead") if isinstance(doc.get("playhead"), dict) else {"index": 0, "started": 0.0}
    if items:
        jump = body.get("jump", body.get("jump_index"))
        if jump is not None and jump != "":
            try:
                idx = int(jump)
            except (TypeError, ValueError):
                idx = 0
            if idx < 0 or idx >= len(items):
                raise HTTPException(status_code=400, detail="Ungültiger Playlist-Punkt.")
            doc["playhead"] = {"index": idx, "started": time.time()}
        else:
            try:
                idx = int(ph.get("index") or 0)
            except (TypeError, ValueError):
                idx = 0
            if idx < 0 or idx >= len(items):
                idx = 0
            started = float(ph.get("started") or 0)
            if not was_on and doc["enabled"]:
                started = time.time()
            elif started <= 0 and doc["enabled"]:
                started = time.time()
            doc["playhead"] = {"index": idx, "started": started}
    else:
        doc["playhead"] = {"index": 0, "started": 0.0}
    save_doc(paths, doc)
    return public_view(doc)


def resolve_wm_file(paths: ProjectPaths, filename: str) -> Path | None:
    derived = safe_join(paths.wall_manager_derived, filename)
    if derived and derived.is_file():
        return derived
    original = safe_join(paths.wall_manager, filename)
    if original and original.is_file():
        return original
    return None
