"""
Local-browser-based-Photo-Frame – Hauptmodul (FastAPI-App).

Dieses Modul ist der Einstiegspunkt der Anwendung. Es:
- Bestimmt das aktive Projekt (via --project= oder PROJECT_NAME)
- Lädt und validiert die config.json (inkl. Migrationen)
- Registriert alle Router (wall, admin, upload)
- Stellt den Service Worker für den Media-Cache bereit
- Öffnet/schließt die Firewall und startet/stoppt den Cloudflare-Tunnel
"""
import os
import sys
import json
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from server.firewall import open_firewall_port, close_firewall_port
from server.version import __version__

# ------------------------------------------------
# Projekt bestimmen (CLI oder Umgebungsvariable)
# ------------------------------------------------

PROJECT_NAME = None

# 1️⃣ CLI Parameter prüfen
for arg in sys.argv:
    if arg.startswith("--project="):
        PROJECT_NAME = arg.split("=")[1]

# 2️⃣ Environment Variable prüfen
if PROJECT_NAME is None:
    PROJECT_NAME = os.getenv("PROJECT_NAME")

# 3️⃣ Fehler wenn nichts gesetzt
if not PROJECT_NAME:

    print("\nERROR: No project specified.\n")
    print("Start the server with:")
    print("uvicorn server.main:app --port 8000 --project=<project_name>")
    print("or set environment variable PROJECT_NAME\n")

    sys.exit(1)

print(f"\nStarting project: {PROJECT_NAME}")

# ------------------------------------------------
# Projektpfade
# ------------------------------------------------
# BASE_DIR: Projektstamm (übergeordnetes Verzeichnis von server/)
# PROJECT_DIR: projects/<projektname>/
# MEDIA_DIR: Hochgeladene Bilder/Videos
# HEADER_DIR: Header-Bild für Upload-Seite
# BACKGROUND_DIR: Hintergrundbilder für die Wall
# CONFIG_FILE: config.json des Projekts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_DIR = os.path.join(BASE_DIR, "projects", PROJECT_NAME)
MEDIA_DIR = os.path.join(PROJECT_DIR, "media")
HEADER_DIR = os.path.join(PROJECT_DIR, "header")
BACKGROUND_DIR = os.path.join(PROJECT_DIR, "background")
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(HEADER_DIR, exist_ok=True)
os.makedirs(BACKGROUND_DIR, exist_ok=True)

# ------------------------------------------------
# Default Config
# ------------------------------------------------

