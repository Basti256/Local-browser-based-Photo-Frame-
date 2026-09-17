# Technische Beschreibung

Handbuch der Software. Funktionen, Schnittstellen, Ports, Betrieb.
Keine personenbezogenen Daten. Keine Zugangsdaten.

Version des beschriebenen Stands: 2.27.0

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

Ein Serverprozess. Alles hängt am Serverport: `/setup` und laufende Projekte unter `/{name}/…`. Keine zusätzlichen TCP-Ports je Projekt. Start/Stop schaltet nur, ob das Projekt unter seinem Pfad ausgeliefert wird.

```text
python -m server [--host HOST] [--port PORT]
```

Startskripte `start.sh` und `start.bat` rufen denselben Einstieg auf. Updates: unter `/setup` (prüfen / einspielen) oder `update.sh` / `update.bat` (fast-forward `main`, pip, optional systemd-Neustart).

Host ohne `--host`: `data/runtime.json` Feld `bind_host`, Standard `0.0.0.0`.
Port ohne `--port`: `data/runtime.json` Feld `port`, Standard 8000. Das ist der Serverport (`/setup` und alle Projektpfade).

Ändert die Erstkonfiguration oder `/setup` den Serverport gegenüber dem laufenden Prozess, speichert der Server den Port und startet sich in einem eigenen Thread neu (nicht über FastAPI-Background-Tasks). `python -m server` entfernt `PHOTO_FRAME_SKIP_RESTART`, falls es in der Umgebung steht. Die Browserseite wartet 10 Sekunden, prüft die neue Adresse und wiederholt das, bis sie erreichbar ist. Zusätzlich gibt es einen direkten Link. Unter systemd beendet der Prozess sich; `Restart=always` holt ihn mit dem neuen Port zurück. Ohne systemd wird ein neuer Prozess gestartet. Unter Windows wird der Nachfolgeprozess aus der Job-Gruppe der Konsole gelöst, damit er den alten Prozess überlebt.

Nach dem Neustart setzt der Prozess die in `running_projects` eingetragenen Projekte wieder auf laufend.

Bind-Adresse gilt nach diesem Neustart. Im LAN gilt `http://<lokale-IPv4>:<serverport>/{name}` für laufende Projekte (Network und Public). Auf dem Host der öffentlichen Adresse existiert `/{name}` nur im Modus `public` (sonst 404). Die öffentliche Adresse steht in der Runtime als Host plus Schema (`public_host`, `public_https`), Eingabe unter `/setup` als `https://…` oder `http://…`.

Wall, Upload und Admin eines Projekts sind nur erreichbar, solange das Projekt unter `/setup` gestartet ist. Mehrere Projekte gleichzeitig: derselbe Serverport, verschiedene Pfade. Einrichtung, Login und projektverwaltende APIs nur ohne Projekt-Prefix, nicht unter `/{name}/`.

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
│   ├── wall_manager/        # Wall-Manager-Originale (nicht Gäste-Medien)
│   ├── wall_manager_derived/
│   ├── wall_manager.json    # Playlist und Clip-Metadaten
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

Am Serverport im Modus `public`: `/{name}/wall`, `/{name}/upload`, `/{name}/admin` (LAN und öffentliche Adresse). Im Modus `network` gilt dasselbe nur über die LAN-Adresse; auf der öffentlichen Adresse 404. `/setup` ohne Projekt-Prefix.

---

## 5. Serverweite Dateien

Ablage unter `data/`. Nicht in der Versionskontrolle (nur leeres Verzeichnis mit `.gitkeep`).

| Datei | Inhalt |
|-------|--------|
| `runtime.json` | `port` (Serverport), `bind_host`, `active_project`, `running_projects`, `public_host`, `public_https`, `log_level`, `media_root` |
| `auth.json` | Benutzer `Admin`, Passwort-Hash. Kein Klartext-Passwort. |
| `secret.key` | Schlüssel für Session-Signatur |
| `login_lock.json` | Fehlversuche und Sperrzeit für Setup-Login und Erstkonfiguration |
| `app.log` | Protokoll der letzten 72 Stunden, ohne Passwörter oder PINs |
| `templates/<id>/` | Config-Vorlagen: `meta.json` (Name, Beschreibung), `config.json` (nur Wand-Schlüssel), optional `background/` und `header/` |
| `shared_backgrounds/` | Standardhintergründe für alle Projekte |

`projects/` ebenfalls lokal, nicht im Git (nur `.gitkeep`). Pro Projekt `config.json`, `access.json` (PIN-Hash, versiegelter Anzeigewert, Fehlzählung, Sperrzeit; keine Klartext-Ziffern), `media/`, `derived/`, `wall_manager/`, `wall_manager_derived/`, `wall_manager.json`, `header/`, `background/`. Die PIN-Anzeige erfolgt nur über `/api/setup/state` (Master).

---

## 6. Port und Bindung

