"""Laufende Projekte im selben Prozess, ohne Extra-TCP-Ports."""
from __future__ import annotations

import asyncio

from fastapi import HTTPException

from server.project import (
    ProjectPaths,
    clear_active_project,
    set_active_project,
    validate_project_name,
)
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
        self._live: set[str] = set()

    def is_running(self, name: str) -> bool:
        return name in self._live

    def running_names(self) -> list[str]:
        return [name for name in sorted(self._live)]

    def project_for_port(self, port: int | None) -> str | None:
        return None

    def _persist(self) -> None:
        update_runtime(running_projects=self.running_names())

    async def restore(self) -> None:
        from server.project import list_projects
        known = set(list_projects())
        for name in list(load_runtime().get("running_projects") or []):
            if name in known:
                self._live.add(name)
            else:
                print(f"[Projekt] Nach Neustart unbekannt, nicht gestartet: {name}")
        self._persist()

    async def start(self, name: str) -> dict:
        name = validate_project_name(name)
        async with self._lock:
            paths = ProjectPaths(name)
            if not paths.config_file.is_file():
                raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
            self._live.add(name)
            set_active_project(name)
            self._persist()
            print(f"[Projekt] {name} läuft")
            from server.applog import log
            log("INFO", f"Projekt gestartet {name}")
            return {"ok": True, "name": name, "running": True}

    async def stop(self, name: str, persist: bool = True) -> dict:
        name = validate_project_name(name)
        async with self._lock:
            self._live.discard(name)
            clear_active_project(name)
            if persist:
                self._persist()
            print(f"[Projekt] {name} gestoppt")
            from server.applog import log
            log("INFO", f"Projekt gestoppt {name}")
            return {"ok": True, "name": name, "running": False}

    async def stop_all(self) -> None:
        snapshot = self.running_names()
        self._live.clear()
        update_runtime(running_projects=snapshot)


runner = ProjectRunner()
