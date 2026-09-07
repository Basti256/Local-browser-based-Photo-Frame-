# Local-browser-based-Photo-Frame

**Version 2.19.0**

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

Der Port 8000 ist der Serverport. **Public**-Projekte: `http://192.168.x.x:8000/<projekt>/wall` und `https://frame.example.com/<projekt>/wall`. **Network**-Projekte: nur die LAN-IP, auf der öffentlichen Domain existiert der Pfad nicht. Unter `/setup` Starten/Stoppen.

Beim Erststart setzt du das Admin-Passwort und den Serverport. Ändert sich der Port, startet der Server neu; die Seite wartet mit Timer und Link auf die neue Adresse. Ein Projekt ist optional und wird danach unter `/setup` angelegt. Passwort und Projekt-PINs werden als Argon2id-Hash gespeichert. `data/` und `projects/` entstehen lokal und gehören nicht ins Git.

Je Projekt: Modus **Network** (nur LAN unter `/{projekt}`; die öffentliche Domain kennt das Projekt nicht) oder **Public** (öffentliche Adresse unter `/setup` mit `https://` oder `http://`, Pfad `/{projekt}`). Bei Public-Projekten die Links lokal/öffentlich umschalten.

Dauerbetrieb unter systemd: `deploy/photo-frame.service`. Details in `TECHNICAL.md`.

---

## Update

Live-Systeme bleiben auf Branch `main`. `data/` und `projects/` gehören nicht ins Git und bleiben beim Update unangetastet. Unter `/setup` gibt es **Auf Updates prüfen** und **Aktualisieren**. Alternativ:

Linux:

```bash
chmod +x update.sh
./update.sh
```

Windows:

```bat
update.bat
```

Ohne Skript:

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
venv/bin/pip install -r requirements.txt
```

Danach den Server neu starten (`./start.sh` / `start.bat`, oder `sudo systemctl restart photo-frame`). `--ff-only` lehnt abweichende lokale Commits ab; auf dem Gerät nicht am Code arbeiten.

## Funktionen

- Projekte mit eigener Config, Medien, PIN; unter `/{name}/` am Serverport; Start/Stop und Löschen unter `/setup`; Config als ZIP laden/exportieren (`config.json` und Hintergründe)
- Config-Vorlagen und Standardhintergründe unter `/setup`, nutzbar in allen Projekten
- Medienspeicher serverweit (Ordner mit Unterverzeichnis je Projekt) oder im jeweiligen Projektordner
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