| Parameter | Wert |
|-----------|------|
| Serverport | 8000 Standard, Feld `port` in Runtime |
| Protokoll der App | HTTP |
| TLS | nicht in der App. Bei Public-HTTPS: Reverse-Proxy. Schema steht in der öffentlichen Adresse. |

Firewall: unter Windows eingehende Regel für den Serverport. Unter Linux keine automatische Regel.

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
- Cookie `pf_admin`, HttpOnly, SameSite=Lax, gebunden an den Projektnamen, Path `/{name}`, 12 Stunden
- Logout: `GET /admin/logout`
- Nach Fehlversuch n: Wartezeit `min(3600, 2^n)` Sekunden (erster Fehler: 2 s). Während der Sperre keine PIN-Prüfung. Die Wartezeit gilt projektweit. Korrekter PIN setzt den Zähler zurück.
- Fehlt ein PIN (ältere Projekte): die Einrichtung erzeugt beim nächsten Laden einen neuen 4-stelligen PIN.

Zustandsändernde authentifizierte Anfragen: Header `Origin` muss zum Host der Anfrage passen (`Host` oder `X-Forwarded-Host`) oder fehlen. Das Schema darf abweichen (HTTPS am Reverse-Proxy, HTTP in der App).

### Geschützt (Master)

`/setup` nach Erststart. APIs: `/api/setup/state`, `/api/setup/logs`, `/api/setup/update`, `/api/setup/templates`, `/api/setup/backgrounds`, `/api/projects*`, `/api/runtime`, `/api/system`. `POST /api/login` mit Sperre nach Fehlversuchen.

### Geschützt (PIN)

`/admin` und `/admin/classic` (nach Freischalten). Optional nach Prozessneustart: `/admin/preview` (PIN, Dummy). `POST /api/config`, `/api/admin/stats`, `/api/network_test`, `/api/background/*`, `/api/header/list`, `/api/header/upload`, `/api/admin/templates`, `/api/admin/templates/apply`.

### Ungeschützt

`/upload` GET/POST, `/wall`, `/wall/grid`, `/ws`, `/media/*`, `/header/*`, `/background/*`, `/derived/*`, `/static/*`, `/sw.js`, `GET /api/config`, `GET /api/images`, `GET /api/upload_url`, `GET /api/upload_heartbeat`, `GET /api/version`, `GET /api/setup/status`, `GET /api/admin/pin-status`, `POST /api/setup/init` nur solange kein Master-Konto existiert. Die klickbare Attrappe der geplanten Projektseite liegt unter `GET /static/setup-preview.html` (ohne PIN, speichert nicht).

---

## 8. HTTP- und WebSocket-Schnittstellen

Basis: Serverport `http://<host>:<serverport>`. Reverse-Proxy spricht denselben Port. Öffentliche Pfade nutzen denselben Host plus `/{name}`.

Projektseiten, APIs, WebSocket, Medien und `sw.js` hängen unter `/{name}/…` (HTML setzt `meta name="pf-base"`). Ohne Prefix: `/setup`, Login, projektverwaltende APIs. Unter `/{name}/setup`, `/{name}/login`, `/{name}/logout` und den Control-APIs (`/api/setup`, `/api/projects`, `/api/runtime`, `/api/system`, `/api/login`, `/api/logout`, `/api/auth`) antwortet der Server mit HTTP 404 und leerem Körper.

### Seiten

| Methode | Pfad | Funktion |
|---------|------|----------|
| GET | `/` | Ohne Prefix: Umleitung auf `/setup`. Unter `/{name}`: Wall |
| GET | `/{name}/wall` | Fly oder Grid, wenn das Projekt läuft. Gestoppt: Hinweisseite. Unbekanntes erstes Segment: 404 ohne Körper. Modus `network` nur über private LAN-IP, localhost oder `*.local`; sonst 404 ohne Körper |
| GET | `/{name}/upload` | Gäste-Upload (Network nur LAN; Public auch öffentlich) |
| GET | `/{name}/admin` | Wand-Einstellungen, nach PIN. Reiter Wand / Texte / Upload / Wall Manager / System. Chrome: Hell / Dunkel / System (`localStorage` `pf-admin-theme`, nicht in `config.json`). Photowall-IA unverändert |
| GET | `/{name}/admin/classic` | Vorherige Admin-HTML, nach PIN |
| GET | `/static/setup-preview.html` | Klickbare Attrappe der geplanten Projekt-Einrichtung, ohne PIN. Datei unter `web/static/`. Speichert nicht. Derselbe Theme-Schalter wie `/admin`. Cockpit-Chrome (Lage/Ablauf) bleibt Attrappe. Die lebende Photowall-IA liegt unter `/admin` |
| GET | `/{name}/admin/preview` | Dieselbe Attrappe nach PIN, nur nach Prozessneustart (Route in `pages.py`). Optional |
| GET | `/{name}/admin/browser` | Medienbrowser, nach PIN |
| GET | `/{name}/admin/logout` | PIN-Sitzung löschen |
| GET | `/wall` | Ohne Prefix: Umleitung auf das einzige laufende Projekt (auf der öffentlichen Adresse nur Public) oder Hinweisseite |
| GET | `/upload` | Entsprechend Upload |
| GET | `/admin` | Entsprechend Admin |
| GET | `/p/{name}/wall` | 302 auf `/{name}/wall` (Network auf öffentlicher Adresse: 404) |
| GET | `/p/{name}/upload` | Entsprechend Upload |
| GET | `/p/{name}/admin` | Entsprechend Admin |
| GET | `/p/{name}/browser` | Entsprechend Medienbrowser |
| GET | `/setup` | Erststart, Projekte (Karten zugeklappt: Links, URLs, Start/Stop, PIN-Taste), Server, Protokoll |
| GET | `/login` | Anmeldung als Admin |
| GET | `/logout` | Master-Session löschen |

