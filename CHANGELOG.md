# Changelog

Alle wesentlichen Änderungen am Local-browser-based-Photo-Frame werden in dieser Datei dokumentiert.

---

## [2.17.1] – 2026-09-07

### Behoben

- Setup-POST (Update, Log-Level, Runtime) hinter HTTPS/Reverse-Proxy: Herkunftsprüfung vergleicht den Host, nicht mehr `http` gegen `https`. Die Fehlermeldung steht direkt bei den Schaltflächen.

---

## [2.17.0] – 2026-09-07

### Neu

- Einrichtung: auf Updates prüfen und einspielen (origin/main, fast-forward, pip, Neustart). `data/` und `projects/` bleiben. Die Skripte `update.sh` / `update.bat` bleiben.

---

## [2.16.0] – 2026-09-07

### Neu

- Öffentliche Domain gilt serverweit unter `/setup`. Projekte im Modus Public nutzen sie plus `/{name}`; im Modus Network existiert `/{name}` am Steuer-Port nicht.
- Einrichtung: Umschalter lokale/öffentliche Links; öffentliche URL auch bei gestopptem Public-Projekt.
- Anmelde-Sperre für `/login` und Projekt-PIN mit Wartezeit; Hinweis unter `/setup`. Während der Sperre prüft der Server kein Passwort und keine PIN.
- Protokoll der letzten 72 Stunden unter `/setup` (lesen, leeren, herunterladen, Log-Level).

---

## [2.15.0] – 2026-09-07

### Neu

- Öffentliche Domain: laufende Projekte unter `/{name}/wall`, `/{name}/upload`, `/{name}/admin` am Steuer-Port, ohne Umleitung auf den Projekt-Port.
- GET `/` am Steuer-Port führt nach `/setup`. Legacy `/p/{name}/…` leitet auf `/{name}/…` um (gleicher Host).
- Public-QR und Public-Links nutzen nur Domain plus Pfad. LAN-Projekt-Port bleibt für Modus Network.
- Projektnamen, die mit Systempfaden kollidieren (`setup`, `admin`, `wall`, …), werden beim Anlegen abgelehnt.

### Geändert

- Admin-Cookie `pf_admin` gilt unter `/{name}` am Steuer-Port, damit die PIN je Projekt bleibt.

---

## [2.14.0] – 2026-09-07

### Neu

- Live-Update: `update.sh` / `update.bat` holen `main` per fast-forward, installieren Abhängigkeiten und starten unter Linux den Dienst `photo-frame`, falls er läuft. `data/` und `projects/` bleiben lokal.

---

## [2.13.2] – 2026-09-06

### Geändert

- Fly-Bahnen: die äußeren Bahnen bleiben um die halbe maximale Bildgröße vom Bildschirmrand, damit Frames vollständig sichtbar starten.

---

## [2.13.1] – 2026-09-06

### Behoben

- Burst: Bilder starten mit der Mitte auf der wandernden Debug-Linie (vorher die linke Kante, dadurch wirkten große Frames immer mittig).

### Geändert

- Debug: bei einem Spawn auf einer Bahn oder im Burst wird die Linie 500 ms rot.

---

## [2.13.0] – 2026-09-06

### Neu

- Fly-Wall: Spawn-Modus Bahnen, Burst oder Zufall. Burst schwingt als Sinus von der Mitte nach rechts und links in 0,1°-Schritten; die Geschwindigkeit (Sekunden für einmal links nach rechts) ist einstellbar, Minimum 0,1. Debug zeigt die aktuelle Burst-Position. Zufall ist wieder ohne Bahnen.

---

## [2.12.1] – 2026-09-06

### Neu

- Fly-Wall: bei aktivem Debug-Overlay vertikale Linien mit Nummern auf den Spawn-Bahnen.

---

## [2.12.0] – 2026-09-06

### Neu

- Fly-Wall: unter `/admin` (Slideshow) Anzahl der Bahnen (1–20) und Reihenfolge: Zufällig, Zufällig (niemals nebeneinander), Nebeneinander. Standard: 6 Bahnen, niemals nebeneinander. Gilt für Bilder und Videos.

---

## [2.11.3] – 2026-09-06

### Behoben

- Banner: neue Zeilen im Editor bleiben auf der Wall eigene Zeilen (Überschrift verschluckt Folgezeilen nicht mehr). Die letzte Zeile wird nicht mehr flachgequetscht.

---

## [2.11.2] – 2026-09-06

### Neu

- Banner und Upload-Begrüßung: Unterstreichen in der WYSIWYG-Leiste (Auswahl, nicht nur der ganze Block). Bildtext unter den Fotos behält die bestehende Option.

---

## [2.11.1] – 2026-09-06

### Geändert

