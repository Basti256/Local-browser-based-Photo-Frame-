"""Zusätzliche Listen-Ports für laufende Projekte im selben Prozess."""
from __future__ import annotations

import asyncio

import uvicorn
from fastapi import HTTPException

from server.firewall import close_firewall_port, open_firewall_port
from server.project import (
    ProjectPaths,
    clear_active_project,
    port_in_use,
    project_listen_port,
    set_active_project,
    validate_project_name,
)
from server.restart import listen_host, listen_port
from server.runtime import load_runtime, update_runtime

CONTROL_ONLY_PREFIXES = (
    "/setup",
    "/login",
    "/logout",
    "/api/setup",
    "/api/projects",
    "/api/runtime",
    "/api/system",
    "/api/login",
    "/api/logout",
    "/api/auth",
)


def is_control_only(path: str) -> bool:
    p = path.rstrip("/") or "/"
    return any(p == prefix or p.startswith(prefix + "/") for prefix in CONTROL_ONLY_PREFIXES)


class ProjectRunner:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._live: dict[str, tuple[uvicorn.Server, asyncio.Task, int]] = {}

    def is_running(self, name: str) -> bool:
        entry = self._live.get(name)
        if not entry:
            return False
        server, task, _port = entry
        return bool(server.started) and not task.done()

    def running_names(self) -> list[str]:
        return [name for name in self._live if self.is_running(name)]

    def project_for_port(self, port: int | None) -> str | None:
        if port is None:
            return None
        control = listen_port()
        if port == control:
            return None
        for name, (server, task, listen) in self._live.items():
            if listen == port and server.started and not task.done():
                return name
        return None

    def _persist(self) -> None:
        update_runtime(running_projects=self.running_names())

    async def restore(self) -> None:
        names = list(load_runtime().get("running_projects") or [])
        for name in names:
            try:
                await self.start(name)
            except HTTPException as e:
                print(f"[Projekt] Start nach Neustart fehlgeschlagen ({name}): {e.detail}")
            except Exception as e:
                print(f"[Projekt] Start nach Neustart fehlgeschlagen ({name}): {e}")
        self._persist()

    async def start(self, name: str) -> dict:
        name = validate_project_name(name)
        async with self._lock:
            if self.is_running(name):
                paths = ProjectPaths(name)
                return {"ok": True, "name": name, "port": project_listen_port(paths), "running": True}
            paths = ProjectPaths(name)
            if not paths.config_file.is_file():
                raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
            port = project_listen_port(paths)
            if port == listen_port():
                raise HTTPException(
                    status_code=409,
                    detail="Projekt-Port ist der Einrichtungs-Port. Anderen Port setzen.",
                )
            for other, (_server, _task, other_port) in self._live.items():
                if other_port == port and self.is_running(other):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Port {port} wird von Projekt {other} genutzt.",
                    )
            if port_in_use(port):
                raise HTTPException(
                    status_code=409,
                    detail=f"Port {port} ist belegt.",
                )
            host = listen_host() or "0.0.0.0"
            from server.main import app as asgi_app
            config = uvicorn.Config(
                asgi_app,
                host=host,
                port=port,
                lifespan="off",
                log_level="info",
            )
            server = uvicorn.Server(config)
            server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
            task = asyncio.create_task(server.serve(), name=f"pf-project-{name}")
            self._live[name] = (server, task, port)
            started = False
            for _ in range(80):
                if task.done():
                    self._live.pop(name, None)
                    err = task.exception() if not task.cancelled() else None
                    raise HTTPException(
                        status_code=500,
                        detail=f"Projekt-Listener beendet sich: {err or 'unbekannt'}",
                    )
                if server.started:
                    started = True
                    break
                await asyncio.sleep(0.05)
            if not started:
                server.should_exit = True
                task.cancel()
                self._live.pop(name, None)
                raise HTTPException(status_code=500, detail="Projekt-Port startete nicht.")
            try:
                open_firewall_port(port)
            except Exception as e:
                print("Firewall konnte nicht geöffnet werden:", e)
            set_active_project(name)
            self._persist()
            print(f"[Projekt] {name} läuft auf Port {port}")
            from server.applog import log
            log("INFO", f"Projekt gestartet {name} Port {port}")
            return {"ok": True, "name": name, "port": port, "running": True}

    async def stop(self, name: str, persist: bool = True) -> dict:
        name = validate_project_name(name)
        async with self._lock:
            entry = self._live.pop(name, None)
            if entry:
                server, task, port = entry
                server.should_exit = True
                server.force_exit = True
                try:
                    await asyncio.wait_for(task, timeout=4)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
                except Exception:
                    pass
                try:
                    close_firewall_port(port)
                except Exception as e:
                    print("Firewall konnte nicht geschlossen werden:", e)
                print(f"[Projekt] {name} gestoppt (Port {port})")
                from server.applog import log
                log("INFO", f"Projekt gestoppt {name} Port {port}")
            clear_active_project(name)
            if persist:
                self._persist()
            return {"ok": True, "name": name, "running": False}

    async def stop_all(self) -> None:
        snapshot = self.running_names()
        names = list(self._live)
        for name in names:
            try:
                await self.stop(name, persist=False)
            except Exception as e:
                print(f"[Projekt] Stop fehlgeschlagen ({name}): {e}")
        update_runtime(running_projects=snapshot)


runner = ProjectRunner()