`{name}` ist der Projektordner. URL-Groß/Kleinschreibung darf abweichen, wenn der Name intern eindeutig ist. Reservierte erste Pfadsegmente, die kein Projekt sein dürfen: `setup`, `login`, `logout`, `admin`, `wall`, `upload`, `api`, `media`, `derived`, `header`, `background`, `p`, `ws`, `static`, `assets` (plus `sw.js`, `favicon.ico`, `robots.txt`).

Pfade ohne passende Route (inkl. `/docs`, `/openapi.json`, `/irgendetwas`) antworten mit HTTP 404 und leerem Körper. Kein JSON `Not Found`, keine Hinweis-HTML. API-Endpunkte, die eine bekannte Ressource nicht finden, behalten ihren Fehlertext.

Unter `/{name}/` gelten dieselben Projekt-APIs und Dateipfade wie ohne Prefix: `/ws`, `/api/config`, `/api/images`, `/api/version`, `/media/*`, `/derived/*`, `/header/*`, `/background/*`, `/sw.js`, `/wm/*`. Control-Pfade (Setup, Login, Runtime, System, Projekte starten/stoppen) sind unter Prefix nicht erreichbar (404 leer). Die Wall registriert den Service Worker unter `/{name}/sw.js` (Scope `/{name}/`).

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
| POST | `/api/runtime` | Master, Serverport, öffentliche Adresse, Medienordner, Log-Level |
| POST | `/api/projects` | Master, leeres Projekt anlegen |
| POST | `/api/projects/import` | Master, ZIP oder `config.json`; neues Projekt |
| GET | `/api/projects/{name}/export` | Master, ZIP nur Config und Hintergrund-/Header-Bilder |
| GET | `/api/setup/templates` | Master, Vorlagenliste |
| POST | `/api/setup/templates` | Master, ZIP oder `config.json` plus Name und Beschreibung |
| PATCH | `/api/setup/templates/{id}` | Master, Name/Beschreibung |
| DELETE | `/api/setup/templates/{id}` | Master |
| POST | `/api/projects/{name}/apply-template` | Master, Wand-Config der Vorlage auf das Projekt |
| GET | `/api/setup/backgrounds` | Master, Standardhintergründe |
| POST | `/api/setup/backgrounds` | Master, Bild hochladen |
| GET | `/api/setup/backgrounds/{datei}` | Master, Datei |
| DELETE | `/api/setup/backgrounds/{datei}` | Master |
| POST | `/api/projects/{name}/start` | Master |
| POST | `/api/projects/{name}/stop` | Master |
| DELETE | `/api/projects/{name}` | Master, Projektordner und Medien löschen |
| POST | `/api/projects/{name}/network` | Master |
| POST | `/api/projects/{name}/pin` | Master |
| GET | `/api/admin/media` | PIN |
| GET | `/api/header/list` | PIN |
| POST | `/api/header/upload` | PIN |
| GET | `/api/admin/media/archive` | PIN, ZIP der Originale |
| POST | `/api/admin/media/batch` | PIN, `hide` / `show` / `delete` |
| DELETE | `/api/admin/media/{datei}` | PIN |
| POST | `/api/admin/media/{datei}/hide` | PIN |
| POST | `/api/admin/wall-reload` | PIN, Wall-Seite neu laden (`__config_reload__`) |
| GET | `/api/admin/templates` | PIN, aktuelle Projekt-Wand plus serverweite Vorlagen (`data/templates`) |
| POST | `/api/admin/templates` | PIN, aktuelle Wand als serverweite Vorlage (nur Wand-Schlüssel, optional Projekthintergrund) |
| POST | `/api/admin/templates/apply` | PIN, Vorlage auf das laufende Projekt; nur Wand-Schlüssel, Upload/Netzwerk/PIN/Medien bleiben |
| GET/POST | `/api/config` | GET nein, POST PIN |
| POST | `/api/admin/unlock` | nein, mit Wartezeit |
| GET | `/api/admin/pin-status` | nein |
| GET | `/api/images` | nein |
| POST | `/upload` | nein |
| WS | `/ws` | nein, nur Wall-Ereignisse |
| GET | `/background/shared/{datei}` | nein, laufendes Projekt, serverweiter Hintergrund |
| GET | `/background/{datei}` | nein, laufendes Projekt |
| GET | `/sw.js` | nein |

