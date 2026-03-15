import json
import socket
import urllib.request
import os
from server.main import PROJECT_DIR
from server.tunnel_manager import tunnel_manager


CONFIG_FILE = os.path.join(PROJECT_DIR,"config.json")


def get_local_ip():

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    ip = s.getsockname()[0]
    s.close()

    return ip


# ------------------------------------------------
# NEW: External IP detection
# ------------------------------------------------

def get_external_ip():

    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as r:
            return r.read().decode()
    except:
        return None


def get_base_url():

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

    return get_base_url() + "/upload"


# ------------------------------------------------
# NEW: Wall URL
# ------------------------------------------------

def get_wall_url():

    return get_base_url() + "/wall"


# ------------------------------------------------
# NEW: Debug information
# ------------------------------------------------

def get_network_info():

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