DEFAULT_CONFIG = {

    # Ansicht (fly = Bilder fliegen, grid = Grid nebeneinander)
    "wall_view_mode": "fly",

    # Grid-Ansicht Einstellungen (nur bei wall_view_mode="grid")
    "grid_columns": 4,
    "grid_animation_duration": 8,
    "grid_show_frames": True,
    "grid_spacing_rows": 0,
    "grid_spacing_columns": 20,

    # Netzwerk
    "network_mode": "local",
    "public_base_url": "",

    # Wall - Slideshow (Bilder)
    "image_spawn_interval": 6,
    "max_images_on_screen": 10,
    "image_min_size": 100,
    "image_max_size": 150,

    # Wall - Slideshow (Videos)
    "max_videos_on_screen": 2,
    "video_playback_mode": "once",
    "video_spawn_interval": 10,
    "video_min_size": 100,
    "video_max_size": 150,

    # Bilder: Rotation/Bewegung
    "image_rotation_strength": 90,
    "image_drift_strength": 0.2,
    "image_rotation_direction_mode": "both",
    "image_flight_path_mode": "random",

    # Bilder: Geschwindigkeit
    "image_animation_duration": 30,
    "image_speed_variation_enabled": True,
    "image_speed_variation_strength": 0.4,

    # Bilder: Highlight
    "image_highlight_new": True,
    "image_highlight_duration": 10,
    "image_highlight_color": "#ffff00",
    "image_max_simultaneous_highlights": 3,

    # Videos: Rotation/Bewegung
    "video_rotation_strength": 90,
    "video_drift_strength": 0.2,
    "video_rotation_direction_mode": "both",
    "video_flight_path_mode": "random",

    # Videos: Geschwindigkeit
    "video_animation_duration": 30,
    "video_speed_variation_enabled": True,
    "video_speed_variation_strength": 0.4,

    # Videos: Highlight
    "video_highlight_new": True,
    "video_highlight_duration": 10,
    "video_highlight_color": "#ffff00",
    "video_max_simultaneous_highlights": 3,

    "center_highlight_enabled": False,
    "center_highlight_duration": 5,
    "center_highlight_mode": "fly",
    "center_highlight_entry_speed": 1.0,
    "center_highlight_exit_speed": 1.0,
    "center_highlight_screen_percent": 30,
    "center_highlight_max_simultaneous": 1,
    "center_highlight_position_variation": 30,

    "show_qr_code": True,
    "qr_text": "Schick uns dein Bild!",
    "qr_size": 220,
    "qr_text_size": 24,
    "qr_position": "center-bottom",
    "qr_text_color": "#db0a0a",

    "qr_dynamic_enabled": True,
    "qr_show_duration": 5,
    "qr_hide_duration": 5,

    # Banner
    "banner_enabled": False,
    "banner_text": "",
    "banner_position": "bottom",
    "banner_height": 120,
    "banner_color": "#000000",
    "banner_text_color": "#ffffff",
    "banner_show_duration": 10,
    "banner_hide_duration": 10,

    # Media-Cache (Fallback bei Verbindungsabbruch)
    "cache_enabled": False,
    "cache_ttl_minutes": 30,
    "cache_max_images": 100,
    "cache_max_videos": 20,
    "cache_max_size_mb": 500,

    # Debug
    "debug_overlay": False,
    "screen_wake_lock_enabled": False,
    "screen_wake_lock_alternative": False,

    # Upload-Seite
    "upload_greeting": "Lade deine Fotos hoch ❤️",
    "upload_image": "",
    "upload_button_color": "#ff4b5c",
    "upload_allow_videos": True,
    "upload_max_files": 20,
    "upload_max_file_size_mb": 50,

    # Rahmen um Bilder (weißer Rand)
    "frame_padding_top": 12,
    "frame_padding_side": 12,
    "frame_padding_bottom": 50,

    # Kommentare
    "comments_enabled": True,
    "comment_font": "Pacifico",
    "comment_color": "#e51515",
    "comment_size": 22,
    "comment_bold": False,
    "comment_underline": False,
    "comment_max_length": 80
}

# ------------------------------------------------
# Config Validator
# ------------------------------------------------

def validate_config():

    if not os.path.exists(CONFIG_FILE):

        print("CONFIG: config.json fehlt → neue Datei wird erstellt")

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

        return DEFAULT_CONFIG

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    changed = False

    # Migration: alte Keys auf neue image_/video_ Keys mappen
    MIGRATION = [
        ("rotation_strength", "image_rotation_strength", "video_rotation_strength"),
        ("drift_strength", "image_drift_strength", "video_drift_strength"),
        ("rotation_direction_mode", "image_rotation_direction_mode", "video_rotation_direction_mode"),
        ("flight_path_mode", "image_flight_path_mode", "video_flight_path_mode"),
        ("animation_duration", "image_animation_duration", "video_animation_duration"),
        ("speed_variation_enabled", "image_speed_variation_enabled", "video_speed_variation_enabled"),
        ("speed_variation_strength", "image_speed_variation_strength", "video_speed_variation_strength"),
        ("highlight_new_images", "image_highlight_new", "video_highlight_new"),
        ("highlight_duration", "image_highlight_duration", "video_highlight_duration"),
        ("highlight_color", "image_highlight_color", "video_highlight_color"),
        ("max_simultaneous_highlights", "image_max_simultaneous_highlights", "video_max_simultaneous_highlights"),
    ]
    for old_key, img_key, vid_key in MIGRATION:
        if old_key in config:
            if img_key not in config:
                config[img_key] = config[old_key]
                changed = True
            if vid_key not in config:
                config[vid_key] = config[old_key]
                changed = True

    # Grid: grid_interval -> grid_animation_duration
    if "grid_animation_duration" not in config and "grid_interval" in config:
        config["grid_animation_duration"] = config["grid_interval"]
        changed = True

    # Grid: grid_spacing_rows (alt) -> grid_spacing_columns, grid_spacing -> grid_spacing_rows
    if "grid_spacing_columns" not in config and "grid_spacing_rows" in config:
        config["grid_spacing_columns"] = config["grid_spacing_rows"]
        changed = True
    if "grid_spacing" in config:
        config["grid_spacing_rows"] = config["grid_spacing"]
        changed = True

    # center_highlight_scale -> center_highlight_screen_percent (grobe Umrechnung)
    if "center_highlight_screen_percent" not in config and "center_highlight_scale" in config:
        scale = float(config.get("center_highlight_scale", 1.6))
        config["center_highlight_screen_percent"] = min(100, max(5, int(scale * 15)))
        changed = True

    # Video-Größe von Bild-Größe übernehmen falls nicht gesetzt
    if "video_min_size" not in config and "image_min_size" in config:
        config["video_min_size"] = config["image_min_size"]
        changed = True
    if "video_max_size" not in config and "image_max_size" in config:
        config["video_max_size"] = config["image_max_size"]
        changed = True

    for key, value in DEFAULT_CONFIG.items():

        if key not in config:

            print(f"CONFIG WARNING: '{key}' fehlt → wird ergänzt")

            config[key] = value
            changed = True

    if changed:

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        print("CONFIG: config.json automatisch aktualisiert")

    return config