---

## 9. Netzwerkmodi

Feld `network_mode` in `projects/<name>/config.json`. Zulässig: `network`, `public`. Die öffentliche Adresse steht in `data/runtime.json` (`public_host`, `public_https`; Eingabe mit `http://` oder `https://`).

| Wert | LAN `http://<private-IPv4>:<serverport>/{name}` | Öffentliche Adresse `https://<public_host>/{name}` |
|------|--------------------------------------------------|-----------------------------------------------------|
| `network` | ja | nein (404, der Pfad existiert nicht) |
| `public` | ja | ja |

Network gilt nur, wenn **jeder** gemeldete Host (`Host`, `X-Forwarded-Host`, `Forwarded`) eine private/loopback-IP, `localhost` oder `*.local` ist. Reicht der Proxy `X-Forwarded-Host: frame.example.com` durch, bleibt Network unsichtbar, auch wenn `Host` die LAN-IP des Backends ist.

Die Anwendung nimmt selbst nur HTTP entgegen. Das Schema der öffentlichen Adresse ändert ausschließlich die ausgegebenen URLs. QR-Code Upload im Public-Modus: `https://<host>/{name}/upload`. Reverse-Proxy nur auf den Serverport.

Lokale IPv4: UDP zu `8.8.8.8`. Externe IP nur als Fallback, wenn Public ohne Host.

---

## 10. Entfernt

Cloudflare-Tunnel und `cloudflared` sind nicht mehr Bestandteil.

---

## 11. Projektkonfiguration

Datei: `projects/<name>/config.json`. Fehlende Schlüssel werden aus Defaults ergänzt. Schreibzugriff auf die Wand-Config nur mit gültiger PIN-Sitzung. `POST /api/config` übernimmt `network_mode`, `public_host`, `public_https`, `public_base_url`, `storage_mode`, `storage_path` und `port` nicht; die setzt nur Setup (Master). `GET /api/config` liefert `storage_path` nicht. `wall_display_rotation` (0 / 90 / 180 / 270, Standard 0) dreht die gesamte Wall; Einstellung unter `/admin` Reiter Wand, Abschnitt Anzeige.

Export (`GET /api/projects/{name}/export`): ZIP mit `config.json` und Bildern aus `background/` sowie `header/`. Ohne `media/`, `derived/`, `hidden.json`, `access.json`. Import (`POST /api/projects/import`): legt ein neues Projekt an (neuer PIN). Übernimmt Wand-Schlüssel aus der Datei, nicht Setup-Schlüssel (Netzwerk, Speicher, Port). Optional Bilder aus `background/` und `header/` im ZIP. `config.json` darf im ZIP im Wurzelverzeichnis oder in einem Ordner liegen.

Vorlagen liegen serverweit unter `data/templates/`. Anlage unter `/setup` (Reiter Vorlagen): Upload derselben ZIP/`config.json` wie beim Projektexport, plus Name und Beschreibung. Unter `/admin` Wand: Liste inkl. „Aktuell“, Anwenden (`POST /api/admin/templates/apply`, nur Wand-Schlüssel, Hintergrunddatei der Vorlage wird kopiert, Header nicht) und „Aktuelle Wand als Vorlage“ (`POST /api/admin/templates`). Kein zweiter Speicher. Keine Netzwerk-, Speicher-, Port- oder PIN-Daten. Beim Anlegen eines Projekts optional eine Vorlage wählen; bestehende Projekte auch in den Kartendetails unter `/setup`. Setup-Anwenden kopiert weiterhin Hintergrund und Header.

Standardhintergründe unter `data/shared_backgrounds/`, Upload unter `/setup` (Reiter Vorlagen, Liste als kleine Vorschaubilder). In der Admin-Auswahlliste als `shared:<datei>` mit dem Zusatz „serverweit“. Die Wall und die Admin-Vorschau laden `GET /background/shared/{datei}` (nur bei laufendem Projekt). `GET /background/{datei}` bleibt für Projektdateien; ein Wert mit Präfix `shared:` wird ebenfalls aus dem serverweiten Ordner gelesen.

Projekt-Chrome (nicht die Gäste-Wand): Hell / Dunkel / System im Kopf, gespeichert als `localStorage` `pf-admin-theme` (nicht in `config.json`). Dieselbe Wahl gilt in dem Browser für `/admin`, PIN, Medienbrowser, `/upload` und `/static/setup-preview.html`. `/admin/classic` und `/setup` bleiben unverändert.

