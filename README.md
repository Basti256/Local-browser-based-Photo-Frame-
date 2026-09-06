# Local-browser-based-Photo-Frame

**Version 2.13.2**

Browserbasierter Foto-Rahmen: Gäste laden Bilder und Videos über eine Upload-Seite. Eine Wall zeigt die Medien in Echtzeit. Die Einrichtung liegt unter `/setup` (Konto **Admin**). Die Wand-Einstellungen unter `/admin` sind per Projekt-PIN geschützt.

---

## Voraussetzungen

- Python 3.10 oder neuer
- Windows oder Linux (Debian als Zielplattform)
- Optional: `ffmpeg` (Video-Transcoding)

---

## Installation

```bash
git clone <repository-url>
cd Local-browser-based-Photo-Frame-
python3 -m venv venv
```

Linux:

```bash
venv/bin/pip install -r requirements.txt
chmod +x start.sh
./start.sh
```

Windows:

```bat
venv\Scripts\pip install -r requirements.txt
start.bat
```

Debian, optionale Systempakete:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg
```

---

## Start

```bash
python -m server
```

Optionen: `--host`, `--port`. Default-Bind `0.0.0.0`, Port 8000 aus `data/runtime.json`.

Nach dem Start:

- Erstkonfiguration: `http://127.0.0.1:8000/setup`
- Anmeldung (Admin): `http://127.0.0.1:8000/login`

Der Port 8000 ist der Einrichtungs-Port. Jedes Projekt hat einen eigenen Port (beim Anlegen vergeben). Unter `/setup` Starten/Stoppen. Wall, Upload und Admin hängen am Projekt-Port, zum Beispiel `http://127.0.0.1:8001/wall`.

Beim Erststart setzt du das Admin-Passwort und den Einrichtungs-Port. Ändert sich der Port, startet der Server neu; die Seite wartet mit Timer und Link auf die neue Adresse. Ein Projekt ist optional und wird danach unter `/setup` angelegt. Passwort und Projekt-PINs werden als Argon2id-Hash gespeichert. `data/` und `projects/` entstehen lokal und gehören nicht ins Git.

Je Projekt: Modus **Network** (LAN-IP und Port, HTTP) oder **Public** (Domain oder IP, optional HTTPS-URLs hinter Reverse-Proxy).

Dauerbetrieb unter systemd: `deploy/photo-frame.service`. Details in `TECHNICAL.md`.

---

## Funktionen

- Projekte mit eigener Config, Medien, PIN, eigenem Port; Start/Stop unter `/setup`; Config als ZIP laden/exportieren (`config.json` und Hintergründe)
- Medienspeicher im Projektordner oder in einem Ordner/Netzlaufwerk
- QR-Code zur Upload-Seite gemäß Projekt-Netzwerkmodus
- PIN-geschützter Medienbrowser: Mehrfachauswahl, Verstecken, Löschen, ZIP-Download
- Wall: Fly-Modus und Grid-Modus; Admin mit Reitern, vorherige Ansicht unter `/admin/classic`; Fly-Spawn Bahnen, Burst oder Zufall
- Upload-Seite: mehrzeilige Begrüßung, Header-Bild mit Upload und Drehung
- WebSocket-Aktualisierung bei Uploads
- Serverseitiges Bild-Skalieren; Videos mit ffmpeg nach H.264/AAC

---

## Dokumentation

- `TECHNICAL.md` — Schnittstellen, Ports, Betrieb

---

## Lizenz

MIT
