# Changelog

Alle wesentlichen Änderungen am Local-browser-based-Photo-Frame werden in dieser Datei dokumentiert.

---

## [1.0.0] – 2025-03-15

### Erste stabile Version

Vollständige Umbenennung von Wedding Photo Frame zu Local-browser-based-Photo-Frame.
Versionierung eingeführt.

---

## [Unreleased] – 2025-03-15

### Neu

#### Hintergrund-Anpassung
- **Hintergrundfarbe oder Hintergrundbild** wählbar
- Neuer Bereich „Hintergrund“ in der Admin-UI (Extras)
- Modus: Farbe (mit Farbwähler) oder Bild
- **Hintergrundbild-Upload** direkt in der Admin-Seite
- Bilder werden im Projektordner `background/` gespeichert
- Unterstützte Formate: JPG, PNG, WebP, GIF (max. 20 MB)

#### Bildschirm wach halten
- **Wake Lock API** – verhindert Bildschirmschoner (Chrome, unterstützte Browser)
- **Alternative Wachfunktion** – Video-Fallback für Edge, Firefox und ältere Browser
- Verwendet `HTMLCanvasElement.captureStream()` – kein externes Video nötig
- Beide Optionen in Admin unter „Extras“ aktivierbar
- Debug-Overlay zeigt Status: „aktiv (Wake Lock)“ oder „aktiv (Alternative)“

#### Center Highlight – Entry/Exit Speed
- Einstellungen für Einblend- und Abfluggeschwindigkeit robuster
- Debug-Ausgabe bei aktiviertem Overlay: `center entry=Xms exit=Yms`
- Admin: Eingabefelder mit `type="number"`, min/max, Einheit „Sekunden“
- Hilfetexte präzisiert (z.B. „0.2 = schnell, 2 = langsam“)

### Verbessert

#### Highlight-Queue bei Verbindungsabbruch
- Queue wird **offline nicht mehr verarbeitet** – verhindert „Geister-Zähler“
- Bei **Reconnect** wird die Queue sofort weiter abgearbeitet
- Kein Festhängen mehr von Bildern in der Queue nach Wiederverbindung

#### Admin-UI
- **Extras**-Bereich unter Erweitert (Bildschirm wach halten, Alternative)
- Hintergrund-Einstellungen mit Upload und Vorschau
- Center Highlight: Entry/Exit Speed mit klaren Einheiten

### Technisch

- Neuer Ordner: `projects/<projekt>/background/`
- Neue API: `GET /api/background/list`, `POST /api/background/upload`
- Statische Dateien: `/background/<dateiname>`
- Config: `background_mode`, `background_color`, `background_image`
- Config: `screen_wake_lock_enabled`, `screen_wake_lock_alternative`

---

## Frühere Versionen

*(Ältere Änderungen wurden vor Einführung des Changelogs vorgenommen.)*