Bildtext der Gäste: Datei `media/<stem>.txt` neben dem Medium. Die Wall (Fly und Grid) lädt sie über `/media/<stem>.txt`, wenn `comments_enabled` gesetzt ist, und holt die Texte beim Laden der Medienliste vor. Darstellung (an, Farbe, Schrift, Größe, Fett, Unterstrichen) unter `/admin` Reiter Wand, Overlay. `comment_max_length` (1–500, Standard 80) steht unter `/admin` im Reiter Upload; die Upload-Seite setzt `maxlength`, kürzt beim Tippen und übernimmt den Wert nach dem Speichern ohne Neuladen. Der Server kürzt beim Speichern ebenfalls. Debug: `debug_random_comments` unter `/admin` (System → Debug, Auswahl An/Aus) füllt leere Bildtexte beim Upload mit Quatsch inkl. Smileys und Symbolen, begrenzt auf `comment_max_length`. Fortschritt auf der Upload-Seite: `upload_show_eta` und `upload_show_speed` (beide Standard aus, unter `/admin` Reiter Upload) ergänzen die Prozentanzeige um Restzeit (`4min 30s verbleibend`) bzw. Bitrate (`U: 256 kbit/s`, ab 1 Mbit/s in Mbit/s). QR und Banner ebenfalls unter Wand → Overlay; der Reiter Texte verweist dorthin. Media-Cache (aktivieren, TTL, Grenzen) unter Wand, Abschnitt Highlights / Cache.

### Medienspeicher

Serverweit unter `/setup` (Reiter Server), Feld `media_root` in `runtime.json`.

| `media_root` | Ort der Originale |
|--------------|-------------------|
| leer | `projects/<name>/media` |
| gesetzt | `<media_root>/<name>` |

Abgeleitete Dateien bleiben unter `projects/<name>/derived/`. Samba: Share als Ordner mounten oder UNC-Pfad als `media_root`. Nextcloud (WebDAV), FTP und SSH sind nicht als eigene Clients eingebaut. Ältere `storage_mode`/`storage_path` je Projekt gelten nur, solange `media_root` leer ist.

### Medienbrowser

Seite `/admin/browser`, PIN-Sitzung wie Admin. Übersicht, Mehrfachauswahl, Verstecken, Löschen, ZIP-Download aller Originale (`GET /api/admin/media/archive`, inkl. versteckter Dateien). Versteckte Dateien bleiben auf dem Speicher. `GET /api/images` listet sie nicht. Die Wall erhält den Dateinamen nicht per WebSocket (`__hide__:` entfernt bereits angezeigte Exemplare, ohne das Medium nachzuladen). Einblenden sendet den Namen wieder an die Wall. Sammelaktionen: `POST /api/admin/media/batch` in Paketen zu 40 Dateien; die Wall bekommt danach einmal `__media_sync__` und gleicht über `GET /api/images` ab, statt tausend Einzel-WebSocket-Nachrichten. Liste der versteckten Originalnamen: `projects/<name>/hidden.json`. Einbinden eines fremden Gallery-Prozesses entfällt; ein Prozess, ein Port.

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

Speichername Original: `{uuid}{endung}` in `media/`. HEIC und andere Nicht-JPEG werden nach JPEG konvertiert. POST `/upload` führt Validierung, JPEG-Verarbeitung und Transcode in einem Worker-Thread aus (`asyncio.to_thread`), damit parallele Uploads den Event-Loop nicht blockieren. Die Gäste-UI sendet bis zu vier Dateien gleichzeitig; ein Einzelfehler bricht die übrigen nicht ab. JPEG ohne EXIF-Drehung bleibt unverändert. Dateityp: MIME oder Endung. Auf `/upload` bleibt der Greeting-Text im Dunkel-Theme lesbar (Farbe folgt dem Chrome, wenn die konfigurierte Farbe untergeht).

Anschließend Derivat in `derived/`:

- Bild: JPEG, Kantenlänge begrenzt, Qualität aus Config
- Video: H.264/AAC MP4 via ffmpeg, optionales Poster. Fehlt ffmpeg, bleibt das Original die Anzeigedatei.

`GET /media/{datei}` liefert zuerst `derived/`, sonst `media/`. Originale werden nicht gelöscht. Fehlt `media/<stem>.txt` (Bildtext), antwortet der Server mit 204, nicht 404; das erscheint nicht im WARNING-Protokoll.

