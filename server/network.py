"""Netzwerk-Utilities: LAN-IP und projektbezogene Basis-URL."""
import socket
import urllib.request

from server.defaults import NETWORK_MODE_ALIASES, NETWORK_MODES
from server.project import get_paths, load_project_config, project_listen_port
from server.runtime import load_runtime, update_runtime


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_external_ip() -> str | None:
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as r:
            return r.read().decode()
    except Exception:
        return None


def sanitize_public_host(value: str) -> str:
    host = (value or "").strip()
    lowered = host.lower()
    if lowered.startswith("https://"):
        host = host[8:]
    elif lowered.startswith("http://"):
        host = host[7:]
    host = host.split("/")[0].split("?")[0].strip()
    if "@" in host:
        host = host.split("@", 1)[-1]
    return host


def normalize_mode(mode: str | None) -> str:
    mode = mode or "network"
    if mode in NETWORK_MODE_ALIASES:
        mode = NETWORK_MODE_ALIASES[mode]
    if mode not in NETWORK_MODES:
        return "network"
    return mode


def lan_origin(request, port: int) -> str:
    hostname = getattr(request.url, "hostname", None) or "127.0.0.1"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    scheme = getattr(request.url, "scheme", None) or "http"
    port = int(port)
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{hostname}"
    return f"{scheme}://{hostname}:{port}"


def public_origin() -> str:
    rt = load_runtime()
    host = sanitize_public_host(rt.get("public_host") or "")
    if not host:
        return ""
    scheme = "https" if rt.get("public_https") else "http"
    return f"{scheme}://{host}".rstrip("/")


def lan_base_url(config: dict | None = None) -> str:
    if config is None:
        paths = get_paths()
        config = load_project_config(paths) if paths else {}
    port = project_listen_port(config=config) if config else int(load_runtime().get("port", 8000))
    return f"http://{get_local_ip()}:{port}"


def public_base_url(name: str | None = None) -> str:
    origin = public_origin()
    slug = (name or "").strip()
    if not origin or not slug:
        return ""
    return f"{origin}/{slug}"


def advertised_base_url(config: dict | None = None, name: str | None = None) -> str:
    paths = get_paths()
    if config is None:
        config = load_project_config(paths) if paths else {}
    if name is None and paths:
        name = paths.name
    mode = normalize_mode(config.get("network_mode"))
    if mode == "public":
        return public_base_url(name) or lan_base_url(config)
    return lan_base_url(config)


def get_base_url() -> str:
    return advertised_base_url()


def get_upload_url() -> str:
    return get_base_url() + "/upload"


def get_wall_url() -> str:
    return get_base_url() + "/wall"


def migrate_server_public_host() -> None:
    rt = load_runtime()
    if sanitize_public_host(rt.get("public_host") or ""):
        return
    from server.project import ProjectPaths, list_projects
    for name in list_projects():
        cfg = load_project_config(ProjectPaths(name))
        host = sanitize_public_host(cfg.get("public_host") or "")
        if host:
            update_runtime(public_host=host, public_https=bool(cfg.get("public_https")))
            return


def get_network_info() -> dict:
    migrate_server_public_host()
    rt = load_runtime()
    control_port = int(rt.get("port", 8000))
    paths = get_paths()
    cfg = load_project_config(paths) if paths else {}
    mode = normalize_mode(cfg.get("network_mode"))
    project_port = project_listen_port(paths, cfg) if paths else control_port
    name = paths.name if paths else ""
    return {
        "mode": mode,
        "port": project_port,
        "control_port": control_port,
        "local_ip": get_local_ip(),
        "external_ip": get_external_ip(),
        "public_host": sanitize_public_host(rt.get("public_host") or ""),
        "public_https": bool(rt.get("public_https")),
        "public_origin": public_origin(),
        "upload_url": get_upload_url() if paths else "",
        "wall_url": get_wall_url() if paths else "",
        "base_url": get_base_url() if paths else "",
        "local_url": lan_base_url(cfg) if paths else "",
        "public_url": public_base_url(name) if paths and mode == "public" else "",
        "bind_host": rt.get("bind_host") or "0.0.0.0",
        "log_level": rt.get("log_level") or "INFO",
    }