- Admin-Banner-Vorschau erscheint in 1/4 der Wall-Größe (Leiste und Schrift). Die gespeicherte Bannerhöhe bleibt unverändert.

---

## [2.11.0] – 2026-09-06

### Neu

- Upload-Begrüßung unter `/admin` wie das Banner: mehrere Zeilen, WYSIWYG (Fett, Kursiv, Überschrift). Speicherung Markdown. Ausrichtung, Schrift, Farbe, Größe, Fett und Unterstrichen bleiben.
- Header-Bild: hochladen und aus der Liste wählen (wie Hintergrund), 90°-Drehung. Originaldatei unverändert.

---

## [2.10.0] – 2026-09-06

### Geändert

- `/admin` ist eine gemeinsame Einstellungsseite (Fly und Grid) mit Reitern Wand, Texte, Upload und System. Alle bisherigen Felder bleiben erhalten, inklusive der Grid-Rahmenabstände. Speichern schreibt die volle Config (erst laden, dann bekannte Schlüssel setzen).
- Die vorherige Admin-Ansicht bleibt unter `/admin/classic` erreichbar, bis die neue Ansicht freigegeben ist.

---

## [2.9.1] – 2026-09-06

### Behoben

- Fly-Wall: neue Bilder und Videos starten verteilt über die Breite (freie Spuren), statt sich per Zufall auf derselben Achse zu klumpen.

---

## [2.9.0] – 2026-09-06

### Neu

- Banner: Textausrichtung links/mittig/rechts und Schriftart-Dropdown (Vorschau in der gewählten Schrift).
- Upload-Seite: für den Begrüßungstext dieselben Textoptionen (Ausrichtung, Schriftart, Farbe, Größe, Fett, Unterstrichen).

---

## [2.8.2] – 2026-09-06

### Geändert

- Fly-Wall: Videos nutzen dieselbe Flugbahn und Rotation wie Bilder, sobald die jeweiligen Bewegungseinstellungen übereinstimmen. Loop und Bounce gelten nur noch für das Abspielen im Frame, nicht für eine eigene Wipp-Rotation oder eine feste 90-Sekunden-Flugzeit.

---

## [2.8.1] – 2026-09-06

### Behoben

- Fly-Wall: Bilder und Videos drehen nicht weiter als die eingestellte Rotation. Ursache war vor allem eine CSS-Transition (`all`), die nach dem Center-Highlight die Winkel-Animation über das Maximum hat schwingen lassen. Der Wert 0 bedeutet jetzt keine Rotation.

---

## [2.8.0] – 2026-09-06

### Neu

- `/setup`: neben Anlegen eine Konfiguration als ZIP oder `config.json` laden (neues Projekt, neuer Port, neuer PIN).
- Admin: Schriftart für den Bildtext als Dropdown; Name und Auswahl erscheinen in der jeweiligen Schrift.

### Geändert

- Projekt-Export enthält nur `config.json` sowie Bilder aus `background/` und `header/`. Keine Medien, kein `hidden.json`, kein `access.json`.

### Behoben

- Bildtext unter Fotos und Videos: die Wall lud `uuid.jpg.txt` statt `uuid.txt` (falsche Dateiendung im JavaScript). Anzeige auch im Grid-Modus.

---

## [2.7.0] – 2026-09-06

### Neu

- Hintergrundbild: 90°-Drehung, Helligkeit, Kontrast, Position (mitte/oben/unten), Größe und Deckkraft zur Hintergrundfarbe. Live-Vorschau unter `/admin`. Die Originaldatei bleibt unverändert.

---

## [2.6.2] – 2026-09-06

### Behoben

- Banner: mehrzeiliger Text wird verkleinert, bis er vollständig in der Leiste sichtbar ist (Admin-Vorschau und Wall).

---

## [2.6.1] – 2026-09-06

### Geändert

- Banner-Schriftgröße wächst und schrumpft proportional mit der Bannerhöhe (Vorschau und Wall).

---

## [2.6.0] – 2026-09-06

### Neu

- Admin: Banner-Text als WYSIWYG in einer Live-Vorschau (Position, Höhe, Farben), Speicherung weiter als Markdown.

---

## [2.5.1] – 2026-09-06

### Behoben

- Fly-Wall: Bilder und Videos bleiben nicht mehr am oberen Bildschirmrand hängen. Die Flugstrecke berücksichtigt die echte Frame-Höhe (Hochformat, große Anzeigegröße).

---

## [2.5.0] – 2026-09-06

### Neu

- Medienbrowser: mehrere Dateien markieren und gemeinsam verstecken, einblenden oder löschen.
- ZIP-Download aller Originalmedien.
- Serverende behält die Liste laufender Projekte für den nächsten Start.

---

