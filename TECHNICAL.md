# Technische Beschreibung

Handbuch der Software. Funktionen, Schnittstellen, Ports, Betrieb.
Keine personenbezogenen Daten. Keine Zugangsdaten.

Version des beschriebenen Stands: 2.17.1

---

## 1. Zweck

Die Software betreibt einen Foto-Rahmen im Browser.

Gäste laden Bilder und Videos. Eine Wall zeigt die Medien. Einrichtung, Projektwahl und Administration erfolgen im Browser nach Anmeldung.

---

## 2. Laufzeitumgebung

| Bestandteil | Wert |
|-------------|------|
| Sprache | Python 3.10+ |
| Web-Framework | FastAPI |
| ASGI-Server | Uvicorn |
| Oberfläche | HTML/CSS/JS unter `web/` |
| Betriebssystem | Windows, Linux (Debian) |
| Passwort-Hash | Argon2id (`argon2-cffi`) |
| Session | signiertes Cookie (`itsdangerous`) |
| Bildverarbeitung | Pillow, pillow-heif |
| Video-Transcoding | ffmpeg, optional |

Python-Pakete: siehe `requirements.txt`.

---

## 3. Prozessmodell

Ein Serverprozess. Die Einrichtung hängt am Steuer-Port. Derselbe Port liefert laufende Projekte unter `/{name}/…`. Zusätzlich bekommt jedes gestartete Projekt einen eigenen TCP-Port für den LAN-Zugriff (weiterer Uvicorn-Listener, gleicher Prozess, ohne zweiten Lifespan).

```text
python -m server [--host HOST] [--port PORT]
```

Startskripte `start.sh` und `start.bat` rufen denselben Einstieg auf. Updates: unter `/setup` (prüfen / einspielen) oder `update.sh` / `update.bat` (fast-forward `main`, pip, optional systemd-Neustart).

Host ohne `--host`: `data/runtime.json` Feld `bind_host`, Standard `0.0.0.0`.
Port ohne `--port`: `data/runtime.json` Feld `port`, Standard 8000. Das ist der Einrichtungs-Port (`/setup`).

Ändert die Erstkonfiguration oder `/setup` den Einrichtungs-Port gegenüber dem laufenden Prozess, speichert der Server den Port und startet sich in einem eigenen Thread neu (nicht über FastAPI-Background-Tasks). `python -m server` entfernt `PHOTO_FRAME_SKIP_RESTART`, falls es in der Umgebung steht. Die Browserseite wartet 10 Sekunden, prüft die neue Adresse und wiederholt das, bis sie erreichbar ist. Zusätzlich gibt es einen direkten Link. Unter systemd beendet der Prozess sich; `Restart=always` holt ihn mit dem neuen Port zurück. Ohne systemd wird ein neuer Prozess gestartet. Unter Windows wird der Nachfolgeprozess aus der Job-Gruppe der Konsole gelöst, damit er den alten Prozess überlebt.

Nach dem Neustart startet der Prozess die in `running_projects` eingetragenen Projekte wieder.

Bind-Adresse gilt nach diesem Neustart. Die Anzeige-URL (QR-Code) im Modus `network` nutzt nur den Projekt-Port. `/{name}` am Steuer-Port existiert in diesem Modus nicht. Im Modus `public` gilt die serverweite Domain (`public_host` in der Runtime) plus `/{name}` am Steuer-Port, ohne Projekt-Port.

Wall, Upload und Admin eines Projekts sind nur erreichbar, solange das Projekt unter `/setup` gestartet ist. Mehrere Projekte gleichzeitig: am Steuer-Port über verschiedene Pfade, im LAN je auf dem Projekt-Port. Einrichtung, Login und projektverwaltende APIs nur auf dem Steuer-Port, nicht unter `/{name}/`.

---

## 4. Verzeichnisstruktur

```
.
├── data/                    # Runtime, Auth-Hash, Session-Secret (nicht öffentlich beschreiben mit Inhalten)
├── deploy/photo-frame.service
├── projects/<name>/
│   ├── config.json
│   ├── access.json          # PIN-Hash, nicht öffentlich ausliefern
│   ├── media/               # Originale
│   ├── derived/             # Anzeige-Derivate
│   ├── header/
│   └── background/
├── server/                  # Python-Backend
├── web/                     # HTML/CSS/JS
│   ├── admin/
│   ├── login/
│   ├── setup/
│   ├── upload/
│   ├── wall/
│   └── static/
├── requirements.txt
├── start.sh
├── start.bat
├── update.sh
├── update.bat
└── TECHNICAL.md
```

