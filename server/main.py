import os
import sys
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Firewall Steuerung
from server.firewall import open_firewall_port, close_firewall_port

# ------------------------------------------------
# Projekt bestimmen
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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_DIR = os.path.join(BASE_DIR, "projects", PROJECT_NAME)
MEDIA_DIR = os.path.join(PROJECT_DIR, "media")
HEADER_DIR = os.path.join(PROJECT_DIR, "header")
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(HEADER_DIR, exist_ok=True)

# ------------------------------------------------
# Default Config
# ------------------------------------------------

DEFAULT_CONFIG = {

    # Netzwerk
    "network_mode": "local",
    "public_base_url": "",
    "server_bind": "auto",

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
    "center_highlight_scale": 1.6,
    "center_highlight_max_simultaneous": 1,
    "center_highlight_position_variation": 30,

    "show_qr_code": True,
    "qr_text": "Schick uns dein Bild!",
    "qr_url": "",
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

    # Debug
    "debug_overlay": False,

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
# Static mounts (Media + Header)
# ------------------------------------------------

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/header", StaticFiles(directory=HEADER_DIR), name="header")

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