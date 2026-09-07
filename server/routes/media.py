"""Statische Medien aus dem aktiven Projekt. Derived hat Vorrang."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

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
    if filename.lower().endswith(".txt"):
        return Response(status_code=204)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden.")


@router.get("/header/{filename}")
def serve_header(filename: str):
    paths = require_paths()
    path = safe_join(paths.header, filename)
    if path and path.is_file():
        return _file_response(path)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden.")


@router.get("/background/shared/{filename}")
def serve_shared_background(filename: str):
    require_paths()
    from server.catalog import shared_background_path
    path = shared_background_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    return _file_response(path)


@router.get("/background/{filename}")
def serve_background(filename: str):
    paths = require_paths()
    from server.catalog import is_shared_background, shared_background_path
    if is_shared_background(filename):
        path = shared_background_path(filename)
        if path is None:
            raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
        return _file_response(path)
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