`network_mode` `local`, `internal` → `network`. `tunnel` → `public`.

Am Steuer-Port im Modus `public`: `/{name}/wall`, `/{name}/upload`, `/{name}/admin`. Im Modus `network` existiert dieser Pfad nicht (404). Am Projekt-Port: `/wall` ohne Prefix. `/setup` nur am Steuer-Port.

---

## 5. Serverweite Dateien

Ablage unter `data/`. Nicht in der Versionskontrolle (nur leeres Verzeichnis mit `.gitkeep`).

| Datei | Inhalt |
|-------|--------|
| `runtime.json` | `port` (Einrichtung), `bind_host`, `active_project`, `running_projects`, `public_host`, `public_https`, `log_level` |
| `auth.json` | Benutzer `Admin`, Passwort-Hash. Kein Klartext-Passwort. |
| `secret.key` | Schlüssel für Session-Signatur |
| `login_lock.json` | Fehlversuche und Sperrzeit für Setup-Login und Erstkonfiguration |
| `app.log` | Protokoll der letzten 72 Stunden, ohne Passwörter oder PINs |

`projects/` ebenfalls lokal, nicht im Git (nur `.gitkeep`). Pro Projekt `config.json`, `access.json` (PIN-Hash, versiegelter Anzeigewert, Fehlzählung, Sperrzeit; keine Klartext-Ziffern), `media/`, `derived/`, `header/`, `background/`. Die PIN-Anzeige erfolgt nur über `/api/setup/state` (Master).

---

## 6. Port und Bindung

| Parameter | Wert |
|-----------|------|
| Einrichtungs-Port | 8000 Standard, Feld `port` in Runtime |
| Projekt-Port | Feld `port` in `projects/<name>/config.json`. Beim Anlegen automatisch eindeutig. |
| Protokoll der App | HTTP |
| TLS | nicht in der App. Bei Public-HTTPS: Reverse-Proxy. |

Firewall: unter Windows eingehende Regel je geöffnetem Port (Einrichtung und jedes gestartete Projekt). Unter Linux keine automatische Regel.

---

## 7. Authentifizierung

Zwei getrennte Zugänge.

### Master-Konto (Einrichtung)

Gilt für `/setup` und projektverwaltende APIs. Es gibt genau ein Konto `Admin`. Erststart: `GET /setup` und `POST /api/setup/init` ohne Session. Init setzt das Passwort und optional den Listen-Port. Ein Projekt ist dabei nicht nötig.

- Login: `GET /login`, `POST /api/login` (nur Passwort)
- Logout: `GET /logout`, `POST /api/logout`
- Cookie `pf_session`, HttpOnly, SameSite=Lax, Secure bei HTTPS, Path `/`, 7 Tage
- Fehlversuche Login und PIN: Wartezeit `min(3600, 2^n)` Sekunden. Während der Sperre keine Passwort- oder PIN-Prüfung. Die Einrichtung zeigt die Sperre inkl. Restzeit.
- Passwort: mindestens 10 Zeichen, ungleich `Admin`, Speicherung Argon2id

### Admin-PIN (Projekt)

Gilt für `/admin` und schreibende Admin-APIs des aktiven Projekts. Beim Anlegen eines Projekts wird ein zufälliger 4-stelliger PIN erzeugt. Die Ziffern sieht nur die Einrichtungsseite (`/setup`, Master-Session). Prüfung weiterhin Argon2id. In `access.json` liegt der Hash und ein versiegelter Anzeigewert, keine Klartext-Ziffernfolge. Ein anderer PIN (4–10 Ziffern) kann unter `/setup` gesetzt werden.

