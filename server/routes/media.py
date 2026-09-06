"""Statische Medien aus dem aktiven Projekt. Derived hat Vorrang."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.project import require_paths, safe_join

router = APIRouter()


def _file_response(path) -> FileResponse:
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


@router.get("/media/{filename}")
def serve_media(filename: str):
    paths = require_paths()
    derived = safe_join(paths.derived, filename)
    if derived and derived.is_file():
        return _file_response(derived)
    original = safe_join(paths.media, filename)
    if original and original.is_file():
        return _file_response(original)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden.")


@router.get("/header/{filename}")
def serve_header(filename: str):
    paths = require_paths()
    path = safe_join(paths.header, filename)
    if path and path.is_file():
        return _file_response(path)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden.")


@router.get("/background/{filename}")
def serve_background(filename: str):
    paths = require_paths()
    path = safe_join(paths.background, filename)
    if path and path.is_file():
        return _file_response(path)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden.")


@router.get("/derived/{filename}")
def serve_derived(filename: str):
    paths = require_paths()
    path = safe_join(paths.derived, filename)
    if path and path.is_file():
        return _file_response(path)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