# ------------------------------------------------
# Config prüfen beim Start
# ------------------------------------------------

CONFIG = validate_config()

# ------------------------------------------------
# Server Port bestimmen
# ------------------------------------------------

SERVER_PORT = CONFIG.get("port", 8000)

# ------------------------------------------------
# FastAPI
# ------------------------------------------------

app = FastAPI()


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_config():
    """Chrome DevTools sucht diese Datei – leere Antwort reduziert 404-Logs."""
    return {}


@app.get("/api/version")
def api_version():
    """Liefert die Projektversion (z.B. für Admin-UI, Debug)."""
    return {"version": __version__, "name": "Local-browser-based-Photo-Frame"}


# ------------------------------------------------
# Service Worker (Media-Cache)
# ------------------------------------------------
# Der Service Worker fängt /media/*-Requests ab, cached sie und liefert
# bei Verbindungsabbruch aus dem Cache. BroadcastChannel informiert
# über Online/Offline-Status. TTL und Limits kommen aus der Config.

SW_SCRIPT = """
const CACHE_ENABLED = %(cache_enabled)s;
const CACHE_TTL_MS = %(cache_ttl_ms)s;
const CACHE_MAX_IMAGES = %(cache_max_images)s;
const CACHE_MAX_VIDEOS = %(cache_max_videos)s;
const CACHE_MAX_BYTES = %(cache_max_bytes)s;
const CACHE_NAME = 'wall-media-v1';
const META_NAME = 'wall-media-meta-v1';
const VIDEO_EXT = ['mp4','mov','webm'];
let serverOnline = true;
const bc = new BroadcastChannel('wall-server-state');
let lastCacheListSent = 0;
const CACHE_LIST_DEBOUNCE_MS = 500;
bc.onmessage = async (e) => {
  if (!e.data || !e.data.state) return;
  serverOnline = e.data.state === 'online';
  if (!serverOnline) {
    const now = Date.now();
    if (now - lastCacheListSent < CACHE_LIST_DEBOUNCE_MS) return;
    lastCacheListSent = now;
    const cache = await caches.open(CACHE_NAME);
    const keys = await cache.keys();
    const files = keys.map(k => (k.url.split('/').pop() || '?').split('?')[0]).filter(f => !f.endsWith('.txt'));
    const clients = await self.clients.matchAll();
    clients.forEach(c => c.postMessage({type: 'cache_list', files}));
  }
};

function isVideo(url){
  const ext = (url.split('.').pop() || '').toLowerCase().split('?')[0];
  return VIDEO_EXT.includes(ext);
}

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });

self.addEventListener('fetch', (e) => {
  if (!CACHE_ENABLED || !e.request.url.includes('/media/')) return;
  if (e.request.url.endsWith('.txt')) return;
  e.respondWith(handleMediaFetch(e.request, e.clientId));
});

async function evictIfNeeded(cache, metaCache, newUrl, newIsVideo, newSize) {
  const keys = await cache.keys();
  const entries = [];
  let totalBytes = 0;
  for (const k of keys) {
    const m = await metaCache.match(k);
    const j = m ? await m.json() : {};
    const t = j.t || 0;
    const sz = j.s || 0;
    totalBytes += sz;
    entries.push({url: k.url, t, isVideo: isVideo(k.url), size: sz});
  }
  let imgCount = entries.filter(e => !e.isVideo).length;
  let vidCount = entries.filter(e => e.isVideo).length;
  if (newIsVideo) vidCount++; else imgCount++;
  totalBytes += newSize;
  const toRemove = [];
  entries.sort((a,b) => a.t - b.t);
  for (const e of entries) {
    if (totalBytes > CACHE_MAX_BYTES || (e.isVideo && vidCount > CACHE_MAX_VIDEOS) || (!e.isVideo && imgCount > CACHE_MAX_IMAGES)) {
      toRemove.push(e);
      totalBytes -= e.size;
      if (e.isVideo) vidCount--; else imgCount--;
    }
  }
  for (const e of toRemove) {
    await cache.delete(e.url);
    await metaCache.delete(e.url);
  }
}

const lastCacheServeByFile = new Map();
const CACHE_SERVE_DEBOUNCE_MS = 300;
function notifyCacheServe(file, expired, clientId) {
  const now = Date.now();
  const last = lastCacheServeByFile.get(file) || 0;
  if (now - last < CACHE_SERVE_DEBOUNCE_MS) return;
  lastCacheServeByFile.set(file, now);
  setTimeout(() => lastCacheServeByFile.delete(file), CACHE_SERVE_DEBOUNCE_MS);
  const msg = {type:'cache_serve', file, expired};
  if (clientId) {
    self.clients.get(clientId).then(c => { if (c) c.postMessage(msg); }).catch(() => {});
  } else {
    self.clients.matchAll().then(clients => { clients.forEach(c => c.postMessage(msg)); });
  }
}
const lastCacheStoreByFile = new Map();
const CACHE_STORE_DEBOUNCE_MS = 300;
function notifyCacheStore(file, clientId) {
  const now = Date.now();
  const last = lastCacheStoreByFile.get(file) || 0;
  if (now - last < CACHE_STORE_DEBOUNCE_MS) return;
  lastCacheStoreByFile.set(file, now);
  setTimeout(() => lastCacheStoreByFile.delete(file), CACHE_STORE_DEBOUNCE_MS);
  const msg = {type:'cache_store', file};
  if (clientId) {
    self.clients.get(clientId).then(c => { if (c) c.postMessage(msg); }).catch(() => {});
  } else {
    self.clients.matchAll().then(clients => { clients.forEach(c => c.postMessage(msg)); });
  }
}

const fetchInFlight = new Map();

async function handleMediaFetch(request, clientId) {
  const cache = await caches.open(CACHE_NAME);
  const metaCache = await caches.open(META_NAME);
  const fn = (request.url.split('/').pop() || '?').split('?')[0];

  if (!serverOnline) {
    const cached = await cache.match(request.url);
    if (cached) {
      const metaRes = await metaCache.match(request.url);
      let expired = false;
      if (metaRes) {
        const meta = await metaRes.json();
        expired = Date.now() - meta.t >= CACHE_TTL_MS;
      }
      notifyCacheServe(fn, expired, clientId);
      return cached;
    }
    return new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  const url = request.url;
  const inFlight = fetchInFlight.get(url);
  if (inFlight) {
    const res = await inFlight;
    if (res) return res.clone();
    const fallback = await cache.match(request.url);
    return fallback || new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  async function doFetch() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    try {
      const netRes = await fetch(request, { cache: 'no-store', signal: controller.signal });
      clearTimeout(timeout);
      if (netRes && netRes.ok) {
        const alreadyCached = await cache.match(request.url);
        const clone = netRes.clone();
        const buf = await clone.arrayBuffer();
        const size = buf.byteLength;
        await evictIfNeeded(cache, metaCache, request.url, isVideo(request.url), size);
        await cache.put(request.url, netRes.clone());
        await metaCache.put(request.url, new Response(JSON.stringify({t: Date.now(), s: size})));
        if (!alreadyCached) notifyCacheStore(fn, clientId);
        return netRes;
      }
      return netRes;
    } catch (err) {
      clearTimeout(timeout);
      const cached = await cache.match(request.url);
      if (cached) {
        const metaRes = await metaCache.match(request.url);
        let expired = false;
        if (metaRes) {
          const meta = await metaRes.json();
          expired = Date.now() - meta.t >= CACHE_TTL_MS;
        }
        notifyCacheServe(fn, expired, clientId);
        return cached;
      }
      return null;
    }
  }

  const promise = doFetch();
  fetchInFlight.set(url, promise);
  try {
    const res = await promise;
    if (res) return res;
    return new Response('', {status: 503, statusText: 'Service Unavailable'});
  } finally {
    fetchInFlight.delete(url);
  }
}
"""