- Freischalten: `POST /api/admin/unlock`
- Cookie `pf_admin`, HttpOnly, SameSite=Lax, gebunden an den Projektnamen, Path `/{name}` am Steuer-Port bzw. `/` am Projekt-Port, 12 Stunden
- Logout: `GET /admin/logout`
- Nach Fehlversuch n: Wartezeit `min(3600, 2^n)` Sekunden (erster Fehler: 2 s). Während der Sperre keine PIN-Prüfung. Die Wartezeit gilt projektweit. Korrekter PIN setzt den Zähler zurück.
- Fehlt ein PIN (ältere Projekte): die Einrichtung erzeugt beim nächsten Laden einen neuen 4-stelligen PIN.

Zustandsändernde authentifizierte Anfragen: Header `Origin` muss zum Host der Anfrage passen (`Host` oder `X-Forwarded-Host`) oder fehlen. Das Schema darf abweichen (HTTPS am Reverse-Proxy, HTTP in der App).

### Geschützt (Master)

`/setup` nach Erststart. APIs: `/api/setup/state`, `/api/setup/logs`, `/api/setup/update`, `/api/projects*`, `/api/runtime`, `/api/system`. `POST /api/login` mit Sperre nach Fehlversuchen.

### Geschützt (PIN)

`/admin` und `/admin/classic` (nach Freischalten). `POST /api/config`, `/api/admin/stats`, `/api/network_test`, `/api/background/*`, `/api/header/list`, `/api/header/upload`.

### Ungeschützt

`/upload` GET/POST, `/wall`, `/wall/grid`, `/ws`, `/media/*`, `/header/*`, `/background/*`, `/derived/*`, `/sw.js`, `GET /api/config`, `GET /api/images`, `GET /api/upload_url`, `GET /api/upload_heartbeat`, `GET /api/version`, `GET /api/setup/status`, `GET /api/admin/pin-status`, `POST /api/setup/init` nur solange kein Master-Konto existiert.

---

## 8. HTTP- und WebSocket-Schnittstellen

Basis: Steuer-Port `http://<host>:<steuer-port>`. Reverse-Proxy/Tunnel spricht nur diesen Port. Öffentliche Pfade nutzen denselben Host.

Projektseiten, APIs, WebSocket, Medien und `sw.js` hängen am Steuer-Port nur im Modus `public` unter `/{name}/…` (HTML setzt `meta name="pf-base"`). Am LAN-Projekt-Port dieselben Pfade ohne Prefix.

### Seiten

| Methode | Pfad | Funktion |
|---------|------|----------|
| GET | `/` | Am Steuer-Port: Umleitung auf `/setup`. Am Projekt-Port oder unter `/{name}`: Wall |
| GET | `/{name}/wall` | Nur Modus `public` am Steuer-Port. Fly oder Grid, wenn das Projekt läuft. Gestoppt: Hinweisseite. Unbekannt oder Modus `network`: 404 |
| GET | `/{name}/upload` | Gäste-Upload (nur `public` am Steuer-Port) |
| GET | `/{name}/admin` | Wand-Einstellungen, nach PIN |
| GET | `/{name}/admin/classic` | Vorherige Admin-HTML, nach PIN |
| GET | `/{name}/admin/browser` | Medienbrowser, nach PIN |
| GET | `/{name}/admin/logout` | PIN-Sitzung löschen |
| GET | `/wall` | Am Projekt-Port: Wall. Am Steuer-Port ohne Prefix: Umleitung auf das einzige laufende Public-Projekt oder Hinweisseite |
| GET | `/upload` | Am Projekt-Port: Upload |
| GET | `/admin` | Am Projekt-Port: Admin |
| GET | `/p/{name}/wall` | Modus `public`: 302 auf `/{name}/wall`. Modus `network`: 404 |
| GET | `/p/{name}/upload` | Entsprechend Upload |
| GET | `/p/{name}/admin` | Entsprechend Admin |
| GET | `/p/{name}/browser` | Entsprechend Medienbrowser |
| GET | `/setup` | Erststart, Projekte, Protokoll |
| GET | `/login` | Anmeldung als Admin |
| GET | `/logout` | Master-Session löschen |

`{name}` ist der Projektordner. URL-Groß/Kleinschreibung darf abweichen, wenn der Name intern eindeutig ist. Reservierte erste Pfadsegmente, die kein Projekt sein dürfen: `setup`, `login`, `logout`, `admin`, `wall`, `upload`, `api`, `media`, `derived`, `header`, `background`, `p`, `ws`, `static`, `assets` (plus `sw.js`, `favicon.ico`, `robots.txt`).