WebSocket sendet den Anzeigenamen nach dem Transcoding. Die Wall prüft die Serververbindung zusätzlich per `GET /api/config` alle 4 s (Abbruch nach 2,5 s) und verlangt in den letzten 15 s einen WebSocket-`__ping__`. `GET /api/version` reicht nicht, weil der Prozess nach Projekt-Stopp weiterlaufen kann. Beim Stopp eines Projekts werden offene `/ws`-Verbindungen geschlossen. Der erste `__ping__` setzt die Wall sofort auf online; der HTTP-Watchdog läuft weiter. Solange `/ws` noch CONNECTING ist oder noch kein Ping kam, gilt der Service Worker nicht als offline, damit `/media/` nicht mit 503 scheitert. Ohne HTTP-Antwort oder ohne frischen Ping nach zuvor bestätigter Verbindung gilt die Wall als offline (roter Punkt). Der Server sendet `__ping__` nach dem Accept, auf Stats und spätestens alle 8 s. Nach einem Verbindungsabbruch holt die Wall beim nächsten `/ws`-Open die Medienliste per `GET /api/images` nach: neue Dateien kommen in die Highlight-Queue (Fly) bzw. in den Pool (Grid), fehlende werden wie `__hide__:` entfernt. Die Highlight-Queue im Tab bleibt während der Trennung stehen und läuft weiter, sobald `serverOnline` wieder gilt. Die Slideshow spielt ohne offenes `/ws` ausschließlich aus dem Browser-Cache (`wall-media-v1`), sofern der Media-Cache aktiv ist. Der Cache füllt sich nur durch tatsächlich angezeigte `/media/`-Dateien (kein Vorabladen), bis `cache_max_images` / `cache_max_videos` / `cache_max_size_mb`, und nicht über den Browser-Quota (Safari enger; etwa 18 % Reserve plus Anteil für den Programm-Cache). Frische Einträge (innerhalb TTL) kommen aus dem Cache, ohne das Original erneut zu laden. Abgelaufene werden online neu geholt; ist der Cache voll, fliegen zuerst abgelaufene, dann ältere Dateien raus, nicht gerade angezeigte. Range-Anfragen (Videos) speichern keine 206-Teilstücke; eine volle Kopie liegt höchstens einmal in `wall-media-v1`. Wall-Manager-Clips liegen getrennt in `wall-program-v1` (`/wm/`, nie `/media/`). Bei verbundenem WebSocket lädt die Wall vom Server, bedient aber unexpired Cache-Treffer lokal. Im Debug-Overlay leert „Cache leeren“ nur den Foto-Cache der Wall, nicht den Programm-Cache. Debug zeigt TTL, Bild-/Video-/MB-Deckel und Quota.

---

## 13. Wall

Die gesamte Wall (Fly und Grid: Medien, Hintergrund, Banner, QR) lässt sich drehen: unter `/admin` Reiter Wand, Abschnitt Anzeige, Auswahl Horizontal 0° (Standard), Porträt 90°, Horizontal gedreht 180°, Porträt gedreht 270°. Wert `wall_display_rotation` in der Projekt-Config. Für Geräte ohne echten Hochkant-Modus. Der Verbindungsindikator (roter/grüner Punkt, oben rechts am Bildschirm) liegt außerhalb von `#wallStage` und dreht nicht mit. Offline bleibt der rote Punkt sichtbar. Das Debug-Overlay zeigt Verbindung, Cache-TTL, Anzahl der gecachten Bilder und Videos, den belegten Speicher und die Browser-Quota. `cache_ttl_minutes`: nach dieser Zeit ohne erfolgreichen Server-Abruf gilt ein Cache-Eintrag als veraltet; bei vollem Cache werden veraltete zuerst entfernt, offline bleiben sie als Fallback sichtbar. Die Wall-HTML kommt ohne Browser-Cache; `wall-rotate.js`/`wall-rotate.css` mit Versionsparameter, damit die alte Auswahl „Anzeige“ auf `/wall` nicht aus dem Cache bleibt. Fly-Medien liegen in `#wallStage` (nicht am `body`); Spawn, Flug, Entfernen und Debug-Bahnlinien rechnen in Bühnenkoordinaten, auch bei 90°/270°.