def _load_config_for_sw():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@app.get("/sw.js", response_class=Response)
def service_worker():
    """Liefert den Service-Worker-Code mit aktueller Cache-Config (TTL, Limits)."""
    cfg = _load_config_for_sw()
    enabled = cfg.get("cache_enabled", False)
    ttl_min = cfg.get("cache_ttl_minutes", 30)
    ttl_ms = ttl_min * 60 * 1000
    max_img = int(cfg.get("cache_max_images", 100))
    max_vid = int(cfg.get("cache_max_videos", 20))
    max_mb = float(cfg.get("cache_max_size_mb", 500))
    max_bytes = int(max_mb * 1024 * 1024) if max_mb > 0 else 4294967296  # 0 = unbegrenzt
    body = SW_SCRIPT % {
        "cache_enabled": "true" if enabled else "false",
        "cache_ttl_ms": ttl_ms,
        "cache_max_images": max_img,
        "cache_max_videos": max_vid,
        "cache_max_bytes": max_bytes,
    }
    return Response(
        content=body,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ------------------------------------------------
# Startup / Shutdown Hooks (Firewall)
# ------------------------------------------------

@app.on_event("startup")
async def startup_event():

    mode = CONFIG.get("network_mode", "local")

    print(f"[Network] Mode: {mode}")

    # --------------------------------
    # Firewall nur für network/public
    # --------------------------------

    if mode in ["network", "public"]:

        try:
            open_firewall_port(SERVER_PORT)
        except Exception as e:
            print("Firewall konnte nicht geöffnet werden:", e)

    else:

        print("[Firewall] Nicht nötig für Modus:", mode)

    # --------------------------------
    # Tunnel automatisch starten
    # --------------------------------

    if mode == "tunnel":

        try:

            print("[Tunnel] Starte Tunnel automatisch...")

            tunnel_manager.start(SERVER_PORT)

        except Exception as e:

            print("[Tunnel] Fehler beim Start:", e)


@app.on_event("shutdown")
async def shutdown_event():

    mode = CONFIG.get("network_mode", "local")

    # Firewall schließen
    if mode in ["network", "public"]:

        try:
            close_firewall_port(SERVER_PORT)
        except Exception as e:
            print("Firewall konnte nicht geschlossen werden:", e)

    # Tunnel stoppen
    if mode == "tunnel":

        try:
            tunnel_manager.stop()
        except Exception as e:
            print("[Tunnel] Fehler beim Stop:", e)


# ------------------------------------------------
# Statische Dateien
# ------------------------------------------------
# /media: Hochgeladene Bilder und Videos
# /header: Header-Bild für Upload-Seite
# /background: Hintergrundbilder für die Wall

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/header", StaticFiles(directory=HEADER_DIR), name="header")
app.mount("/background", StaticFiles(directory=BACKGROUND_DIR), name="background")

# ------------------------------------------------
# Router laden
# ------------------------------------------------

from server.routes import upload
from server.routes import wall
from server.routes import admin
from server.tunnel_manager import tunnel_manager

app.include_router(upload.router)
app.include_router(wall.router)
app.include_router(admin.router)

# ----------------------------------------
# Tunnel-Management (Status, Start, Stop)
# ----------------------------------------

@app.get("/api/tunnel/status")
async def tunnel_status():
    """
    Liefert JSON zurück mit:
      { "running": True/False, "url": "öffentliche URL" }
    """
    return tunnel_manager.status()

@app.post("/api/tunnel/start")
async def tunnel_start():
    """
    Startet den Tunnel (wenn noch nicht gestartet).
    """
    tunnel_manager.start(SERVER_PORT)
    return {"status": "starting"}

@app.post("/api/tunnel/stop")
async def tunnel_stop():
    """
    Stoppt den Tunnel (falls aktiv).
    """
    tunnel_manager.stop()
    return {"status": "stopped"}