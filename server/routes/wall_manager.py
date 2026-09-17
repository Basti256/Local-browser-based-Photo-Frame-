"""Wall-Manager-APIs. Admin mit PIN, Auslieferung an die Wall ohne Login."""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from server.deps import require_admin_pin
from server.project import IMAGE_EXT, VIDEO_EXT, get_paths, require_paths, safe_join
from server.routes.wall import broadcast, clients, require_live_project
from server.wall_manager import (
    MAX_UPLOAD_MB,
    add_asset,
    apply_playlist,
    delete_asset,
    ensure_thumbs,
    jump_playhead,
    load_doc,
    playhead_only,
    resolve_wm_file,
    save_doc,
    tick_playhead,
)
from server.routes.upload import is_valid_image, is_valid_video

router = APIRouter()

WM_UPDATED = "__wall_manager_updated__"
WM_PLAYHEAD = "__wm_playhead__"


async def _notify() -> None:
    await broadcast(WM_UPDATED)


async def _notify_playhead() -> None:
    await broadcast(WM_PLAYHEAD)


def _wall_clients(project: str) -> int:
    return len(clients.get(project) or [])


def _with_wall_clients(payload: dict, project: str) -> dict:
    out = dict(payload or {})
    out["wall_clients"] = _wall_clients(project)
    return out


@router.get("/api/wall-manager")
async def get_wall_manager(_live: str = Depends(require_live_project)):
    paths = require_paths()
    view, changed = tick_playhead(paths)
    if changed:
        await _notify_playhead()
    return view


@router.get("/api/wall-manager/playhead")
async def get_wall_manager_playhead(_live: str = Depends(require_live_project)):
    paths = require_paths()
    ph, changed = playhead_only(paths)
    if changed:
        await _notify_playhead()
    return ph


@router.get("/api/admin/wall-manager")
def admin_get_wall_manager(_project: str = Depends(require_admin_pin)):
    paths = require_paths()
    doc = load_doc(paths)
    if ensure_thumbs(paths, doc):
        save_doc(paths, doc)
    view, _changed = tick_playhead(paths)
    return _with_wall_clients(view, _project)


@router.get("/api/admin/wall-manager/playhead")
async def admin_get_playhead(_project: str = Depends(require_admin_pin)):
    paths = require_paths()
    ph, changed = playhead_only(paths)
    if changed:
        await _notify_playhead()
    return _with_wall_clients(ph, _project)


@router.post("/api/admin/wall-manager/jump")
async def admin_jump_wall_manager(body: dict = Body(...), _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    try:
        index = int(body.get("index"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Index fehlt.")
    view = jump_playhead(paths, index)
    await _notify_playhead()
    await _notify()
    return _with_wall_clients(view["playhead"], _project)


@router.put("/api/admin/wall-manager")
async def admin_save_wall_manager(body: dict = Body(...), _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    view = apply_playlist(paths, body)
    await _notify()
    await _notify_playhead()
    return _with_wall_clients(view, _project)


@router.post("/api/admin/wall-manager/upload")
async def admin_upload_wall_manager(file: UploadFile = File(...), _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    original = file.filename or "upload"
    ext = os.path.splitext(original)[1].lower()
    if ext in IMAGE_EXT:
        media_type = "image"
    elif ext in VIDEO_EXT:
        media_type = "video"
    else:
        raise HTTPException(status_code=400, detail="Nur Bilder und Videos.")
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    stored = f"{uuid.uuid4().hex}{ext}"
    dest = paths.wall_manager / stored
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                buffer.close()
                try:
                    dest.unlink()
                except OSError:
                    pass
                raise HTTPException(status_code=400, detail=f"Datei zu groß. Maximal {MAX_UPLOAD_MB} MB.")
            buffer.write(chunk)
    if media_type == "image" and not is_valid_image(str(dest)):
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Kein gültiges Bild.")
    if media_type == "video" and not is_valid_video(str(dest)):
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Kein gültiges Video.")
    asset = add_asset(paths, stored, original, media_type)
    display = str(asset.get("display") or "")
    thumb = str(asset.get("thumb") or "")
    asset["url"] = f"/wm/{display}" if display else ""
    asset["thumb_url"] = f"/wm/{thumb}" if thumb else ""
    await _notify()
    return asset


@router.delete("/api/admin/wall-manager/asset/{asset_id}")
async def admin_delete_wall_manager_asset(asset_id: str, _project: str = Depends(require_admin_pin)):
    paths = require_paths()
    delete_asset(paths, asset_id)
    await _notify()
    return {"ok": True}


@router.get("/wm/{filename}")
def serve_wall_manager_media(filename: str, _live: str = Depends(require_live_project)):
    paths = get_paths()
    if paths is None:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    if safe_join(paths.wall_manager, filename) is None and safe_join(paths.wall_manager_derived, filename) is None:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    path = resolve_wm_file(paths, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    return FileResponse(path, headers={"Cache-Control": "no-cache"})
