# Wedding Photo Frame

Ein interaktiver Foto-Rahmen für (in meinem Fall) Hochzeiten: Gäste können Fotos und Videos per QR-Code hochladen, die live auf einem Bildschirm angezeigt werden. Es kann auch für jede andere Art von Bildern/Videos verwendet werden. 

## Features

- **Projekt-basiert**: Mehrere Hochzeiten/Events als separate Projekte
- **QR-Code**: Gäste scannen und laden direkt hoch
- **Live-Wall**: Fotos und Videos erscheinen animiert auf dem Bildschirm
- **Admin-Interface**: Konfiguration, Statistiken, Upload-Verwaltung
- **Tunnel-Modus**: Optional öffentlich erreichbar ohne Port-Forwarding

## Voraussetzungen

- Python 3.10+
- Windows (für Firewall-Regeln; läuft auch auf anderen Systemen ohne Firewall-Automatik)
- **Cloudflare Tunnel (optional)**: Für den Tunnel-Modus wird `cloudflared` benötigt – siehe unten

## Installation

```bash
# Repository klonen
git clone https://github.com/Basti256/Local-browser-based-Photo-Frame-.git
cd wedding-photo-frame

# Virtuelle Umgebung anlegen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### Cloudflare Tunnel (für öffentlichen Zugriff)

Der **Tunnel-Modus** ermöglicht einen öffentlichen Zugriff ohne Port-Forwarding. Dafür wird `cloudflared` benötigt:

1. **Download**: [Cloudflare Tunnel – Downloads](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)
2. **Windows**: `cloudflared-windows-amd64.exe` herunterladen und als `cloudflared.exe` in den Ordner `bin/` legen
3. Alternativ per winget: `winget install --id Cloudflare.cloudflared` (danach Pfad zu `cloudflared.exe` in `bin/` kopieren oder anpassen)

Ohne `bin/cloudflared.exe` funktioniert der Tunnel-Modus nicht; alle anderen Features laufen normal.

## Start

**Option 1 – GUI (empfohlen):**
```bash
start.bat
```
oder
```bash
venv\Scripts\python.exe gui\server_gui.py
```

**Option 2 – Server manuell:**
```bash
venv\Scripts\python.exe -m uvicorn server.main:app --port 8000 --project=DeinProjekt
```

## Projektstruktur

```
├── bin/           # cloudflared.exe (optional, für Tunnel-Modus)
├── gui/           # Tkinter-Verwaltungsoberfläche
├── server/        # FastAPI-Backend
├── projects/      # Projekt-Ordner (config.json + media/)
├── requirements.txt
└── start.bat
```

## Lizenz

MIT
