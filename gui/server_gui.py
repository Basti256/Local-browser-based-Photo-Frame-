import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import os
import json
import subprocess
import webbrowser
import socket
import psutil
import zipfile
import sys
import platform
import requests
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.join(BASE_DIR, "projects")

processes = {}
project_labels = {}

prev_net = psutil.net_io_counters()

# ------------------------------------------------
# Network
# ------------------------------------------------

def get_local_ip():

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        return ip

    except:

        return "127.0.0.1"


def get_tunnel_status(port):

    try:

        r = requests.get(f"http://127.0.0.1:{port}/api/tunnel/status", timeout=1)

        if r.ok:
            return r.json()

    except:
        pass

    return {"running": False, "url": None}

# ------------------------------------------------
# Firewall
# ------------------------------------------------

def firewall_rule_name(project, port):

    return f"WeddingPhotoServer_{project}_{port}"


def open_firewall_port(project, port):

    if platform.system() != "Windows":
        return

    rule = firewall_rule_name(project, port)

    subprocess.run(
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={rule}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def close_firewall_port(project, port):

    if platform.system() != "Windows":
        return

    rule = firewall_rule_name(project, port)

    subprocess.run(
        [
            "netsh",
            "advfirewall",
            "firewall",
            "delete",
            "rule",
            f"name={rule}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ------------------------------------------------
# Utilities
# ------------------------------------------------

def is_server_running(port):

    try:

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.settimeout(0.2)

            return s.connect_ex(("127.0.0.1", port)) == 0

    except:

        return False


def load_projects():

    projects = {}

    if not os.path.exists(PROJECT_DIR):
        return projects

    for folder in os.listdir(PROJECT_DIR):

        cfg = os.path.join(PROJECT_DIR, folder, "config.json")

        if not os.path.exists(cfg):
            continue

        try:

            with open(cfg, encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:

            print(f"Config Fehler in {folder}: {e}")
            continue

        # -----------------------------
        # fehlende Defaultwerte ergänzen
        # -----------------------------

        defaults = {

            "project_name": folder,
            "port": 8000,
            "network_mode": "internal",
            "public_base_url": "",
            "runtime": 0,
            "created": "",

            # wall defaults
            "image_spawn_interval": 6,
            "max_images_on_screen": 20,
            "image_min_size": 100,
            "image_max_size": 150,

            "animation_duration": 30,
            "rotation_strength": 90,
            "rotation_direction_mode": "both",

            "flight_path_mode": "random",
            "drift_strength": 0.2,

            "speed_variation_enabled": True,
            "speed_variation_strength": 0.4,

            "highlight_new_images": True,
            "highlight_duration": 10,
            "highlight_color": "#FFD700",
            "max_simultaneous_highlights": 3,

            "comments_enabled": True,

            "max_videos_on_screen": 2,
            "video_playback_mode": "once",

            "show_qr_code": True,
            "qr_size": 220,
            "qr_text_size": 28,

            "banner_enabled": False,

            "frame_padding_top": 12,
            "frame_padding_side": 12,
            "frame_padding_bottom": 50

        }

        for key, val in defaults.items():

            if key not in data:
                data[key] = val

        projects[folder] = data

    return projects

    projects = {}

    if not os.path.exists(PROJECT_DIR):
        return projects

    for folder in os.listdir(PROJECT_DIR):

        cfg = os.path.join(PROJECT_DIR, folder, "config.json")

        if os.path.exists(cfg):

            try:

                with open(cfg) as f:

                    data = json.load(f)

                projects[folder] = data

            except:

                pass

    return projects


def count_media(name):

    media = os.path.join(PROJECT_DIR, name, "media")

    if not os.path.exists(media):

        return 0

    try:

        return len(os.listdir(media))

    except:

        return 0


def find_free_port(start=8000):

    used = []

    for p in load_projects().values():

        used.append(p.get("port", 8000))

    port = start

    while port in used:

        port += 1

    return port


# ------------------------------------------------
# Projekt erstellen
# ------------------------------------------------

def create_project():

    name = simpledialog.askstring("Projektname", "Projektname")

    if not name:
        return

    suggested_port = find_free_port()

    port = simpledialog.askinteger(
        "Port", f"Port wählen (Vorschlag {suggested_port})", initialvalue=suggested_port
    )

    if not port:
        return

    folder = os.path.join(PROJECT_DIR, name)

    os.makedirs(os.path.join(folder, "media"), exist_ok=True)

    config = {
        "project_name": name,
        "port": port,
        "network_mode": "internal",
        "public_base_url": "",
        "runtime": 0,
        "created": datetime.now().isoformat(),
    }

    with open(os.path.join(folder, "config.json"), "w") as f:

        json.dump(config, f, indent=4)

    refresh()


# ------------------------------------------------
# Server starten
# ------------------------------------------------

def start_project(name, port):

    if is_server_running(port):

        return

    config = load_projects()[name]

    mode = config.get("network_mode", "internal")

    host = "127.0.0.1" if mode == "internal" else "0.0.0.0"

    if mode in ["local", "public"]:

        open_firewall_port(name, port)

    env = os.environ.copy()

    env["PROJECT_NAME"] = name

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "server.main:app",
            "--port",
            str(port),
            "--host",
            host,
        ],
        cwd=BASE_DIR,
        env=env,
    )

    processes[name] = proc

    refresh()


# ------------------------------------------------
# Server stoppen
# ------------------------------------------------

def stop_project(name):

    if name not in processes:

        return

    if not messagebox.askyesno("Stop Server", f"{name} wirklich stoppen?"):

        return

    proc = processes.get(name)

    try:

        parent = psutil.Process(proc.pid)

        for child in parent.children(recursive=True):

            child.kill()

        parent.kill()

    except:

        pass

    port = load_projects()[name].get("port", 8000)

    close_firewall_port(name, port)

    processes.pop(name, None)

    refresh()


def start_tunnel(name):
    # Projekt-Port aus den Projektdaten ermitteln
    projects = load_projects()
    port = projects[name]['port']
    try:
        requests.post(f"http://127.0.0.1:{port}/api/tunnel/start")
    except Exception as e:
        messagebox.showerror("Fehler", f"Tunnel konnte nicht gestartet werden:\n{e}")

def stop_tunnel(name):
    projects = load_projects()
    port = projects[name]['port']
    try:
        requests.post(f"http://127.0.0.1:{port}/api/tunnel/stop")
    except Exception as e:
        messagebox.showerror("Fehler", f"Tunnel konnte nicht gestoppt werden:\n{e}")

# ------------------------------------------------
# Dashboard
# ------------------------------------------------

def update_dashboard():

    global prev_net

    now = psutil.net_io_counters()

    up = (now.bytes_sent - prev_net.bytes_sent) / 1024 / 1024
    down = (now.bytes_recv - prev_net.bytes_recv) / 1024 / 1024

    prev_net = now

    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent

    ip = get_local_ip()

    # Schnelle Werte direkt im GUI-Thread aktualisieren
    upload_label.config(text=f"Upload {up:.2f} MB/s")
    download_label.config(text=f"Download {down:.2f} MB/s")

    cpu_label.config(text=f"CPU {cpu}%")
    ram_label.config(text=f"RAM {ram}%")

    ip_label.config(text=f"Local IP: {ip}")

    # Langsamere Port-Scans in einem Hintergrund-Thread ausführen
    def worker():

        projects = load_projects()
        open_ports = []

        for name, data in projects.items():

            port = data.get("port", 8000)

            if is_server_running(port):

                open_ports.append(str(port))

        ports = ", ".join(open_ports) if open_ports else "none"

        def apply_results():
            ports_label.config(text=f"Open Ports: {ports}")

        root.after(0, apply_results)

    threading.Thread(target=worker, daemon=True).start()

    root.after(2000, update_dashboard)


# ------------------------------------------------
# Projektstatus
# ------------------------------------------------

def update_project_stats():
    # Netzwerk- und Port-Prüfungen in einen Hintergrund-Thread auslagern,
    # damit der Tkinter-Hauptthread nicht blockiert.

    def worker():

        projects = load_projects()
        results = {}

        for name, data in projects.items():

            port = data.get("port", 8000)
            media = count_media(name)
            running = is_server_running(port)
            tunnel = get_tunnel_status(port)

            results[name] = {
                "port": port,
                "media": media,
                "running": running,
                "tunnel_running": tunnel.get("running", False),
            }

        def apply_results():

            for name, info in results.items():

                if name not in project_labels:
                    continue

                tunnel_state = "🌍 Tunnel ON" if info["tunnel_running"] else "⚫ Tunnel OFF"
                status = "🟢 Running" if info["running"] else "🔴 Stopped"
                status += " | " + tunnel_state

                project_labels[name].config(
                    text=f"{name} | Port {info['port']} | {info['media']} Dateien | {status}"
                )

        # GUI-Update sicher im Hauptthread ausführen
        root.after(0, apply_results)

    threading.Thread(target=worker, daemon=True).start()

    root.after(4000, update_project_stats)

# ------------------------------------------------
# Tunnelstatus
# ------------------------------------------------   
    
def get_tunnel_status(port):

    try:

        r = requests.get(f"http://127.0.0.1:{port}/api/tunnel/status", timeout=1)

        if r.ok:
            return r.json()

    except:
        pass

    return {"running": False, "url": None}


# ------------------------------------------------
# Export
# ------------------------------------------------

def export_project(name):

    folder = os.path.join(PROJECT_DIR, name)

    path = filedialog.asksaveasfilename(
        defaultextension=".zip", initialfile=f"{name}_backup.zip"
    )

    if not path:
        return

    with zipfile.ZipFile(path, "w") as z:

        for root_dir, dirs, files in os.walk(folder):

            for file in files:

                full = os.path.join(root_dir, file)

                rel = os.path.relpath(full, folder)

                z.write(full, rel)

    messagebox.showinfo("Export", "Backup erstellt")


# ------------------------------------------------
# GUI Refresh
# ------------------------------------------------

def refresh():

    for w in project_frame.winfo_children():

        w.destroy()

    project_labels.clear()

    projects = load_projects()

    row = 0

    for name, data in projects.items():

        port = data.get("port", 8000)

        label = ttk.Label(project_frame)
        label.grid(row=row, column=0, sticky="w")

        project_labels[name] = label

        ttk.Button(
            project_frame,
            text="Start",
            command=lambda n=name, p=port: start_project(n, p),
        ).grid(row=row, column=1)

        ttk.Button(
            project_frame,
            text="Stop",
            command=lambda n=name: stop_project(n),
        ).grid(row=row, column=2)

        ttk.Button(
            project_frame,
            text="Wall",
            command=lambda p=port: open_page(p, "wall"),
        ).grid(row=row, column=3)

        ttk.Button(
            project_frame,
            text="Upload",
            command=lambda p=port: open_page(p, "upload"),
        ).grid(row=row, column=4)

        ttk.Button(
            project_frame,
            text="Admin",
            command=lambda p=port: open_page(p, "admin"),
        ).grid(row=row, column=5)

        ttk.Button(
            project_frame,
            text="Export",
            command=lambda n=name: export_project(n),
        ).grid(row=row, column=6)

        ttk.Button(
            project_frame,
            text="Start Tunnel",
            command=lambda n=name: start_tunnel(n),
        ).grid(row=row, column=7)

        ttk.Button(
            project_frame,
            text="Stop Tunnel",
            command=lambda n=name: stop_tunnel(n),
        ).grid(row=row, column=8)

        row += 1


# ------------------------------------------------
# Seiten öffnen
# ------------------------------------------------

def open_page(port, page):

    webbrowser.open(f"http://localhost:{port}/{page}")


# ------------------------------------------------
# GUI
# ------------------------------------------------

root = tk.Tk()

root.title("Wedding Photo Server")

root.geometry("1200x650")

left = ttk.Frame(root)

left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

ttk.Button(left, text="Neues Projekt", command=create_project).pack(pady=10)

project_frame = ttk.Frame(left)

project_frame.pack(fill="both", expand=True)

right = ttk.Frame(root)

right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

ttk.Label(right, text="Network Panel", font=("Arial", 16)).pack(pady=10)

ip_label = ttk.Label(right, text="Local IP:")

ip_label.pack()

ports_label = ttk.Label(right, text="Open Ports:")

ports_label.pack()

upload_label = ttk.Label(right, text="Upload 0 MB/s")

upload_label.pack()

download_label = ttk.Label(right, text="Download 0 MB/s")

download_label.pack()

cpu_label = ttk.Label(right, text="CPU 0%")

cpu_label.pack()

ram_label = ttk.Label(right, text="RAM 0%")

ram_label.pack()

refresh()

root.after(2000, update_dashboard)

root.after(3000, update_project_stats)

root.mainloop()