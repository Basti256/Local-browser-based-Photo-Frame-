"""Wall: WebSocket, öffentliche Config- und Medienliste."""
from __future__ import annotations

import json
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, WebSocket

from server import stats
from server.context import get_current_project, reset_current_project, set_current_project, set_url_prefix
from server.deps import require_admin_pin
from server.network import get_upload_url
from server.project import (
    DISPLAY_IMAGE_EXT,
    DISPLAY_VIDEO_EXT,
    VIDEO_EXT,
    get_paths,
    load_project_config,
    merge_project_config,
)
from server.hidden import load_hidden
from server.project_runner import runner
from server.transcode import display_name_for

router = APIRouter()
clients: dict[str, list[WebSocket]] = defaultdict(list)


async def broadcast(filename: str, project: str | None = None) -> None:
    name = project or get_current_project()
    if not name:
        return
    dead = []
    for ws in clients[name]:
        try:
            await ws.send_text(filename)
        except Exception:
            dead.append(ws)
    for d in dead:
        if d in clients[name]:
            clients[name].remove(d)


HIDE_PREFIX = "__hide__:"


async def broadcast_hide(display_name: str, project: str | None = None) -> None:
    if display_name:
        await broadcast(HIDE_PREFIX + display_name, project=project)


async def broadcast_config(reload_full: bool = False, project: str | None = None) -> None:
    msg = "__config_reload__" if reload_full else "__config_updated__"
    await broadcast(msg, project=project)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    server = websocket.scope.get("server")
    port = server[1] if server and len(server) >= 2 else None
    state = websocket.scope.get("state") or {}
    name = state.get("project_name") if isinstance(state, dict) else getattr(state, "project_name", None)
    if not name:
        name = runner.project_for_port(port)
    status = state.get("project_status") if isinstance(state, dict) else getattr(state, "project_status", None)
    prefix = (state.get("url_prefix") if isinstance(state, dict) else getattr(state, "url_prefix", None)) or ""
    if not name or status in ("stopped", "missing"):
        await websocket.close(code=1008)
        return
    if prefix and not runner.is_running(name):
        await websocket.close(code=1008)
        return
    token = set_current_project(name)
    prefix_token = set_url_prefix(prefix)
    await websocket.accept()
    clients[name].append(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "stats":
                    st = stats.wall_stats(name)
                    st["images"] = data.get("images", 0)
                    st["videos"] = data.get("videos", 0)
                    st["updated"] = time.time()
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception:
        if websocket in clients[name]:
            clients[name].remove(websocket)
    finally:
        from server.context import reset_url_prefix
        reset_url_prefix(prefix_token)
        reset_current_project(token)


@router.get("/api/upload_url")
def upload_url():
    return {"url": get_upload_url()}


@router.get("/api/images")
def list_images():
    paths = get_paths()
    if paths is None or not paths.media.is_dir():
        return []
    hidden = load_hidden(paths)
    names = []
    seen = set()
    for f in sorted(paths.media.iterdir()):
        if not f.is_file():
            continue
        if f.name in hidden:
            continue
        ext = f.suffix.lower()
        if ext not in DISPLAY_IMAGE_EXT and ext not in DISPLAY_VIDEO_EXT and ext not in VIDEO_EXT:
            continue
        display = display_name_for(f.name, paths.derived)
        if display in seen:
            continue
        seen.add(display)
        names.append(display)
    return names


@router.get("/api/config")
def get_config():
    paths = get_paths()
    if paths is None:
        from server.defaults import DEFAULT_CONFIG
        cfg = DEFAULT_CONFIG.copy()
    else:
        cfg = load_project_config(paths)
    public = dict(cfg)
    public.pop("storage_path", None)
    return public


@router.post("/api/config")
async def save_config(config: dict, _project: str = Depends(require_admin_pin)):
    merged, view_changed = merge_project_config(config)
    await broadcast_config(reload_full=view_changed)
    return {"status": "saved", "view_changed": view_changed}
