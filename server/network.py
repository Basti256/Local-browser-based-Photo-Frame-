"""
Netzwerk-Utilities: IP-Adressen, URLs, Admin-Infos.

- get_local_ip(): Lokale IP im LAN
- get_external_ip(): Externe IP (via ipify.org)
- get_base_url(): Basis-URL je nach network_mode (local/network/public/tunnel)
- get_upload_url(), get_wall_url(): Konkrete Seiten-URLs
- get_network_info(): Infos für Admin-Status (mode, port, IPs, URLs)
"""
import json
import socket
import urllib.request
import os
from server.main import PROJECT_DIR
from server.tunnel_manager import tunnel_manager

CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")


def get_local_ip():
    """Ermittelt die lokale IP-Adresse (z.B. 192.168.1.100) via UDP-Verbindung zu 8.8.8.8."""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    ip = s.getsockname()[0]
    s.close()

    return ip


# ------------------------------------------------
# NEW: External IP detection
# ------------------------------------------------

def get_external_ip():
    """Ermittelt die externe (öffentliche) IP via api.ipify.org. None bei Fehler."""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as r:
            return r.read().decode()
    except Exception:
        return None


def get_base_url():
    """Liefert die Basis-URL (z.B. http://192.168.1.100:8000) je nach network_mode."""

    if not os.path.exists(CONFIG_FILE):
        return "http://127.0.0.1:8000"

    with open(CONFIG_FILE,"r") as f:
        cfg=json.load(f)

    mode = cfg.get("network_mode","local")
    port = cfg.get("port",8000)

    # --------------------------------
    # Local
    # --------------------------------
    if mode == "local":

        return f"http://127.0.0.1:{port}"

    # --------------------------------
    # Network
    # --------------------------------
    if mode == "network":

        ip = get_local_ip()
        return f"http://{ip}:{port}"

    # --------------------------------
    # Public Legacy
    # --------------------------------
    if mode == "public":

        url = cfg.get("public_base_url","")

        if url:
            return url

        external_ip = get_external_ip()

        if external_ip:
            return f"http://{external_ip}:{port}"

        ip = get_local_ip()
        return f"http://{ip}:{port}"

    # --------------------------------
    # Public Tunnel
    # --------------------------------
    if mode == "tunnel":

        if tunnel_manager.running and tunnel_manager.public_url:
            return tunnel_manager.public_url

        # fallback solange Tunnel noch startet
        return f"http://127.0.0.1:{port}"

    # --------------------------------
    # Fallback
    # --------------------------------
    return f"http://127.0.0.1:{port}"


def get_upload_url():
    """URL der Upload-Seite für Gäste (z.B. für QR-Code)."""
    return get_base_url() + "/upload"


def get_wall_url():
    """URL der Wall-Anzeige."""
    return get_base_url() + "/wall"


def get_network_info():
    """Liefert ein Dict mit mode, port, local_ip, external_ip, upload_url, wall_url für die Admin-UI."""

    if not os.path.exists(CONFIG_FILE):
        return {}

    with open(CONFIG_FILE,"r") as f:
        cfg=json.load(f)

    port = cfg.get("port",8000)
    mode = cfg.get("network_mode","internal")

    info = {
        "mode": mode,
        "port": port,
        "local_ip": get_local_ip(),
        "external_ip": get_external_ip(),
        "upload_url": get_upload_url(),
        "wall_url": get_wall_url()
    }

    return info