Unter `/{name}/` gelten dieselben APIs und Dateipfade wie ohne Prefix: `/ws`, `/api/*`, `/media/*`, `/derived/*`, `/header/*`, `/background/*`, `/sw.js`.

### API (Auswahl)

| Methode | Pfad | Auth |
|---------|------|------|
| GET | `/api/version` | nein |
| GET | `/api/auth/status` | nein |
| GET | `/api/setup/status` | nein |
| POST | `/api/setup/init` | nur Erststart |
| POST | `/api/login` | nein |
| POST | `/api/logout` | Session |
| GET | `/api/setup/state` | Master |
| GET | `/api/setup/logs` | Master, Protokolltext |
| DELETE | `/api/setup/logs` | Master, leeren |
| GET | `/api/setup/logs/download` | Master, Datei |
| POST | `/api/setup/update/check` | Master, Stand von `origin/main` |
| POST | `/api/setup/update` | Master, fast-forward, pip, Neustart |
| POST | `/api/runtime` | Master, Port, öffentliche Adresse, Log-Level |
| POST | `/api/projects` | Master, leeres Projekt anlegen |
| POST | `/api/projects/import` | Master, ZIP oder `config.json`; neues Projekt |
| GET | `/api/projects/{name}/export` | Master, ZIP nur Config und Hintergrund-/Header-Bilder |
| POST | `/api/projects/{name}/start` | Master |
| POST | `/api/projects/{name}/stop` | Master |
| POST | `/api/projects/{name}/port` | Master |
| POST | `/api/projects/{name}/network` | Master |
| POST | `/api/projects/{name}/storage` | Master |
| GET | `/api/admin/media` | PIN |
| GET | `/api/header/list` | PIN |
| POST | `/api/header/upload` | PIN |
| GET | `/api/admin/media/archive` | PIN, ZIP der Originale |
| POST | `/api/admin/media/batch` | PIN, `hide` / `show` / `delete` |
| DELETE | `/api/admin/media/{datei}` | PIN |
| POST | `/api/admin/media/{datei}/hide` | PIN |
| GET/POST | `/api/config` | GET nein, POST PIN |
| POST | `/api/admin/unlock` | nein, mit Wartezeit |
| GET | `/api/admin/pin-status` | nein |
| GET | `/api/images` | nein |
| POST | `/upload` | nein |
| WS | `/ws` | nein, nur Wall-Ereignisse |
| GET | `/sw.js` | nein |

---

## 9. Netzwerkmodi

Feld `network_mode` in `projects/<name>/config.json`. Zulässig: `network`, `public`. Die Domain steht in `data/runtime.json` (`public_host`, `public_https`).

| Wert | Anzeige-URL (QR, Links) | Steuer-Port `/{name}` |
|------|-------------------------|------------------------|
| `network` | `http://<lokale-IPv4>:<projekt-port>` | existiert nicht (404) |
| `public` | `https://<public_host>/{name}` bzw. `http://<public_host>/{name}` | ausliefern |

Die Anwendung nimmt selbst nur HTTP entgegen. Der Schalter HTTPS ändert ausschließlich die ausgegebenen URLs. QR-Code Upload im Public-Modus: `https://<host>/{name}/upload`. Reverse-Proxy nur auf den Steuer-Port.

Lokale IPv4: UDP zu `8.8.8.8`. Externe IP nur als Fallback, wenn Public ohne Host.

---

## 10. Entfernt

Cloudflare-Tunnel und `cloudflared` sind nicht mehr Bestandteil.

---

## 11. Projektkonfiguration

Datei: `projects/<name>/config.json`. Fehlende Schlüssel werden aus Defaults ergänzt. Schreibzugriff auf die Wand-Config nur mit gültiger PIN-Sitzung. `POST /api/config` übernimmt `network_mode`, `public_host`, `public_https`, `public_base_url`, `storage_mode`, `storage_path` und `port` nicht; die setzt nur Setup (Master). `GET /api/config` liefert `storage_path` nicht.

