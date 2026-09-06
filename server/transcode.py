"""Serverseitiges Transcoding. Originale bleiben erhalten."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from server.project import IMAGE_EXT, VIDEO_EXT, ProjectPaths

IMAGE_OUT_EXT = ".jpg"


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def display_name_for(original_name: str, derived_dir: Path) -> str:
    stem = Path(original_name).stem
    ext = Path(original_name).suffix.lower()
    if ext in VIDEO_EXT:
        candidate = stem + ".mp4"
        if (derived_dir / candidate).is_file():
            return candidate
        return original_name
    if (derived_dir / original_name).is_file():
        return original_name
    jpg = stem + IMAGE_OUT_EXT
    if (derived_dir / jpg).is_file():
        return jpg
    return original_name


def transcode_upload(paths: ProjectPaths, stored_name: str, config: dict) -> str:
    if not config.get("transcode_enabled", True):
        return stored_name
    src = paths.media / stored_name
    if not src.is_file():
        return stored_name
    ext = src.suffix.lower()
    try:
        if ext in IMAGE_EXT or ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return _transcode_image(paths, stored_name, config)
        if ext in VIDEO_EXT:
            return _transcode_video(paths, stored_name)
    except Exception as exc:
        print("[Transcode] Fehler:", exc)
    return stored_name


def _transcode_image(paths: ProjectPaths, stored_name: str, config: dict) -> str:
    src = paths.media / stored_name
    dest_name = Path(stored_name).stem + IMAGE_OUT_EXT
    dest = paths.derived / dest_name
    max_edge = int(config.get("transcode_image_max_edge") or 1920)
    quality = int(config.get("transcode_image_quality") or 85)
    max_edge = max(320, min(max_edge, 4096))
    quality = max(40, min(quality, 95))
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((max_edge, max_edge))
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "JPEG", quality=quality, optimize=True)
    if dest.is_file():
        return dest_name
    return stored_name


def _transcode_video(paths: ProjectPaths, stored_name: str) -> str:
    binary = ffmpeg_bin()
    if not binary:
        print("[Transcode] ffmpeg nicht gefunden, Original wird verwendet.")
        return stored_name
    src = paths.media / stored_name
    dest_name = Path(stored_name).stem + ".mp4"
    dest = paths.derived / dest_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary, "-y", "-i", str(src),
        "-vf", "scale='min(1920,iw)':-2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ac", "2", "-b:a", "128k",
        "-movflags", "+faststart",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0 or not dest.is_file():
        print("[Transcode] ffmpeg fehlgeschlagen:", (result.stderr or "")[-500:])
        if dest.exists():
            dest.unlink()
        return stored_name
    poster = paths.derived / (Path(stored_name).stem + ".jpg")
    poster_cmd = [
        binary, "-y", "-ss", "0.5", "-i", str(dest),
        "-frames:v", "1", str(poster),
    ]
    subprocess.run(poster_cmd, capture_output=True, text=True, timeout=30)
    return dest_name
