"""Login, Logout, Session-Status."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.auth import (
    SETUP_USERNAME,
    clear_login_failures,
    clear_session,
    has_user,
    load_auth,
    login_allowed,
    record_login_failure,
    session_username,
    set_session,
    verify_password,
)

router = APIRouter()


class LoginBody(BaseModel):
    password: str
    username: str | None = None


@router.get("/api/auth/status")
def auth_status(request: Request):
    return {
        "first_run": not has_user(),
        "authenticated": session_username(request) is not None,
        "username": SETUP_USERNAME if has_user() else None,
    }


@router.post("/api/login")
def login(body: LoginBody, request: Request):
    if not has_user():
        raise HTTPException(status_code=409, detail="Erstkonfiguration erforderlich.")
    if not login_allowed(request):
        raise HTTPException(status_code=429, detail="Zu viele Fehlversuche. Später erneut versuchen.")
    auth = load_auth()
    if not auth or not verify_password(body.password, auth["password_hash"]):
        record_login_failure(request)
        raise HTTPException(status_code=401, detail="Anmeldung fehlgeschlagen.")
    clear_login_failures(request)
    response = JSONResponse({"ok": True})
    set_session(response, request)
    return response


@router.post("/api/logout")
def logout():
    response = JSONResponse({"ok": True})
    clear_session(response)
    return response
