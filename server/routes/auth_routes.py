"""Login, Logout, Session-Status."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.auth import (
    SETUP_USERNAME,
    clear_session,
    has_user,
    load_auth,
    session_username,
    set_session,
    verify_password,
)
from server.lockout import clear_failures, record_failure, refuse_if_locked, status as lock_status
from server.applog import log

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
        "login_lock": lock_status("setup", "/login"),
    }


@router.post("/api/login")
def login(body: LoginBody, request: Request):
    if not has_user():
        raise HTTPException(status_code=409, detail="Erstkonfiguration erforderlich.")
    refuse_if_locked("setup", "/login")
    auth = load_auth()
    if not auth or not verify_password(body.password, auth["password_hash"]):
        wait = record_failure("setup")
        log("WARNING", "Setup-Login fehlgeschlagen")
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Anmeldung fehlgeschlagen.",
                "wait_seconds": wait,
                "path": "/login",
            },
        )
    clear_failures("setup")
    log("INFO", "Setup-Login erfolgreich")
    response = JSONResponse({"ok": True})
    set_session(response, request)
    return response


@router.post("/api/logout")
def logout():
    response = JSONResponse({"ok": True})
    clear_session(response)
    return response
