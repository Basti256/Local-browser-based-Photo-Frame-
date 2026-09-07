"""Auslieferung der HTML-Seiten aus web/."""
from __future__ import annotations

import html as html_lib
import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth import has_user
from server.context import get_url_prefix
from server.deps import html_guard
from server.paths import WEB_DIR
from server.pin import admin_project, clear_admin_session, has_pin
from server.project import (
    get_paths,
    load_project_config,
)
from server.project_runner import runner
from server.routing import STATUS_MISSING, STATUS_STOPPED, empty_not_found, with_prefix
from server.version import __version__

router = APIRouter()
_HEAD_RE = re.compile(r"<head[^>]*>", re.IGNORECASE)


def _page(*parts: str) -> HTMLResponse:
    path = WEB_DIR.joinpath(*parts)
    text = path.read_text(encoding="utf-8")
    prefix = get_url_prefix() or ""
    inject = (
        f'<meta name="pf-base" content="{html_lib.escape(prefix, quote=True)}">'
        f'<script src="/static/js/pf-base.js"></script>'
    )
    text, n = _HEAD_RE.subn(lambda m: m.group(0) + inject, text, count=1)
    if n == 0:
        text = inject + text
    v = html_lib.escape(__version__, quote=True)
    text = text.replace("/static/wall-rotate.js", f"/static/wall-rotate.js?v={v}")
    text = text.replace("/static/wall-rotate.css", f"/static/wall-rotate.css?v={v}")
    return HTMLResponse(
        text,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


def _no_project() -> HTMLResponse:
    return _page("setup", "no-project.html")


def _stopped() -> HTMLResponse:
    return _page("setup", "stopped.html")


def _slug_status(request: Request) -> str | None:
    state = request.scope.get("state") or {}
    return state.get("project_status")


def _on_project_listener(request: Request) -> bool:
    server = request.scope.get("server")
    if not server or len(server) < 2:
        return False
    return runner.project_for_port(server[1]) is not None


@router.get("/")
def root(request: Request):
    if get_url_prefix() or _on_project_listener(request):
        return wall_page(request)
    return RedirectResponse("/setup", status_code=302)


@router.get("/login")
def login_page():
    if not has_user():
        return RedirectResponse("/setup", status_code=302)
    return _page("login", "index.html")


@router.get("/logout")
def logout_page(request: Request):
    response = RedirectResponse("/login", status_code=302)
    from server.auth import clear_session
    clear_session(response)
    return response


@router.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(with_prefix("/admin"), status_code=302)
    clear_admin_session(response)
    return response


@router.get("/setup")
def setup_page(request: Request):
    guard = html_guard(request)
    if guard and has_user():
        return guard
    return _page("setup", "index.html")


@router.get("/admin/classic")
def admin_classic_page(request: Request):
    gated = _project_html_gate(request)
    if gated is not None:
        return gated
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/admin/classic")
    if not has_pin(paths) or admin_project(request) != paths.name:
        return _page("admin", "pin.html")
    config = load_project_config(paths)
    if config.get("wall_view_mode") == "grid":
        return _page("admin", "grid-classic.html")
    return _page("admin", "fly-classic.html")


@router.get("/admin")
def admin_page(request: Request):
    gated = _project_html_gate(request)
    if gated is not None:
        return gated
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/admin")
    if not has_pin(paths) or admin_project(request) != paths.name:
        return _page("admin", "pin.html")
    return _page("admin", "fly.html")


@router.get("/admin/browser")
def admin_browser_page(request: Request):
    gated = _project_html_gate(request)
    if gated is not None:
        return gated
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/admin/browser")
    if not has_pin(paths) or admin_project(request) != paths.name:
        return _page("admin", "pin.html")
    return _page("admin", "browser.html")


def _project_html_gate(request: Request):
    status = _slug_status(request)
    if status == STATUS_MISSING:
        return empty_not_found()
    if status == STATUS_STOPPED:
        return _stopped()
    return None


def _request_hosts(request: Request | None) -> list[str]:
    from server.network import collect_request_hosts
    if request is None:
        return []
    return collect_request_hosts(
        host=request.headers.get("host") or "",
        forwarded_host=request.headers.get("x-forwarded-host") or "",
        forwarded=request.headers.get("forwarded") or "",
    )


def _redirect_single_or_none(request: Request, dest: str):
    from server.network import normalize_mode, request_is_lan
    from server.project import ProjectPaths, load_project_config
    lan = request_is_lan(_request_hosts(request))
    running = []
    for name in runner.running_names():
        mode = normalize_mode(load_project_config(ProjectPaths(name)).get("network_mode"))
        if not lan and mode != "public":
            continue
        running.append(name)
    if len(running) == 1:
        return RedirectResponse(f"/{running[0]}{dest}", status_code=302)
    return _no_project()


def _legacy_project_redirect(name: str, dest: str, request: Request | None = None):
    from server.network import normalize_mode, request_is_lan
    from server.project import ProjectPaths, find_project_by_slug, load_project_config
    found = find_project_by_slug(name)
    if not found:
        return empty_not_found()
    name = found
    cfg = load_project_config(ProjectPaths(name))
    if normalize_mode(cfg.get("network_mode")) != "public" and not request_is_lan(_request_hosts(request)):
        return empty_not_found()
    if not runner.is_running(name):
        return _stopped()
    if dest == "/":
        dest = "/wall"
    return RedirectResponse(f"/{name}{dest}", status_code=302)


@router.get("/p/{name}/wall")
def project_wall(name: str, request: Request):
    return _legacy_project_redirect(name, "/wall", request)


@router.get("/p/{name}/upload")
def project_upload(name: str, request: Request):
    return _legacy_project_redirect(name, "/upload", request)


@router.get("/p/{name}/admin")
def project_admin(name: str, request: Request):
    return _legacy_project_redirect(name, "/admin", request)


@router.get("/p/{name}/browser")
def project_browser(name: str, request: Request):
    return _legacy_project_redirect(name, "/admin/browser", request)


@router.get("/p/{name}")
def project_legacy_root(name: str, request: Request):
    return _legacy_project_redirect(name, "/wall", request)


@router.get("/p/{name}/{rest:path}")
def project_legacy_rest(name: str, rest: str, request: Request):
    dest = "/" + rest.lstrip("/") if rest else "/wall"
    if dest == "/browser" or dest.startswith("/browser/"):
        dest = "/admin" + dest[len("/browser"):] if dest != "/browser" else "/admin/browser"
        if dest == "/admin":
            dest = "/admin/browser"
    return _legacy_project_redirect(name, dest, request)


@router.get("/wall")
def wall_page(request: Request):
    gated = _project_html_gate(request)
    if gated is not None:
        return gated
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/wall")
    if get_url_prefix() and not runner.is_running(paths.name):
        return _stopped()
    config = load_project_config(paths)
    if config.get("wall_view_mode") == "grid":
        return _page("wall", "grid.html")
    return _page("wall", "fly.html")


@router.get("/wall/grid")
def wall_grid_page(request: Request):
    gated = _project_html_gate(request)
    if gated is not None:
        return gated
    if get_paths() is None:
        return _redirect_single_or_none(request, "/wall/grid")
    return _page("wall", "grid.html")


@router.get("/upload")
def upload_page(request: Request):
    gated = _project_html_gate(request)
    if gated is not None:
        return gated
    if get_paths() is None:
        return _redirect_single_or_none(request, "/upload")
    if get_url_prefix() and not runner.is_running(get_paths().name):
        return _stopped()
    return _page("upload", "index.html")
