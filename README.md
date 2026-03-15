# Wedding Photo Frame

Ein interaktiver Foto-Rahmen für Hochzeiten: Gäste können Fotos und Videos per QR-Code hochladen, die live auf einem Bildschirm angezeigt werden.

## Features

- **Projekt-basiert**: Mehrere Hochzeiten/Events als separate Projekte
- **QR-Code**: Gäste scannen und laden direkt hoch
- **Live-Wall**: Fotos und Videos erscheinen animiert auf dem Bildschirm
- **Admin-Interface**: Konfiguration, Statistiken, Upload-Verwaltung
- **Tunnel-Modus**: Optional öffentlich erreichbar ohne Port-Forwarding

## Voraussetzungen

- Python 3.10+
- Windows (für Firewall-Regeln; läuft auch auf anderen Systemen ohne Firewall-Automatik)

## Installation

```bash
# Repository klonen
git clone https://github.com/DEIN-USERNAME/wedding-photo-frame.git
cd wedding-photo-frame

# Virtuelle Umgebung anlegen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

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
├── gui/           # Tkinter-Verwaltungsoberfläche
├── server/        # FastAPI-Backend
├── projects/      # Projekt-Ordner (config.json + media/)
├── requirements.txt
└── start.bat
```

## Lizenz

MIT (oder nach Wunsch anpassen)
