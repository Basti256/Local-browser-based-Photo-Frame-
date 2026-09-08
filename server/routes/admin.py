"""Admin-APIs. PIN-Sitzung erforderlich."""
from __future__ import annotations

import socket
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timezone

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from server import stats
from server.deps import require_admin_pin
from server.hidden import drop_hidden, is_hidden, set_hidden, set_hidden_many
from server.network import get_network_info
from server.pin import (
    admin_project,
    has_pin,
    set_admin_session,
    try_pin,
    wait_seconds_remaining,
)
from server.project import IMAGE_EXT, VIDEO_EXT, get_paths, require_paths, safe_join
from server.routes.wall import broadcast, broadcast_config, broadcast_hide, clients
from server.transcode import display_name_for

router = APIRouter()

BG_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


class PinBody(BaseModel):
    pin: str


class HideBody(BaseModel):
    hidden: bool


class BatchBody(BaseModel):
    names: list[str]
    action: str


@router.get("/api/admin/pin-status")
def pin_status(request: Request):
    paths = get_paths()
    if paths is None:
        return {"has_project": False, "has_pin": False, "unlocked": False, "wait_seconds": 0}
    unlocked = admin_project(request) == paths.name
    return {
        "has_project": True,
        "project": paths.name,
        "has_pin": has_pin(paths),
        "unlocked": unlocked,
        "wait_seconds": round(wait_seconds_remaining(paths), 1),
    }


@router.post("/api/admin/unlock")
def admin_unlock(body: PinBody, request: Request):
    paths = require_paths()
    try_pin(paths, body.pin)
    response = JSONResponse({"ok": True, "project": paths.name})
    set_admin_session(response, paths.name, request)
    return response



@router.get("/api/admin/stats")
def admin_stats(_project: str = Depends(require_admin_pin)):
    paths = get_paths()
    media_images = 0
    media_videos = 0
    if paths and paths.media.is_dir():
        for f in paths.media.iterdir():
            ext = f.suffix.lower()
            if ext in IMAGE_EXT:
                media_images += 1
            elif ext in VIDEO_EXT:
                media_videos += 1
    now = time.time()
    viewers = stats.upload_viewers(_project)
    upload_viewers = sum(1 for t in viewers.values() if now - t <= stats.VIEWER_TIMEOUT)
    net = get_network_info()
    st = stats.wall_stats(_project)
    group = clients.get(_project) or []
    return {
        "wall_images_displayed": st.get("images", 0),
        "wall_videos_displayed": st.get("videos", 0),
        "media_images_count": media_images,
        "media_videos_count": media_videos,
        "upload_page_viewers": upload_viewers,
        "uploads_in_progress": stats.uploads_in_progress(_project),
        "wall_connected": len(group) > 0,
        "wall_clients": len(group),
        "server_online_since": stats.server_start_time,
        "network_mode": net.get("mode", ""),
        "network_port": net.get("port", ""),
        "local_ip": net.get("local_ip", ""),
        "external_ip": net.get("external_ip") or "",
        "base_url": net.get("base_url", ""),
        "public_https": net.get("public_https", False),
    }


@router.post("/api/admin/wall-reload")
async def wall_reload(_project: str = Depends(require_admin_pin)):
    n = len(clients.get(_project) or [])
    await broadcast_config(reload_full=True, project=_project)
    return {"ok": True, "walls": n}


@router.get("/api/network_test")
def network_test(_project: str = Depends(require_admin_pin)):
    info = get_network_info()
    port = info.get("port")
    local_ip = info.get("local_ip")
    external_ip = info.get("external_ip")
    result = {
        "local_ok": False,
        "public_ok": False,
        "local_url": f"http://{local_ip}:{port}",
        "public_url": f"http://{external_ip}:{port}" if external_ip else None,
        "port": port,
    }
    try:
        with socket.create_connection((local_ip, port), timeout=2):
            result["local_ok"] = True
    except Exception:
        pass
    if external_ip:
        try:
            with socket.create_connection((external_ip, port), timeout=2):
                result["public_ok"] = True
        except Exception:
            pass
    return result


@router.get("/api/background/list")
def background_list(_project: str = Depends(require_admin_pin)):
    from server.catalog import list_shared_backgrounds, shared_value
    paths = require_paths()
    files = []
    if paths.background.is_dir():
        for f in sorted(paths.background.iterdir()):
            if f.is_file() and f.suffix.lower() in BG_IMAGE_EXT:
                files.append(f.name)
    for name in list_shared_backgrounds():
        files.append(shared_value(name))
    return files