Export (`GET /api/projects/{name}/export`): ZIP mit `config.json` und Bildern aus `background/` sowie `header/`. Ohne `media/`, `derived/`, `hidden.json`, `access.json`. Import (`POST /api/projects/import`): legt ein neues Projekt an (neuer Port, neuer PIN). Übernimmt Wand-Schlüssel aus der Datei, nicht Setup-Schlüssel (Netzwerk, Speicher, Port). Optional Bilder aus `background/` und `header/` im ZIP. `config.json` darf im ZIP im Wurzelverzeichnis oder in einem Ordner liegen.

Bildtext der Gäste: Datei `media/<stem>.txt` neben dem Medium. Die Wall (Fly und Grid) lädt sie über `/media/<stem>.txt`, wenn `comments_enabled` gesetzt ist. Schriftart unter `/admin` als Auswahlliste.

### Medienspeicher

`storage_mode`:

| Wert | Ort der Originale |
|------|-------------------|
| `project` | `projects/<name>/media` |
| `folder` | Pfad in `storage_path` (lokal, UNC, Mount) |

Abgeleitete Dateien bleiben unter `projects/<name>/derived/`. Samba: Share als Ordner mounten oder UNC-Pfad. Nextcloud (WebDAV), FTP und SSH sind nicht als eigene Clients eingebaut.

### Medienbrowser

Seite `/admin/browser`, PIN-Sitzung wie Admin. Übersicht, Mehrfachauswahl, Verstecken, Löschen, ZIP-Download aller Originale (`GET /api/admin/media/archive`, inkl. versteckter Dateien). Versteckte Dateien bleiben auf dem Speicher. `GET /api/images` listet sie nicht. Die Wall erhält den Dateinamen nicht per WebSocket (`__hide__:` entfernt bereits angezeigte Exemplare, ohne das Medium nachzuladen). Einblenden sendet den Namen wieder an die Wall. Liste der versteckten Originalnamen: `projects/<name>/hidden.json`. Sammelaktionen: `POST /api/admin/media/batch`. Einbinden eines fremden Gallery-Prozesses entfällt; ein Prozess, mehrere Listener.

Transcoding-Schlüssel:

| Schlüssel | Default |
|-----------|---------|
| `transcode_enabled` | true |
| `transcode_image_max_edge` | 1920 |
| `transcode_image_quality` | 85 |
| `transcode_keep_original` | true |

---

## 12. Upload und Transcoding

