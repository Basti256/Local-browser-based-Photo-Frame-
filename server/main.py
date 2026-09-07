"""FastAPI-Einstieg. Kein Projekt zwingend beim Import."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.firewall import close_firewall_port, open_firewall_port
from server.paths import WEB_DIR, ensure_data_dir
from server.project_runner import runner
from server.routing import (
    ProjectPrefixASGI,
    attach_request_context,
    control_only_blocked,
    empty_not_found,
    reset_request_context,
    setup_redirect_response,
)
from server.runtime import load_runtime
from server.service_worker import service_worker_response
from server.version import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dir()
    rt = load_runtime()
    port = int(rt.get("port", 8000))
    bind = rt.get("bind_host") or "0.0.0.0"
    print(f"[Runtime] bind={bind} port={port}")
    try:
        open_firewall_port(port)
    except Exception as e:
        print("Firewall konnte nicht geöffnet werden:", e)
    await runner.restore()
    print(f"[Runtime] running={runner.running_names() or '-'}")
    from server.applog import log
    log("INFO", f"Server gestartet bind={bind} port={port}")
    yield
    await runner.stop_all()
    try:
        close_firewall_port(port)
    except Exception as e:
        print("Firewall konnte nicht geschlossen werden:", e)


fastapi_app = FastAPI(
    title="Local-browser-based-Photo-Frame",
    version=__version__,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@fastapi_app.exception_handler(StarletteHTTPException)
async def silent_unmatched_404(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and exc.detail == "Not Found":
        return empty_not_found()
    return await http_exception_handler(request, exc)


@fastapi_app.middleware("http")
async def bind_project_port(request: Request, call_next):
    t_proj, t_pref = attach_request_context(request.scope)
    try:
        if control_only_blocked(request.scope, request.url.path):
            return setup_redirect_response(request)
        response = await call_next(request)
        try:
            from server.applog import log_request
            log_path = (request.scope.get("state") or {}).get("log_path") or request.url.path
            log_request(request.method, log_path, response.status_code)
        except Exception:
            pass
        return response
    finally:
        reset_request_context(t_proj, t_pref)


@fastapi_app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_config():
    return {}


@fastapi_app.get("/api/version")
def api_version():
    return {"version": __version__, "name": "Local-browser-based-Photo-Frame"}


@fastapi_app.get("/sw.js")
def service_worker():
    return service_worker_response()


from server.routes import admin, auth_routes, media, pages, setup, upload, wall

fastapi_app.include_router(auth_routes.router)
fastapi_app.include_router(setup.router)
fastapi_app.include_router(pages.router)
fastapi_app.include_router(upload.router)
fastapi_app.include_router(wall.router)
fastapi_app.include_router(admin.router)
fastapi_app.include_router(media.router)
fastapi_app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

app = ProjectPrefixASGI(fastapi_app)
