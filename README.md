# Local-browser-based-Photo-Frame

**Version 1.0**

Ein interaktiver Foto-Rahmen für (in meinem Fall) Hochzeiten: Gäste können Fotos und Videos per QR-Code hochladen, die live auf einem Bildschirm angezeigt werden. Es kann auch für jede andere Art von Bildern/Videos verwendet werden.

---

## Inhaltsverzeichnis

- [Features](#features)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Start](#start)
- [Projektstruktur](#projektstruktur)
- [Verwendete Bibliotheken](#verwendete-bibliotheken)
- [Lizenz](#lizenz)

---

## Features

### Kernfunktionen

- **Projekt-basiert** – Mehrere Events als separate Projekte mit eigener Config und Medien
- **QR-Code** – Gäste scannen und laden direkt hoch (Upload-Seite)
- **Live-Wall** – Fotos und Videos erscheinen animiert auf dem Bildschirm
- **Admin-Interface** – Konfiguration, Statistiken, Upload-Verwaltung
- **WebSocket** – Echtzeit-Synchronisation bei neuen Uploads

### Anzeige-Modi

- **Fly-Modus** – Bilder und Videos fliegen über den Bildschirm (Slideshow mit Animation)
- **Grid-Modus** – Mehrere Spalten, Bilder laufen von unten nach oben durch

### Wall-Einstellungen

- **Center Highlight** – Neue Bilder erscheinen groß in der Mitte (Fly Through oder Spotlight)
- **Entry/Exit Speed** – Einblend- und Abfluggeschwindigkeit konfigurierbar
- **Hintergrund** – Farbe oder Bild wählbar, Upload direkt in der Admin-UI
- **Banner** – Text-Banner oben oder unten (Markdown unterstützt)
- **Kommentare** – Textdateien neben Bildern (z.B. `bild.jpg` + `bild.txt`)

### Extras

- **Bildschirm wach halten** – Verhindert Bildschirmschoner
  - Wake Lock API (Chrome, unterstützte Browser)
  - Alternative Wachfunktion (Video-Fallback für Edge, Firefox)
- **Media-Cache** – Fallback bei Verbindungsabbruch (Service Worker)
- **Highlight-Queue** – Neue Uploads werden priorisiert angezeigt

### Netzwerk

- **Local** – Nur dieser Computer
- **Network** – Im WLAN sichtbar (Firewall-Port wird automatisch geöffnet)
- **Public** – Router Port-Forwarding
- **Tunnel** – Cloudflare Tunnel für öffentlichen Zugriff ohne Port-Forwarding

---

## Voraussetzungen

- **Python 3.10+**
- **Windows** (für Firewall-Regeln; läuft auch auf Linux/macOS ohne Firewall-Automatik)
- **Cloudflare Tunnel (optional)** – Für den Tunnel-Modus wird `cloudflared` benötigt

---

## Installation

```bash
# Repository klonen
git clone https://github.com/Basti256/Local-browser-based-Photo-Frame-.git
cd Local-browser-based-Photo-Frame-

# Virtuelle Umgebung anlegen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### Cloudflare Tunnel (für öffentlichen Zugriff)

Der **Tunnel-Modus** ermöglicht einen öffentlichen Zugriff ohne Port-Forwarding:

1. **Download**: [Cloudflare Tunnel – Downloads](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)
2. **Windows**: `cloudflared-windows-amd64.exe` herunterladen und als `cloudflared.exe` in den Ordner `bin/` legen
3. Alternativ: `winget install --id Cloudflare.cloudflared` (danach Pfad zu `cloudflared.exe` in `bin/` kopieren)

Ohne `bin/cloudflared.exe` funktioniert der Tunnel-Modus nicht; alle anderen Features laufen normal.

---

## Start

```bash
# Option 1 – GUI (empfohlen)
start.bat
# oder
venv\Scripts\python.exe gui\server_gui.py

# Option 2 – Server manuell
venv\Scripts\python.exe -m uvicorn server.main:app --port 8000 --project=Example
```

Nach dem Start:

- **Wall**: `http://localhost:8000/wall` (oder `http://<IP>:8000/wall` im Netzwerk)
- **Admin**: `http://localhost:8000/admin`
- **Upload-Seite**: `http://localhost:8000/upload`

---

## Projektstruktur

```
├── bin/              # cloudflared.exe (optional, für Tunnel-Modus)
├── gui/              # Tkinter-Verwaltungsoberfläche
│   └── server_gui.py
├── server/           # FastAPI-Backend
│   ├── main.py       # App, Config, Service Worker
│   ├── version.py    # __version__ = "1.0"
│   ├── network.py    # Netzwerk-Infos, URLs
│   ├── stats.py      # Statistiken (Wall, Upload)
│   ├── firewall.py   # Windows-Firewall
│   ├── tunnel_manager.py  # Cloudflare Tunnel
│   └── routes/
│       ├── wall.py       # Wall (Fly-Modus), WebSocket, API
│       ├── wall_grid.py  # Wall (Grid-Modus)
│       ├── admin.py      # Admin (Fly)
│       ├── admin_grid.py # Admin (Grid)
│       └── upload.py     # Upload-Seite
├── projects/         # Projekt-Ordner
│   └── <projekt>/
│       ├── config.json
│       ├── media/        # Hochgeladene Bilder/Videos
│       ├── header/       # Header-Bild für Upload-Seite
│       └── background/   # Hintergrundbilder für die Wall
├── requirements.txt
├── start.bat
├── CHANGELOG.md
└── README.md
```

---

## Verwendete Bibliotheken

### Python (Backend)

| Paket | Beschreibung | Link |
|-------|--------------|------|
| FastAPI | Web-Framework | [github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi) |
| Uvicorn | ASGI-Server | [github.com/encode/uvicorn](https://github.com/encode/uvicorn) |
| Pillow | Bildverarbeitung | [github.com/python-pillow/Pillow](https://github.com/python-pillow/Pillow) |
| pillow-heif | HEIC/HEIF-Support | [github.com/bigcat88/pillow_heif](https://github.com/bigcat88/pillow_heif) |
| qrcode | QR-Code-Generierung (Python) | [github.com/lincolnloop/python-qrcode](https://github.com/lincolnloop/python-qrcode) |
| PySide6 | GUI (Qt) | [github.com/qt/qtbase](https://github.com/qt/qtbase) |
| psutil | System-Infos | [github.com/giampaolo/psutil](https://github.com/giampaolo/psutil) |

### JavaScript (Frontend, via CDN)

| Bibliothek | Beschreibung | Link |
|------------|--------------|------|
| QRCode.js | QR-Code-Rendering im Browser | [github.com/davidshimjs/qrcodejs](https://github.com/davidshimjs/qrcodejs) |
| marked | Markdown-Parsing (Banner) | [github.com/markedjs/marked](https://github.com/markedjs/marked) |

### Externe Dienste

- **Cloudflare Tunnel** – Öffentlicher Zugriff ohne Port-Forwarding  
  [developers.cloudflare.com/cloudflare-one](https://developers.cloudflare.com/cloudflare-one/)

---

## Lizenz

MIT (oder nach Wunsch anpassen)
