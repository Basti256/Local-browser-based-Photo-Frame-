"""Serverseitiges Transcoding. Originale bleiben erhalten."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from server.project import IMAGE_EXT, VIDEO_EXT, ProjectPaths

IMAGE_OUT_EXT = ".jpg"


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def ffprobe_bin() -> str | None:
    return shutil.which("ffprobe")


def probe_media(path: Path) -> dict:
    """Breite, Höhe, Dauer, Codec. Ohne ffprobe nur Bildgröße via Pillow."""
    info: dict = {"width": 0, "height": 0, "duration_sec": 0.0, "codec": "", "ok": False}
    probe = ffprobe_bin()
    if probe and path.is_file():
        try:
            result = subprocess.run(
                [probe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            data = json.loads(result.stdout or "{}")
            streams = data.get("streams") or []
            video = next((s for s in streams if s.get("codec_type") == "video"), None)
            if video:
                info["width"] = int(video.get("width") or 0)
                info["height"] = int(video.get("height") or 0)
                info["codec"] = str(video.get("codec_name") or "")
            dur = 0.0
            try:
                dur = float((data.get("format") or {}).get("duration") or 0)
            except (TypeError, ValueError):
                dur = 0.0
            if dur <= 0 and video:
                try:
                    dur = float(video.get("duration") or 0)
                except (TypeError, ValueError):
                    dur = 0.0
            info["duration_sec"] = max(0.0, dur)
            info["ok"] = info["width"] > 0 or info["height"] > 0 or dur > 0
            return info
        except Exception:
            pass
    if path.suffix.lower() in IMAGE_EXT | {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        try:
            with Image.open(path) as img:
                img = ImageOps.exif_transpose(img)
                info["width"], info["height"] = img.size
                info["codec"] = (img.format or "").lower()
                info["ok"] = True
        except Exception:
            pass
    return info


def recommend_program_transcode(path: Path, media_type: str, probe: dict | None = None) -> bool:
    """True wenn 720p-H.264/JPEG sinnvoller ist als das Original."""
    probe = probe or probe_media(path)
    h = int(probe.get("height") or 0)
    w = int(probe.get("width") or 0)
    codec = str(probe.get("codec") or "").lower()
    if media_type == "image":
        return h > 720 or w > 1280 or path.suffix.lower() not in {".jpg", ".jpeg"}
    if codec and codec not in {"h264", "avc1"}:
        return True
    if path.suffix.lower() != ".mp4":
        return True
    return h > 720


def transcode_program_image(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((1280, 720))
        img.save(dest, "JPEG", quality=85, optimize=True)
    return dest.is_file()


def transcode_program_video(src: Path, dest: Path) -> bool:
    binary = ffmpeg_bin()
    if not binary:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary, "-y", "-i", str(src),
        "-vf", r"scale=-2:min(720\,ih),scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ac", "2", "-b:a", "128k",
        "-movflags", "+faststart",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0 or not dest.is_file():
        print("[Wall Manager] ffmpeg fehlgeschlagen:", (result.stderr or "")[-500:])
        if dest.exists():
            dest.unlink()
        return False
    return True


def make_program_thumb(src: Path, dest: Path, media_type: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if media_type == "image":
            with Image.open(src) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                resample = getattr(Image, "Resampling", Image).LANCZOS
                img.thumbnail((200, 200), resample)
                canvas = Image.new("RGB", (200, 200), (17, 17, 17))
                canvas.paste(img, ((200 - img.width) // 2, (200 - img.height) // 2))
                canvas.save(dest, "JPEG", quality=80, optimize=True)
            return dest.is_file()
        binary = ffmpeg_bin()
        if not binary:
            return False
        cmd = [
            binary, "-y", "-ss", "0.5", "-i", str(src),
            "-vf", "scale=200:200:force_original_aspect_ratio=decrease,pad=200:200:(ow-iw)/2:(oh-ih)/2:black",
            "-frames:v", "1",
            str(dest),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0 or not dest.is_file():
            cmd[cmd.index("-ss") + 1] = "0"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0 and dest.is_file()
    except Exception as exc:
        print("[Wall Manager] Thumb:", exc)
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        return False


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