## [2.4.0] – 2026-09-06

### Neu

- Medienbrowser: Verstecken. Die Datei bleibt gespeichert, die Wall listet und lädt sie nicht.

---

## [2.3.1] – 2026-09-06

### Behoben

- Medienbrowser: Schließen und Löschen nur noch in der Großansicht, nicht dauerhaft über der Übersicht.

---

## [2.3.0] – 2026-09-06

### Neu

- Projekte unter `/setup` einzeln starten und stoppen.
- Jedes laufende Projekt lauscht auf einem eigenen Port im selben Prozess.
- Mehrere Projekte gleichzeitig.

### Geändert

- Wall, Upload und Admin nur am Projekt-Port, solange das Projekt läuft.
- Anzeige-URLs nutzen den Projekt-Port.

---

## [2.2.0] – 2026-09-06

### Neu

- Wall, Upload, Admin und Medienbrowser je Projekt auf der Einrichtungsseite.
- PIN-geschützter Medienbrowser unter `/admin/browser`.
- Medienspeicher je Projekt: Projektordner oder externer Ordner/UNC/Mount.

---

## [2.1.5] – 2026-09-06

### Neu

- Beim Anlegen eines Projekts wird ein zufälliger 4-stelliger Admin-PIN erzeugt und unter `/setup` angezeigt.

---

## [2.1.4] – 2026-09-06

### Behoben

- Unter Windows starb der neu gestartete Prozess mit der alten Konsole. Neustart löst den Kindprozess aus der Job-Gruppe.

---

## [2.1.3] – 2026-09-06

### Behoben

- Portwechsel startete den Prozess nicht, wenn `PHOTO_FRAME_SKIP_RESTART` in der Umgebung stand. Der Serverstart ignoriert diese Variable jetzt. Neustart läuft in einem eigenen Thread.

---

## [2.1.2] – 2026-09-06

### Geändert

- Portwechsel in der Einrichtung startet den Server neu.
- Warteseite mit 10-Sekunden-Timer, Wiederholung und manuellem Link.

---

## [2.1.1] – 2026-09-06

### Geändert

- Erstsetup: festes Konto `Admin`, nur Passwort. Kein Pflichtprojekt.
- Listen-Port bereits in der Erstkonfiguration setzbar (gilt nach Neustart).
- Login nur noch mit Passwort.

---

## [2.1.0] – 2026-09-06

### Neu

- Master-Konto nur für `/setup`.
- Admin-PIN je Projekt, exponentielle Wartezeit nach Fehlversuchen.
- Netzwerkmodus je Projekt: Network (LAN HTTP) oder Public (Host, optional HTTPS-Anzeige-URLs).

### Entfernt

- Cloudflare-Tunnel und zugehörige APIs.

### Geändert

- Default-Bind `0.0.0.0`. Runtime ohne serverweiten Netzwerkmodus.
- Alte Modi `local`/`internal`/`tunnel` werden gemappt.

---

## [2.0.0] – 2026-09-06

### Neu

- Browser-Einrichtung unter `/setup` (Erstkonfiguration, Projekte, Netzwerk, Tunnel, Export).
- Anmeldung unter `/login`. Administrationskonto, Passwort als Argon2id-Hash.
- Session-Cookie, Rate-Limit für Login.
- Ein Serverprozess, Start über `python -m server`, `start.sh`, `start.bat`.
- Linux/Debian: kein Desktop erforderlich, systemd-Vorlage unter `deploy/`.
- Serverseitiges Transcoding: Bilder skaliert nach `derived/`, Videos mit ffmpeg nach MP4.

### Geändert

- HTML/CSS/JS liegen unter `web/`, nicht mehr als Python-Strings.
- `cloudflared` wird über PATH, `CLOUDFLARED_PATH` oder `bin/` gesucht.
- Firewall nur unter Windows; andere Systeme ohne Absturz.
- Upload-Dateinamen als UUID.
- Config-Schreiben nur bekannte Schlüssel, nur mit Session.
- Netzwerkmodus `internal` wird als `local` gelesen.

### Entfernt

- Tkinter-Desktop-GUI.
- PySide6-Abhängigkeit.
- Legacy-Router `server/routes/api.py`.

### Sicherheit

- Admin, Setup, Tunnel, Config-Schreiben und Hintergrund-Upload erfordern Session.
- Gäste-Upload und Wall bleiben ohne Login.
- Keine Klartext-Passwörter.

---

## [1.0.0] – 2025-03-15

### Erste stabile Version

Vollständige Umbenennung von Wedding Photo Frame zu Local-browser-based-Photo-Frame.
Versionierung eingeführt.

Hintergrund, Wake Lock, Center Highlight, Media-Cache wie zuvor beschrieben.
