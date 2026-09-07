"""Projekt-Pfade am Serverport: /{slug}/wall ohne extra TCP-Ports."""
from __future__ import annotations

from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send

from server.context import reset_current_project, reset_url_prefix, set_current_project, set_url_prefix
from server.project import PROJECT_NAME_RE, find_project_by_slug
from server.project_runner import is_control_only, runner
from server.restart import setup_url_for_port
from server.slugs import is_reserved_segment

STATUS_OK = "ok"
STATUS_STOPPED = "stopped"
STATUS_MISSING = "missing"


@dataclass(frozen=True)
class PrefixResult:
    path: str
    project: str | None
    prefix: str
    status: str | None
    redirect: str | None = None


def split_segment(path: str) -> tuple[str, str]:
    raw = path.split("?", 1)[0] or "/"
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw == "/":
        return "", "/"
    parts = raw.lstrip("/").split("/", 1)
    first = parts[0]
    remainder = "/" + parts[1] if len(parts) > 1 else "/"
    return first, remainder


def _scope_host(scope: Scope) -> str:
    headers = scope.get("headers") or []
    forwarded = ""
    host = ""
    for key, value in headers:
        name = key.decode("latin-1").lower() if isinstance(key, (bytes, bytearray)) else str(key).lower()
        text = value.decode("latin-1") if isinstance(value, (bytes, bytearray)) else str(value)
        if name == "x-forwarded-host" and not forwarded:
            forwarded = text.split(",")[0].strip()
        elif name == "host" and not host:
            host = text.split(",")[0].strip()
    return forwarded or host


def resolve_control_path(path: str, running: set[str] | None = None, http_host: str = "") -> PrefixResult:
    first, remainder = split_segment(path)
    if not first or is_reserved_segment(first):
        return PrefixResult(path=path, project=None, prefix="", status=None)
    name = find_project_by_slug(first)
    if name is None:
        if PROJECT_NAME_RE.match(first):
            prefix = "/" + first
            return PrefixResult(
                path=remainder,
                project=None,
                prefix=prefix,
                status=STATUS_MISSING,
            )
        return PrefixResult(path=path, project=None, prefix="", status=None)
    from server.network import is_public_http_host, normalize_mode
    from server.project import ProjectPaths, load_project_config
    cfg = load_project_config(ProjectPaths(name))
    if normalize_mode(cfg.get("network_mode")) != "public" and is_public_http_host(http_host):
        return PrefixResult(path=path, project=None, prefix="", status=None)
    prefix = "/" + name
    redirect = None
    if first != name:
        q = ""
        if "?" in path:
            q = "?" + path.split("?", 1)[1]
        dest = prefix if remainder == "/" else prefix + remainder
        redirect = dest + q
    if running is not None:
        live = name in running
    else:
        live = runner.is_running(name)
    status = STATUS_OK if live else STATUS_STOPPED
    return PrefixResult(
        path=remainder,
        project=name,
        prefix=prefix,
        status=status,
        redirect=redirect,
    )


def with_prefix(path: str) -> str:
    prefix = ""
    try:
        from server.context import get_url_prefix
        prefix = get_url_prefix() or ""
    except Exception:
        prefix = ""
    if not path.startswith("/"):
        path = "/" + path
    return prefix + path


def _scope_port(scope: Scope) -> int | None:
    server = scope.get("server")
    if server and len(server) >= 2 and server[1] is not None:
        try:
            return int(server[1])
        except (TypeError, ValueError):
            return None
    return None


def bind_project_scope(scope: Scope) -> Scope:
    scope = dict(scope)
    state = dict(scope.get("state") or {})
    path = scope.get("path") or "/"
    port = _scope_port(scope)
    port_project = runner.project_for_port(port) if port is not None else None
    state["log_path"] = path
    if port_project:
        state["project_name"] = port_project
        state["url_prefix"] = ""
        state["project_status"] = STATUS_OK
        state["redirect"] = None
        scope["state"] = state
        return scope
    result = resolve_control_path(path, http_host=_scope_host(scope))
    if result.redirect:
        state["redirect"] = result.redirect
        state["project_name"] = result.project
        state["url_prefix"] = result.prefix
        state["project_status"] = result.status
        scope["state"] = state
        return scope
    if result.prefix:
        scope["path"] = result.path
        scope["raw_path"] = result.path.encode("ascii", "ignore")
    state["project_name"] = result.project
    state["url_prefix"] = result.prefix
    state["project_status"] = result.status
    state["redirect"] = None
    scope["state"] = state
    return scope


async def _send_redirect(send: Send, location: str) -> None:
    await send({
        "type": "http.response.start",
        "status": 302,
        "headers": [
            (b"location", location.encode("ascii", "ignore")),
            (b"cache-control", b"no-store"),
        ],
    })
    await send({"type": "http.response.body", "body": b""})


class ProjectPrefixASGI:
    """Schreibt /{slug}/… am Serverport auf die bestehenden Routen um."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            scope = bind_project_scope(scope)
            redirect = (scope.get("state") or {}).get("redirect")
            if redirect and scope["type"] == "http" and scope.get("method") in ("GET", "HEAD"):
                await _send_redirect(send, redirect)
                return
        await self.app(scope, receive, send)


def state_value(scope: Scope, key: str, default=None):
    state = scope.get("state")
    if state is None:
        return default
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def attach_request_context(scope: Scope):
    name = state_value(scope, "project_name")
    prefix = state_value(scope, "url_prefix") or ""
    t_proj = set_current_project(name)
    t_pref = set_url_prefix(prefix)
    return t_proj, t_pref


def reset_request_context(t_proj, t_pref) -> None:
    reset_url_prefix(t_pref)
    reset_current_project(t_proj)


def control_only_blocked(scope: Scope, path: str) -> bool:
    port_name = runner.project_for_port(_scope_port(scope))
    return bool(port_name and is_control_only(path))


def setup_redirect_response(request, send_status: int = 302):
    from fastapi.responses import JSONResponse, RedirectResponse
    from server.restart import listen_port
    path = request.url.path
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Nur auf dem Serverport."}, status_code=404)
    return RedirectResponse(setup_url_for_port(request, listen_port()), status_code=send_status)
