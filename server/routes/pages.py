"""Auslieferung der HTML-Seiten aus web/."""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from server.auth import has_user
from server.deps import html_guard
from server.network import lan_origin
from server.paths import WEB_DIR
from server.pin import admin_project, clear_admin_session, has_pin
from server.project import (
    ProjectPaths,
    get_paths,
    load_project_config,
    project_listen_port,
    validate_project_name,
)
from server.project_runner import runner

router = APIRouter()


def _page(*parts: str) -> FileResponse:
    path = WEB_DIR.joinpath(*parts)
    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


def _no_project() -> FileResponse:
    return _page("setup", "no-project.html")


def _stopped() -> FileResponse:
    return _page("setup", "stopped.html")


def _project_origin(request: Request, name: str) -> str:
    paths = ProjectPaths(name)
    return lan_origin(request, project_listen_port(paths))


@router.get("/")
def root(request: Request):
    return wall_page(request)


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
    response = RedirectResponse("/admin", status_code=302)
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
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/admin")
    if not has_pin(paths) or admin_project(request) != paths.name:
        return _page("admin", "pin.html")
    return _page("admin", "fly.html")


@router.get("/admin/browser")
def admin_browser_page(request: Request):
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/admin/browser")
    if not has_pin(paths) or admin_project(request) != paths.name:
        return _page("admin", "pin.html")
    return _page("admin", "browser.html")


def _redirect_single_or_none(request: Request, dest: str):
    running = runner.running_names()
    if len(running) == 1:
        return RedirectResponse(_project_origin(request, running[0]) + dest, status_code=302)
    return _no_project()


def _open_project(request: Request, name: str, dest: str):
    name = validate_project_name(name)
    paths = ProjectPaths(name)
    if not paths.config_file.is_file():
        return _no_project()
    if not runner.is_running(name):
        return _stopped()
    return RedirectResponse(_project_origin(request, name) + dest, status_code=302)


@router.get("/p/{name}/wall")
def project_wall(name: str, request: Request):
    return _open_project(request, name, "/wall")


@router.get("/p/{name}/upload")
def project_upload(name: str, request: Request):
    return _open_project(request, name, "/upload")


@router.get("/p/{name}/admin")
def project_admin(name: str, request: Request):
    return _open_project(request, name, "/admin")


@router.get("/p/{name}/browser")
def project_browser(name: str, request: Request):
    return _open_project(request, name, "/admin/browser")


@router.get("/wall")
def wall_page(request: Request):
    paths = get_paths()
    if paths is None:
        return _redirect_single_or_none(request, "/wall")
    config = load_project_config(paths)
    if config.get("wall_view_mode") == "grid":
        return _page("wall", "grid.html")
    return _page("wall", "fly.html")


@router.get("/wall/grid")
def wall_grid_page(request: Request):
    if get_paths() is None:
        return _redirect_single_or_none(request, "/wall/grid")
    return _page("wall", "grid.html")


@router.get("/upload")
def upload_page(request: Request):
    if get_paths() is None:
        return _redirect_single_or_none(request, "/upload")
    return _page("upload", "index.html")