@router.post("/api/background/upload")
async def background_upload(file: UploadFile = File(...), _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    ext = os_ext(file.filename or "")
    if ext not in BG_IMAGE_EXT:
        return {"ok": False, "error": "Nur Bilder erlaubt (jpg, png, webp, gif)"}
    filename = f"bg_{uuid.uuid4().hex[:10]}{ext}"
    dest = safe_join(paths.background, filename)
    if dest is None:
        return {"ok": False, "error": "Ungültiger Dateiname"}
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        return {"ok": False, "error": "Datei zu groß (max 20 MB)"}
    dest.write_bytes(content)
    return {"ok": True, "filename": filename}


@router.get("/api/header/list")
def header_list(_project: str = Depends(require_admin_pin)):
    paths = require_paths()
    if not paths.header.is_dir():
        return []
    files = []
    for f in sorted(paths.header.iterdir()):
        if f.is_file() and f.suffix.lower() in BG_IMAGE_EXT:
            files.append(f.name)
    return files


@router.post("/api/header/upload")
async def header_upload(file: UploadFile = File(...), _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    paths.header.mkdir(parents=True, exist_ok=True)
    ext = os_ext(file.filename or "")
    if ext not in BG_IMAGE_EXT:
        return {"ok": False, "error": "Nur Bilder erlaubt (jpg, png, webp, gif)"}
    filename = f"hdr_{uuid.uuid4().hex[:10]}{ext}"
    dest = safe_join(paths.header, filename)
    if dest is None:
        return {"ok": False, "error": "Ungültiger Dateiname"}
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        return {"ok": False, "error": "Datei zu groß (max 20 MB)"}
    dest.write_bytes(content)
    return {"ok": True, "filename": filename}


@router.get("/api/admin/media")
def admin_media_list(_project: str = Depends(require_admin_pin)):
    paths = require_paths()
    items = []
    if paths.media.is_dir():
        files = [f for f in paths.media.iterdir() if f.is_file() and f.suffix.lower() != ".txt"]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files:
            ext = f.suffix.lower()
            if ext in IMAGE_EXT:
                kind = "image"
            elif ext in VIDEO_EXT:
                kind = "video"
            else:
                continue
            items.append({
                "name": f.name,
                "display": display_name_for(f.name, paths.derived),
                "kind": kind,
                "size": f.stat().st_size,
                "mtime": int(f.stat().st_mtime),
                "hidden": is_hidden(paths, f.name),
            })
    return {"project": paths.name, "items": items}


def _iter_media_files(paths):
    if not paths.media.is_dir():
        return
    for f in sorted(paths.media.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXT | VIDEO_EXT:
            yield f


def _delete_one(paths, filename: str) -> str:
    original = safe_join(paths.media, filename)
    if original is None or not original.is_file():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    display = display_name_for(filename, paths.derived)
    derived = safe_join(paths.derived, display)
    comment = safe_join(paths.media, Path(filename).stem + ".txt")
    original.unlink()
    if derived is not None and derived.is_file() and derived != original:
        derived.unlink()
    if comment is not None and comment.is_file():
        comment.unlink()
    drop_hidden(paths, filename)
    return display


@router.get("/api/admin/media/archive")
def admin_media_archive(_project: str = Depends(require_admin_pin)):
    paths = require_paths()
    tmp = tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024)
    count = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as zf:
        used = set()
        for f in _iter_media_files(paths):
            name = f.name
            if name in used:
                continue
            used.add(name)
            zf.write(f, name)
            count += 1
    if count == 0:
        tmp.close()
        raise HTTPException(status_code=404, detail="Keine Medien.")
    tmp.seek(0)

    def chunks():
        try:
            while True:
                data = tmp.read(1024 * 1024)
                if not data:
                    break
                yield data
        finally:
            tmp.close()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"{paths.name}_medien_{stamp}.zip"
    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/admin/media/batch")
async def admin_media_batch(body: BatchBody, _project: str = Depends(require_admin_pin)):
    action = (body.action or "").strip().lower()
    if action not in ("hide", "show", "delete"):
        raise HTTPException(status_code=400, detail="Aktion: hide, show oder delete.")
    names = []
    for raw in body.names or []:
        name = str(raw or "").strip()
        if name and name == Path(name).name and name not in names:
            names.append(name)
        if len(names) >= 5000:
            break
    if not names:
        raise HTTPException(status_code=400, detail="Keine Dateien angegeben.")
    paths = require_paths()
    if action == "delete":
        displays = []
        missing = 0
        for name in names:
            try:
                displays.append(_delete_one(paths, name))
            except HTTPException as e:
                if e.status_code == 404:
                    missing += 1
                    continue
                raise
        for display in displays:
            await broadcast_hide(display)
        return {"ok": True, "action": "delete", "count": len(displays), "missing": missing}
    hidden = action == "hide"
    done = set_hidden_many(paths, names, hidden)
    for name in done:
        display = display_name_for(name, paths.derived)
        if hidden:
            await broadcast_hide(display)
        else:
            await broadcast(display)
    return {"ok": True, "action": action, "count": len(done), "hidden": hidden}


@router.delete("/api/admin/media/{filename}")
async def admin_media_delete(filename: str, _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    display = _delete_one(paths, filename)
    await broadcast_hide(display)
    return {"ok": True, "display": display}


@router.post("/api/admin/media/{filename}/hide")
async def admin_media_hide(
    filename: str,
    body: HideBody,
    _project: str = Depends(require_admin_pin),
):
    paths = require_paths()
    hidden = set_hidden(paths, filename, body.hidden)
    display = display_name_for(filename, paths.derived)
    if hidden:
        await broadcast_hide(display)
    else:
        await broadcast(display)
    return {"ok": True, "hidden": hidden, "display": display}


def os_ext(name: str) -> str:
    return Path(name).suffix.lower()