Fly: bewegte Medien. Spawn-Modus `spawn_mode`: `lanes` (Standard), `burst` oder `random`. Bahnen: `spawn_lane_count` (1–20, Standard 6), `spawn_lane_order` `random` / `random_apart` (Standard) / `adjacent`. Auswahl bevorzugt wenig genutzte Bahnen; nicht zweimal hintereinander dieselbe, und bei mindestens drei Bahnen kein A-B-A-Wechsel. `random_apart` meidet Nachbarn, weicht aber aus wenn sonst Bahnen leer bleiben. Belegte Bahnen werden nach Möglichkeit übersprungen; die äußeren Bahnen liegen um die halbe maximale Bild-/Videogröße (`image_max_size` / `video_max_size`) vom Rand. Burst: Sinus Mitte→rechts→Mitte→links in 0,1°-Schritten; `spawn_burst_period` ist die Dauer in Sekunden für einmal links nach rechts (Minimum und Schritt 0,1); die Bildmitte liegt auf der aktuellen Sinus-Position. Zufall: beliebige horizontale Position ohne Bahnen. Debug-Overlay: Bahnlinien im Modus `lanes`, wandernde Linie mit Winkel im Modus `burst`; bei einem Spawn wird die betreffende Linie 500 ms rot. Zusätzlich eine Auswahl „Debug drehen“ (nur diese Browser-Sitzung, nicht die Projekt-Config). Die Flugstrecke nach oben richtet sich nach der tatsächlichen Frame-Größe (inkl. Hochformat), nicht nur nach der Bildschirmhöhe. Bilder und Videos nutzen dieselbe Flug- und Rotationslogik; getrennte Config-Schlüssel (z. B. `image_rotation_strength` / `video_rotation_strength`) bei gleichen Werten also gleiches Verhalten. `video_playback_mode` (`once` / `loop` / `bounce`) betrifft nur das Abspielen im Frame. Fly startet das erste Bild und das erste Video sofort zusammen mit den Spawn-Intervallen. `image_spawn_interval` und `video_spawn_interval` sind Sekunden als Float (Minimum und Schritt 0,1); Speichern, Vorlagen und Import kürzen sie nicht zu `int`. `image_rotation_strength` und `video_rotation_strength` sind der Maximalwinkel in Grad (0 = keine Drehung). Banner-Text: `banner_align` (`left` / `center` / `right`), `banner_font`, Unterstreichen als `++Text++` im Markdown. Upload-Begrüßung ist Markdown (mehrere Zeilen, Fett/Kursiv/Überschrift) plus `upload_greeting_align`, `upload_greeting_font`, `upload_greeting_color`, `upload_greeting_size`, `upload_greeting_bold`, `upload_greeting_underline`. Header-Bild: Datei in `header/`, Auswahl und Upload unter `/admin`, Drehung `upload_image_rotation` (0/90/180/270) per CSS, Original unverändert. Polaroid-Rahmen (`frame_padding_*`) und Bildtext-Schrift wachsen mit der Medienbreite über 150 px Referenz (Faktor bis 2,5), damit der Text unter größeren Fotos lesbar bleibt. Grid: Spalten, Lauf von unten nach oben; dieselben Rahmenabstände, wenn Fotorahmen an sind. Die Einstellungen unter `/admin` liegen auf einer Seite (Fly- und Grid-Felder), gegliedert in Reiter Wand, Texte, Upload, Wall Manager und System. Ansicht Grid blendet die Fly-only-Blöcke Spawn/Bahnen und Größe/Bewegung aus (`display:none`, Werte bleiben im Formular und werden mitgespeichert); die Grid-Box (`grid_*`) erscheint nur bei Grid. Zahlenfelder in `/admin` (`load()`) übernehmen 0 (`??`), nicht den Formular-Default (`||`). Speichern lädt die aktuelle Config und setzt die bekannten Schlüssel; Felder anderer Reiter gehen dabei nicht verloren. Unter System → Debug lädt `POST /api/admin/wall-reload` (PIN) alle verbundenen Wall-Tabs neu (`__config_reload__` über `/ws`); ohne offene Verbindung bleibt die Wall unverändert. Die vorherige Admin-HTML bleibt unter `/admin/classic` (Fly oder Grid je nach `wall_view_mode`). `/admin/preview` ist eine PIN-geschützte klickbare Attrappe der geplanten Projekt-Einrichtung (Lage, Ablauf, Photowall, Upload, Betrieb, Debug); sie speichert nicht und ersetzt `/admin` nicht. Banner-Text ist Markdown; unter `/admin` wird er in einem WYSIWYG mit Live-Vorschau in 1/4 der Wall-Größe (Position, Höhe, Farben, Ausrichtung, Schrift) bearbeitet. Die Schriftgröße skaliert mit der Bannerhöhe und wird bei mehrzeiligem Text automatisch so verkleinert, dass alles in die Leiste passt, ohne einzelne Zeilen flachzudrücken. Enter im Editor erzeugt einen neuen Absatz; Überschriften gelten nur für die erste Zeile. Hintergrundbild: 90°-Drehung, Helligkeit, Kontrast, Position (mitte/oben/unten), Größe relativ zur Bildschirmfüllung, Deckkraft gegenüber der Hintergrundfarbe. Originaldatei unverändert. Die Admin-Vorschau unter Wand zeigt das gesamte Bild (höchstens 300 Pixel hoch, Seitenverhältnis erhalten), nicht den Wand-Zuschnitt. Position und Größe wirken auf der Wall. Service Worker cached `/media/*` bei aktiviertem Cache. Die Wall registriert ihn unter dem Projekt-Prefix (`/{name}/sw.js`, Scope `/{name}/`), damit TTL und `cache_max_*` der Projektconfig gelten; `/sw.js` ohne Prefix nutzt das einzige laufende Projekt, falls es genau eines gibt.

Client-Bibliotheken per CDN: QRCode.js, marked, Schriftarten.

---

## 13a. Wall Manager

Optionaler Ablauf über der unveränderten Photowall. Aus: heutige Dauer-Wall. Ein: Playlist aus Photowall-Slots, Videos und Bildern.

Dateien unter `wall_manager/` (Original) und `wall_manager_derived/` (Anzeige). Nicht in `media/`, nicht in `/api/images`. Metadaten `wall_manager.json`.

