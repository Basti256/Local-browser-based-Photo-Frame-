"""FastAPI-Abhängigkeiten für Setup-Session, Admin-PIN und CSRF."""
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from server.auth import has_user, same_origin, session_username
from server.pin import require_pin_session
from server.project import get_paths


def require_user(request: Request) -> str:
    if not has_user():
        raise HTTPException(status_code=409, detail="Erstkonfiguration erforderlich.")
    name = session_username(request)
    if not name:
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich.")
    if request.method not in ("GET", "HEAD", "OPTIONS") and not same_origin(request):
        raise HTTPException(status_code=403, detail="Ungültige Herkunft.")
    return name


def require_admin_pin(request: Request) -> str:
    paths = get_paths()
    if paths is None:
        raise HTTPException(status_code=409, detail="Kein laufendes Projekt.")
    require_pin_session(request, paths.name)
    return paths.name


def html_guard(request: Request) -> RedirectResponse | None:
    """Nur für /setup."""
    if not has_user():
        if request.url.path.rstrip("/") in ("/setup", "/login"):
            return None
        return RedirectResponse("/setup", status_code=302)
    if session_username(request):
        return None
    nxt = request.url.path
    return RedirectResponse(f"/login?next={nxt}", status_code=302)
