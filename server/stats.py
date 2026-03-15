"""
Zentrale Statistik-Sammlung für Admin-Übersicht.
"""
import time

# Server-Startzeit
server_start_time = time.time()

# Wall: Bilder/Videos aktuell angezeigt (vom Wall-Client gemeldet)
wall_stats = {"images": 0, "videos": 0, "updated": 0}

# Upload-Seite: IP -> letzter Heartbeat (Zeitstempel)
upload_page_viewers = {}

# Laufende Uploads
uploads_in_progress = 0

# Heartbeat gültig für 45 Sekunden
VIEWER_TIMEOUT = 45