Anzeige: H.264/AAC MP4 bzw. JPEG, Kante höchstens 720p/1280, nie größer als die Quelle. `GET /wm/{datei}` (laufendes Projekt). Admin (PIN): `GET/PUT /api/admin/wall-manager`, `POST /api/admin/wall-manager/upload`, `DELETE /api/admin/wall-manager/asset/{id}`, `POST /api/admin/wall-manager/jump` (Playhead auf Playlist-Index), `GET /api/admin/wall-manager/playhead`. Wall: `GET /api/wall-manager`, `GET /api/wall-manager/playhead`. Nach Speichern `__wall_manager_updated__` über `/ws`. Playhead-Wechsel `__wm_playhead__`. Der Server führt den aktuellen Playlist-Index; Walls folgen (Poll ca. 300 ms plus WS). Fehlt der Playhead, spielt die Wall den Ablauf lokal und zeigt Debug „an“, nicht „aus“. Admin: Auswahl grün, laufender Punkt blau; Doppelklick springt (`POST /api/admin/wall-manager/jump` oder `PUT` mit `jump`). Playlist-Zeilen zeigen links neben Löschen die Laufzeit `vergangen/gesamt` (z. B. `0:30/1:00`); über der Liste steht die Anzahl offener Wall-WebSockets (`n Verb. aktiv`). Admin-Playhead und Admin-GET liefern `wall_clients`.

Photowall-Zeile: Dauer in Minuten, am Anfang `start` oder `resume`, am Ende `pause` oder `stop`, `photowall_preload_sec` (Standard 15): Start unter dem vorherigen Clip. Clip: `once` / `loop` / `repeat`. Effekt-Zeilen `kind: effect` schlank `{id,kind,effect,duration_sec}` (Wischblende zusätzlich `direction`, Standard `ltr`): `fade` (Dauer `duration_sec`, Standard 5, gilt für Aus- und Einblenden je einmal; Playhead-Länge 2×), `dissolve` (Weiche Blende, Überblendung ohne Schwarz, Playhead-Länge 1× `duration_sec`), `wipe` (Wischblende per CSS `clip-path`, Standard links nach rechts; optional `rtl` / `ttb` / `btt`; Playhead-Länge 1×), `pop` (Playhead-Länge 0,85 s; Folgemedium bleibt nach der Animation im DOM, kein Drop nach `endOverlap`), `cut` (Harter Schnitt, vorheriges Medium weg, nächstes sofort; Playhead-Länge 0,05 s). Der Playhead bleibt auf Schnitt/Pop für diese Occupancy, statt den Slot zu überspringen. Fade: schwarze Ebene über dem vorherigen Clip (CSS-Opacity, vorheriges Medium bleibt bis zum Ende des Ausblendens im DOM); das nächste Medium wartet kurz auf ein dekodiertes Bild und hält bei t=0, bis der Playhead den Clip erreicht. Dissolve: vorheriges und nächstes Medium liegen gleichzeitig in `#wmStage`, Opazitäten kreuzen sich über `duration_sec`. Wipe: nächstes Medium wird geometrisch aufgedeckt; der Fortschritt läuft über `requestAnimationFrame` über `duration_sec`. Photowall `pause`/`stop` am Slotende gilt auch, wenn als Nächstes ein Effekt kommt. Cache-Blobs tragen MIME; `clearStage` widerruft keine Blob-URL, die das nächste Medium gerade setzt. Neue Effektarten in `EFFECTS` brauchen einen Prozessneustart, bevor PUT sie behält; die Wand reicht Hard-Reload. Beginnt der Ablauf mit einem Clip (kein Fade davor), spielt das Medium sofort, die schwarze Ebene bleibt bei Opacity 0. Derselbe Clip wird nicht neu eingehängt, solange er schon lädt oder spielt. Overlay `#wmLayer` ist `position: fixed` über der Photowall; Admin-Theme-CSS gilt nicht auf `/wall`. Alte Playlists mit `transition` am Medium werden als Effekt-Zeilen gelesen. Photowall-Zeilen, die ein früherer Save als 12 min / `enter: start` / `exit: pause` / `transition: fade|pop` geschrieben hat, werden wieder als Effekt gelesen und so gespeichert. Echte Photowall-Slots mit anderer Dauer oder `resume`/`stop` bleiben Photowall. Banner und QR je Clip. Ton an, Mute global oder je Video. Vorladen `next` oder `all` in `wall-program-v1` (eigenes Limit, höchstens 16 Dateien, eigener Quota-Anteil; `all` nur während Photowall und nur nacheinander, bis der Deckel voll ist). Der Programm-Cache rührt `wall-media-v1` nicht an; verwaiste Clips fliegen zuerst raus, aktueller und nächster Clip bleiben. Debug zeigt Programm-Cache, Dateianzahl und Quota. Autoplay mit Ton: einmal tippen (`#wmTap`). Admin: Plus-Menü, Drag-and-drop, rechte Einstellungsleiste, 200×200-Vorschau des gewählten Mediums vollständig im Rahmen (`object-fit: contain`; Bild bzw. stumm laufendes Video) neben Dropdown aller Dateien, Löschen und Vergrößern.

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