Erlaubte Bilder: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.heic`, `.heif`.  
Erlaubte Videos: `.mp4`, `.mov`, `.webm`.

Speichername Original: `{uuid}{endung}` in `media/`. HEIC und andere Nicht-JPEG werden nach JPEG konvertiert.

Anschließend Derivat in `derived/`:

- Bild: JPEG, Kantenlänge begrenzt, Qualität aus Config
- Video: H.264/AAC MP4 via ffmpeg, optionales Poster. Fehlt ffmpeg, bleibt das Original die Anzeigedatei.

`GET /media/{datei}` liefert zuerst `derived/`, sonst `media/`. Originale werden nicht gelöscht.

WebSocket sendet den Anzeigenamen nach dem Transcoding.

---

## 13. Wall

Fly: bewegte Medien. Spawn-Modus `spawn_mode`: `lanes` (Standard), `burst` oder `random`. Bahnen: `spawn_lane_count` (1–20, Standard 6), `spawn_lane_order` `random` / `random_apart` (Standard) / `adjacent`; belegte Bahnen werden nach Möglichkeit übersprungen; die äußeren Bahnen liegen um die halbe maximale Bild-/Videogröße (`image_max_size` / `video_max_size`) vom Rand. Burst: Sinus Mitte→rechts→Mitte→links in 0,1°-Schritten; `spawn_burst_period` ist die Dauer in Sekunden für einmal links nach rechts (Minimum und Schritt 0,1); die Bildmitte liegt auf der aktuellen Sinus-Position. Zufall: beliebige horizontale Position ohne Bahnen. Debug-Overlay: Bahnlinien im Modus `lanes`, wandernde Linie mit Winkel im Modus `burst`; bei einem Spawn wird die betreffende Linie 500 ms rot. Die Flugstrecke nach oben richtet sich nach der tatsächlichen Frame-Größe (inkl. Hochformat), nicht nur nach der Bildschirmhöhe. Bilder und Videos nutzen dieselbe Flug- und Rotationslogik; getrennte Config-Schlüssel (z. B. `image_rotation_strength` / `video_rotation_strength`) bei gleichen Werten also gleiches Verhalten. `video_playback_mode` (`once` / `loop` / `bounce`) betrifft nur das Abspielen im Frame. `image_rotation_strength` und `video_rotation_strength` sind der Maximalwinkel in Grad (0 = keine Drehung). Banner-Text: `banner_align` (`left` / `center` / `right`), `banner_font`, Unterstreichen als `++Text++` im Markdown. Upload-Begrüßung ist Markdown (mehrere Zeilen, Fett/Kursiv/Überschrift) plus `upload_greeting_align`, `upload_greeting_font`, `upload_greeting_color`, `upload_greeting_size`, `upload_greeting_bold`, `upload_greeting_underline`. Header-Bild: Datei in `header/`, Auswahl und Upload unter `/admin`, Drehung `upload_image_rotation` (0/90/180/270) per CSS, Original unverändert. Grid: Spalten, Lauf von unten nach oben. Die Einstellungen unter `/admin` liegen auf einer Seite (Fly- und Grid-Felder), gegliedert in Reiter Wand, Texte, Upload und System. Speichern lädt die aktuelle Config und setzt die bekannten Schlüssel; Felder anderer Reiter gehen dabei nicht verloren. Die vorherige Admin-HTML bleibt unter `/admin/classic` (Fly oder Grid je nach `wall_view_mode`). Banner-Text ist Markdown; unter `/admin` wird er in einem WYSIWYG mit Live-Vorschau in 1/4 der Wall-Größe (Position, Höhe, Farben, Ausrichtung, Schrift) bearbeitet. Die Schriftgröße skaliert mit der Bannerhöhe und wird bei mehrzeiligem Text automatisch so verkleinert, dass alles in die Leiste passt, ohne einzelne Zeilen flachzudrücken. Enter im Editor erzeugt einen neuen Absatz; Überschriften gelten nur für die erste Zeile. Hintergrundbild: 90°-Drehung, Helligkeit, Kontrast, Position (mitte/oben/unten), Größe relativ zur Bildschirmfüllung, Deckkraft gegenüber der Hintergrundfarbe. Originaldatei unverändert. Service Worker cached `/media/*` bei aktiviertem Cache.

Client-Bibliotheken per CDN: QRCode.js, marked, Schriftarten.

---

## 14. Debian / systemd

Beispiel-Einheit: `deploy/photo-frame.service`.

Pfade in der Einheit sind Platzhalter (`/opt/photo-frame`). Anpassen:

- `WorkingDirectory`
- `ExecStart` auf den venv-Interpreter
- optional `User=`
- `Restart=always` (nötig, wenn der Prozess nach Portwechsel kontrolliert endet)

Aktivierung nach Kopie nach `/etc/systemd/system/`.

Internet: Master-Konto und Admin-PIN gelten unabhängig von TLS. Reverse-Proxy mit TLS für Public-HTTPS.

---

## 15. Updates

Auslieferung nur über Branch `main`. Kein Force-Push. `data/` und `projects/` sind lokal und bleiben beim Update erhalten.

Ablauf auf einem Live-System:

1. `git fetch origin` und `git checkout main` (einmalig, falls das Clone noch auf einem anderen Branch steht)
2. `git pull --ff-only origin main`
3. `venv/bin/pip install -r requirements.txt` (Windows: `venv\Scripts\pip.exe`)
4. Prozess neu starten: `sudo systemctl restart photo-frame`, sonst den laufenden Prozess beenden und `./start.sh` bzw. `start.bat`

`update.sh` und `update.bat` führen die Schritte 1–3 aus. `update.sh` startet den systemd-Dienst `photo-frame` neu, wenn er aktiv ist. Unter `/setup` (Master) gibt es dieselben Schritte: prüfen (`POST /api/setup/update/check`) und einspielen (`POST /api/setup/update`, danach Neustart).

`--ff-only` bricht ab, wenn auf dem Gerät lokale Commits von `origin/main` abweichen. Dann nicht mergen: lokalen Stand verwerfen oder auf einem Entwicklungsrechner arbeiten.

Neue ausgelieferte Version: `server/version.py`, README, dieses Handbuch, CHANGELOG. `MANIFEST.md` bleibt lokal und gehört nicht ins Repository.

---

## 16. Lizenz

MIT
