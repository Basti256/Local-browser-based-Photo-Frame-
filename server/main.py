"""FastAPI-Einstieg. Kein Projekt zwingend beim Import."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.context import reset_current_project, set_current_project
from server.firewall import close_firewall_port, open_firewall_port
from server.paths import WEB_DIR, ensure_data_dir
from server.project_runner import is_control_only, runner
from server.restart import listen_port, setup_url_for_port
from server.runtime import load_runtime
from server.service_worker import service_worker_response
from server.version import __version__


def _scope_port(scope: dict) -> int | None:
    server = scope.get("server")
    if server and len(server) >= 2 and server[1] is not None:
        try:
            return int(server[1])
        except (TypeError, ValueError):
            return None
    return None


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
    yield
    await runner.stop_all()
    try:
        close_firewall_port(port)
    except Exception as e:
        print("Firewall konnte nicht geschlossen werden:", e)


app = FastAPI(title="Local-browser-based-Photo-Frame", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def bind_project_port(request: Request, call_next):
    name = runner.project_for_port(_scope_port(request.scope))
    token = set_current_project(name)
    try:
        if name and is_control_only(request.url.path):
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "Nur auf dem Einrichtungs-Port."}, status_code=404)
            return RedirectResponse(setup_url_for_port(request, listen_port()), status_code=302)
        return await call_next(request)
    finally:
        reset_current_project(token)


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_config():
    return {}


@app.get("/api/version")
def api_version():
    return {"version": __version__, "name": "Local-browser-based-Photo-Frame"}


@app.get("/sw.js")
def service_worker():
    return service_worker_response()


from server.routes import admin, auth_routes, media, pages, setup, upload, wall

app.include_router(auth_routes.router)
app.include_router(setup.router)
app.include_router(pages.router)
app.include_router(upload.router)
app.include_router(wall.router)
app.include_router(admin.router)
app.include_router(media.router)
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
