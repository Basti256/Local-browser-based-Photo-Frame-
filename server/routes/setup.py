"""Einrichtung: Master-Konto, Projekte, je Projekt Netzwerk und PIN."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from server.auth import SETUP_USERNAME, create_user, has_user, set_session
from server.defaults import NETWORK_MODES, STORAGE_MODES
from server.deps import require_user
from server.network import advertised_base_url, get_network_info, normalize_mode, sanitize_public_host
from server.pin import ensure_project_pin, has_pin, set_pin
from server.project import (
    IMAGE_EXT,
    ProjectPaths,
    apply_imported_config,
    apply_listen_port,
    apply_storage,
    create_project,
    list_projects,
    load_project_config,
    project_listen_port,
    save_project_config,
    used_project_ports,
    validate_project_name,
    write_imported_asset,
)
from server.project_runner import runner
from server.restart import listen_port, restart_fields, schedule_restart
from server.runtime import load_runtime, parse_port, update_runtime
from server.transcode import ffmpeg_bin
from server.version import __version__

router = APIRouter()


class InitBody(BaseModel):
    password: str
    port: int | None = None


class ProjectBody(BaseModel):
    name: str


class RuntimeBody(BaseModel):
    port: int | None = None
    bind_host: str | None = None
    active_project: str | None = None


class ProjectNetworkBody(BaseModel):
    network_mode: str
    public_host: str = ""
    public_https: bool = False


class ProjectPinBody(BaseModel):
    pin: str


class ProjectPortBody(BaseModel):
    port: int


class ProjectStorageBody(BaseModel):
    storage_mode: str
    storage_path: str = ""


def _apply_network(paths: ProjectPaths, mode: str, public_host: str, public_https: bool) -> dict:
    cfg = load_project_config(paths)
    cfg["network_mode"] = normalize_mode(mode)
    cfg["public_host"] = sanitize_public_host(public_host)
    cfg["public_https"] = bool(public_https) if cfg["network_mode"] == "public" else False
    save_project_config(paths, cfg)
    return cfg


@router.get("/api/setup/status")
def setup_status():
    rt = load_runtime()
    return {
        "first_run": not has_user(),
        "has_project": bool(list_projects()),
        "port": rt.get("port", 8000),
    }


@router.post("/api/setup/init")
def setup_init(body: InitBody, request: Request):
    if has_user():
        raise HTTPException(status_code=409, detail="Bereits eingerichtet.")
    port = None
    if body.port is not None:
        try:
            port = parse_port(body.port)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    create_user(body.password)
    old_port = listen_port()
    if port is not None:
        update_runtime(port=port)
    new_port = load_runtime()["port"]
    changed = port is not None and new_port != old_port
    payload = {
        "ok": True,
        "username": SETUP_USERNAME,
        "port": new_port,
        **restart_fields(request, new_port, changed),
    }
    if changed:
        schedule_restart()
    response = JSONResponse(payload)
    set_session(response, request)
    return response


@router.get("/api/setup/state")
def setup_state(_user: str = Depends(require_user)):
    rt = load_runtime()
    names = list_projects()
    projects = []
    for name in names:
        p = ProjectPaths(name)
        cfg = load_project_config(p)
        media_count = 0
        if p.media.is_dir():
            media_count = sum(1 for f in p.media.iterdir() if f.is_file() and f.suffix.lower() != ".txt")
        projects.append({
            "name": name,
            "running": runner.is_running(name),
            "active": runner.is_running(name),
            "media_count": media_count,
            "port": project_listen_port(p, cfg),
            "network_mode": normalize_mode(cfg.get("network_mode")),
            "public_host": sanitize_public_host(cfg.get("public_host") or ""),
            "public_https": bool(cfg.get("public_https")),
            "storage_mode": cfg.get("storage_mode") or "project",
            "storage_path": cfg.get("storage_path") or "",
            "has_pin": has_pin(p),
            "pin": ensure_project_pin(p),
            "base_url": advertised_base_url(cfg, name=name),
        })
    return {
        "version": __version__,
        "username": _user,
        "runtime": rt,
        "running_projects": runner.running_names(),
        "network": get_network_info(),
        "projects": projects,
        "ffmpeg": ffmpeg_bin() is not None,
        "modes": list(NETWORK_MODES),
        "storage_modes": list(STORAGE_MODES),
    }


@router.post("/api/projects")
def api_create_project(body: ProjectBody, _user: str = Depends(require_user)):
    paths = create_project(body.name)
    return {
        "ok": True,
        "name": paths.name,
        "pin": ensure_project_pin(paths),
        "port": project_listen_port(paths),
        "running": False,
    }


@router.post("/api/projects/{name}/start")
async def api_start_project(name: str, _user: str = Depends(require_user)):
    return await runner.start(name)


@router.post("/api/projects/{name}/stop")
async def api_stop_project(name: str, _user: str = Depends(require_user)):
    return await runner.stop(name)


@router.post("/api/projects/{name}/activate")
async def api_activate_project(name: str, _user: str = Depends(require_user)):
    return await runner.start(name)


@router.post("/api/projects/{name}/port")
def api_project_port(name: str, body: ProjectPortBody, _user: str = Depends(require_user)):
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    if runner.is_running(name):
        raise HTTPException(status_code=409, detail="Projekt zuerst stoppen.")
    cfg = apply_listen_port(paths, body.port)
    return {"ok": True, "port": cfg["port"]}


@router.post("/api/projects/{name}/network")
def api_project_network(name: str, body: ProjectNetworkBody, _user: str = Depends(require_user)):
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    cfg = _apply_network(paths, body.network_mode, body.public_host, body.public_https)
    return {
        "ok": True,
        "network_mode": cfg["network_mode"],
        "public_host": cfg["public_host"],
        "public_https": cfg["public_https"],
        "base_url": advertised_base_url(cfg, name=name),
    }


@router.post("/api/projects/{name}/pin")
def api_project_pin(name: str, body: ProjectPinBody, _user: str = Depends(require_user)):
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    set_pin(paths, body.pin)
    return {"ok": True, "has_pin": True, "pin": ensure_project_pin(paths)}


@router.post("/api/projects/{name}/storage")
def api_project_storage(name: str, body: ProjectStorageBody, _user: str = Depends(require_user)):
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    cfg = apply_storage(paths, body.storage_mode, body.storage_path)
    return {
        "ok": True,
        "storage_mode": cfg["storage_mode"],
        "storage_path": cfg.get("storage_path") or "",
        "media_path": str(paths.media),
    }


_IMPORT_MAX = 25 * 1024 * 1024
_ASSET_MAX = 20 * 1024 * 1024


def _zip_prefix(names: list[str]) -> str:
    configs = []
    for raw in names:
        name = raw.replace("\\", "/")
        if name.endswith("/") or name.split("/")[-1] != "config.json":
            continue
        if name.startswith("media/") or "/media/" in name:
            continue
        configs.append(name)
    if not configs:
        raise HTTPException(status_code=400, detail="ZIP enthält keine config.json.")
    cfg = min(configs, key=lambda n: n.count("/"))
    if "/" in cfg:
        return cfg.rsplit("/", 1)[0] + "/"
    return ""


def _parse_project_bundle(data: bytes, filename: str) -> tuple[dict, list[tuple[str, str, bytes]]]:
    fname = (filename or "").lower()
    if fname.endswith(".json"):
        try:
            parsed = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail="JSON ungültig.") from e
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="JSON muss ein Objekt sein.")
        return parsed, []
    bio = io.BytesIO(data)
    if not zipfile.is_zipfile(bio):
        raise HTTPException(status_code=400, detail="Bitte ZIP oder config.json laden.")
    bio.seek(0)
    assets: list[tuple[str, str, bytes]] = []
    with zipfile.ZipFile(bio) as zf:
        names = zf.namelist()
        prefix = _zip_prefix(names)
        cfg_name = prefix + "config.json"
        try:
            raw = zf.read(cfg_name)
        except KeyError as e:
            raise HTTPException(status_code=400, detail="ZIP enthält keine config.json.") from e
        try:
            parsed = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail="config.json ungültig.") from e
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="config.json muss ein Objekt sein.")
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if prefix:
                if not name.startswith(prefix):
                    continue
                rel = name[len(prefix):]
            else:
                rel = name
            parts = rel.split("/")
            if len(parts) != 2 or parts[0] not in ("background", "header"):
                continue
            asset_name = parts[1]
            if asset_name != Path(asset_name).name or asset_name in (".", ".."):
                continue
            if Path(asset_name).suffix.lower() not in IMAGE_EXT:
                continue
            if info.file_size > _ASSET_MAX:
                raise HTTPException(status_code=400, detail="Datei in ZIP zu groß.")
            assets.append((parts[0], asset_name, zf.read(info)))
    return parsed, assets


@router.post("/api/projects/import")
async def api_import_project(
    name: str = Form(...),
    file: UploadFile = File(...),
    _user: str = Depends(require_user),
):
    data = await file.read()
    if len(data) > _IMPORT_MAX:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 25 MB).")
    incoming, assets = _parse_project_bundle(data, file.filename or "")
    paths = create_project(name)
    apply_imported_config(paths, incoming)
    for folder, filename, blob in assets:
        if len(blob) > _ASSET_MAX:
            continue
        write_imported_asset(paths, folder, filename, blob)
    return {
        "ok": True,
        "name": paths.name,
        "pin": ensure_project_pin(paths),
        "port": project_listen_port(paths),
        "running": False,
    }


@router.get("/api/projects/{name}/export")
def api_export_project(name: str, _user: str = Depends(require_user)):
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(paths.config_file, "config.json")
        for folder in ("background", "header"):
            src = paths.background if folder == "background" else paths.header
            if not src.is_dir():
                continue
            for item in sorted(src.iterdir()):
                if not item.is_file():
                    continue
                if item.suffix.lower() not in IMAGE_EXT:
                    continue
                zf.write(item, f"{folder}/{item.name}")
    buf.seek(0)
    filename = f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/runtime")
def api_runtime(
    body: RuntimeBody,
    request: Request,
    _user: str = Depends(require_user),
):
    kwargs = {}
    old_port = listen_port()
    if body.port is not None:
        try:
            kwargs["port"] = parse_port(body.port)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if kwargs["port"] != old_port and kwargs["port"] in used_project_ports():
            raise HTTPException(status_code=409, detail="Port ist einem Projekt zugeordnet.")
    if body.bind_host is not None:
        kwargs["bind_host"] = body.bind_host
    rt = update_runtime(**kwargs) if kwargs else load_runtime()
    new_port = int(rt["port"])
    changed = "port" in kwargs and new_port != old_port
    if changed:
        schedule_restart()
    return {
        "ok": True,
        "runtime": rt,
        "port": new_port,
        **restart_fields(request, new_port, changed),
    }


@router.get("/api/system")
def api_system(_user: str = Depends(require_user)):
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": vm.percent,
        }
    except Exception:
        return {"cpu_percent": None, "ram_percent": None}
