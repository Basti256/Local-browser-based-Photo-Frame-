"""Gäste-Upload. Ohne Anmeldung."""
from __future__ import annotations

import os
import time
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from server import stats
from server.debug_comments import generate_random_comment
from server.project import IMAGE_EXT, VIDEO_EXT, load_project_config, require_paths
from server.routes.wall import broadcast
from server.transcode import transcode_upload

register_heif_opener()

router = APIRouter()

VIDEO_SIGNATURES = [
    (b"ftyp", 4),
    (b"\x1a\x45\xdf\xa3", 0),
]


def is_valid_image(file_path: str) -> bool:
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def is_valid_video(file_path: str) -> bool:
    try:
        with open(file_path, "rb") as f:
            header = f.read(32)
        for sig, offset in VIDEO_SIGNATURES:
            if header[offset:offset + len(sig)] == sig:
                return True
        return False
    except Exception:
        return False


def process_image(file_path: str) -> str:
    try:
        ext = os.path.splitext(file_path)[1].lower()
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        if ext in [".jpg", ".jpeg"]:
            img = img.convert("RGB")
            img.save(file_path, "JPEG", quality=95)
            return os.path.basename(file_path)
        new_path = os.path.splitext(file_path)[0] + ".jpg"
        img = img.convert("RGB")
        img.save(new_path, "JPEG", quality=95)
        if os.path.exists(new_path):
            os.remove(file_path)
            return os.path.basename(new_path)
        return os.path.basename(file_path)
    except Exception as e:
        print("Image processing error:", e)
        return os.path.basename(file_path)


@router.get("/api/upload_heartbeat")
def upload_heartbeat(request: Request):
    ip = request.client.host if request.client else "unknown"
    viewers = stats.upload_viewers()
    viewers[ip] = time.time()
    now = time.time()
    expired = [k for k, v in viewers.items() if now - v > stats.VIEWER_TIMEOUT]
    for k in expired:
        del viewers[k]
    return {"ok": True}


@router.post("/upload")
async def upload(file: UploadFile = File(...), comment: str = Form("")):
    stats.bump_uploads(1)
    try:
        return await _do_upload(file, comment)
    finally:
        stats.bump_uploads(-1)


async def _do_upload(file: UploadFile, comment: str):
    paths = require_paths()
    config = load_project_config(paths)
    allow_videos = config.get("upload_allow_videos", True)
    max_size_mb = config.get("upload_max_file_size_mb", 50)
    max_size_bytes = max_size_mb * 1024 * 1024

    original = file.filename or "upload"
    ext = os.path.splitext(original)[1].lower()
    allowed = set(IMAGE_EXT)
    if allow_videos:
        allowed.update(VIDEO_EXT)
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Diese Datei ist kein Bild oder Video.")

    if file.size and file.size > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"Datei zu groß. Maximal {max_size_mb} MB erlaubt.")

    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = str(paths.media / filename)
    with open(file_path, "wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            buffer.write(chunk)

    if os.path.getsize(file_path) > max_size_bytes:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Datei zu groß. Maximal {max_size_mb} MB erlaubt.")

    if ext in IMAGE_EXT:
        if not is_valid_image(file_path):
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Diese Datei ist kein gültiges Bild.")
        filename = process_image(file_path)
        file_path = str(paths.media / filename)
    elif ext in VIDEO_EXT:
        if not allow_videos:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Video-Upload ist deaktiviert.")
        if not is_valid_video(file_path):
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Diese Datei ist kein gültiges Video.")

    try:
        max_len = int(config.get("comment_max_length", 80))
    except (TypeError, ValueError):
        max_len = 80
    max_len = max(1, min(500, max_len))
    text = (comment or "").strip()
    if not text and config.get("debug_random_comments"):
        text = generate_random_comment(max_len)
    if text:
        comment_file = paths.media / (os.path.splitext(filename)[0] + ".txt")
        comment_file.write_text("".join(list(text)[:max_len]), encoding="utf-8")

    display = transcode_upload(paths, filename, config)
    await broadcast(display)
    return {"status": "success", "file": display}
