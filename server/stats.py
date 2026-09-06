"""
Zentrale Statistik-Sammlung für Admin-Übersicht.
"""
import time
from collections import defaultdict

from server.context import get_current_project

# Server-Startzeit
server_start_time = time.time()

# Wall: Bilder/Videos aktuell angezeigt (vom Wall-Client gemeldet)
_wall_stats: dict[str, dict] = defaultdict(lambda: {"images": 0, "videos": 0, "updated": 0})

# Upload-Seite: Projekt -> IP -> letzter Heartbeat
_upload_page_viewers: dict[str, dict[str, float]] = defaultdict(dict)

# Laufende Uploads je Projekt
_uploads_in_progress: dict[str, int] = defaultdict(int)

# Heartbeat gültig für 45 Sekunden
VIEWER_TIMEOUT = 45


def _key(project: str | None = None) -> str:
    return project or get_current_project() or "_"


def wall_stats(project: str | None = None) -> dict:
    return _wall_stats[_key(project)]


def upload_viewers(project: str | None = None) -> dict[str, float]:
    return _upload_page_viewers[_key(project)]


def uploads_in_progress(project: str | None = None) -> int:
    return _uploads_in_progress[_key(project)]


def bump_uploads(delta: int, project: str | None = None) -> None:
    key = _key(project)
    _uploads_in_progress[key] = max(0, _uploads_in_progress[key] + delta)
