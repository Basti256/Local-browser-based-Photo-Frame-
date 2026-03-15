"""
Admin-Route (Fly-Modus): Konfigurations- und Status-UI.

- GET /admin: Liefert Admin-HTML (Fly oder Grid je nach wall_view_mode)
- API: /api/config (GET/POST), /api/admin/stats, /api/network_test
- API: /api/background/list, /api/background/upload (Hintergrundbilder)
- Enthält das komplette Admin-HTML als String (_get_admin_fly_html)
"""
import socket
import os
import time
import json
import uuid
from server.network import get_network_info
from server import stats
from server.routes.wall import clients
from server.main import PROJECT_DIR, BACKGROUND_DIR
from server.routes.admin_grid import get_admin_grid_html
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse

router = APIRouter()

MEDIA_DIR = os.path.join(PROJECT_DIR, "media")
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
VIDEO_EXT = (".mp4", ".mov", ".webm")


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@router.get("/admin", response_class=HTMLResponse)
def admin():
    net = get_network_info()
    config = _load_config()
    if config.get("wall_view_mode") == "grid":
        return get_admin_grid_html(net)
    return _get_admin_fly_html(net)


def _get_admin_fly_html(net):
    return """

<!DOCTYPE html>
<html>

<head>

<title>Local-browser-based-Photo-Frame Admin</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>

<style>

body{
font-family:Arial;
padding:40px;
background:#f5f5f5;
}

.container{
background:white;
padding:30px;
border-radius:10px;
max-width:950px;
margin:auto;
box-shadow:0 5px 20px rgba(0,0,0,0.15);
}

h1{margin-top:0;}

.section{
border-top:1px solid #ddd;
margin-top:15px;
padding-top:10px;
}

.sectionHeader{
font-size:20px;
cursor:pointer;
display:flex;
justify-content:space-between;
align-items:center;
}

.sectionContent{
display:none;
margin-top:15px;
}

.sectionGroupTitle{
font-size:22px;
margin-top:25px;
margin-bottom:10px;
}

label{
font-weight:bold;
}

input,select,textarea{
width:100%;
padding:10px;
margin-top:5px;
margin-bottom:15px;
}

textarea{
height:120px;
resize:vertical;
}

.row{
display:flex;
align-items:center;
justify-content:space-between;
}

.checkbox{
width:auto;
transform:scale(1.3);
}

.help{
margin-left:8px;
cursor:pointer;
color:#2196F3;
font-weight:bold;
}

.helpText{
display:none;
background:#eef5ff;
padding:10px;
border-radius:6px;
margin-bottom:10px;
font-size:14px;
}

.sectionInfo{
background:#eef5ff;
padding:10px;
border-radius:6px;
margin-bottom:10px;
font-size:14px;
}

button{
background:#4CAF50;
color:white;
border:none;
padding:15px;
font-size:18px;
border-radius:8px;
width:100%;
margin-top:25px;
}

@media (max-width:600px){
#status_grid{grid-template-columns:1fr !important;}
}

</style>

</head>

<body>

<div class="container">

<h1>Local-browser-based-Photo-Frame Einstellungen <span id="app_version" style="font-size:0.5em;color:#666;font-weight:normal;"></span></h1>

<!-- Design -->

<h2 class="sectionGroupTitle">Design</h2>

<!-- Ansicht -->

<div class="section">

<div class="sectionHeader" onclick="toggleSection(this)">
Ansicht
<span>▼</span>
</div>

<div class="sectionContent">

<div id="help_view_mode" class="sectionInfo">
Wählt die Darstellungsart: Fliegende Bilder oder Grid. Nach dem Speichern werden Admin und Wall neu geladen.
</div>

<label>Design</label>
<select id="wall_view_mode">
<option value="fly">Fliegend (Bilder fliegen über den Bildschirm)</option>
<option value="grid">Grid (Bilder nebeneinander)</option>
</select>

<div id="grid_settings" style="margin-top:20px;padding-top:15px;border-top:1px solid #eee;display:none;">

<h3 style="margin-top:0;color:#333;">Grid-Einstellungen</h3>

<label>Spalten (gleichzeitig sichtbare Bilder)</label>
<input id="grid_columns" placeholder="4" type="number">

<label>Durchlaufzeit (Sekunden bis Bild oben verschwindet)</label>
<input id="grid_animation_duration" placeholder="8" type="number">

<label>Abstand zwischen Spalten (px)</label>
<input id="grid_spacing_columns" placeholder="20" type="number">

<label>Abstand zwischen Zeilen (px)</label>
<input id="grid_spacing_rows" placeholder="0" type="number">

<div class="row">
<label>Fotorahmen anzeigen</label>
<input type="checkbox" id="grid_show_frames" class="checkbox">
</div>

</div>

</div>
</div>


<!-- Slideshow -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Slideshow
<span>▼</span>
</div>
<div class="sectionContent">

<h3 style="margin-top:0;color:#333;">Slideshow Einstellungen Bilder</h3>
<label>Bild Intervall (Sekunden)</label>
<input id="spawn_interval" placeholder="6">
<label>Maximale Bilder gleichzeitig</label>
<input id="max_images" placeholder="10">
<label>Min Bildgröße (px)</label>
<input id="image_min" placeholder="100">
<label>Max Bildgröße (px)</label>
<input id="image_max" placeholder="150">

<h3 style="margin-top:20px;color:#333;">Slideshow Einstellungen Videos</h3>
<label>Max Videos gleichzeitig</label>
<input id="max_videos" placeholder="2">
<label>Video Intervall (Sekunden)</label>
<input id="video_interval" placeholder="10">
<label>Video Modus</label>
<select id="video_mode">
<option value="once">Einmal</option>
<option value="loop">Loop</option>
<option value="bounce">Bounce</option>
</select>
<label>Min Videogröße (px)</label>
<input id="video_min" placeholder="100">
<label>Max Videogröße (px)</label>
<input id="video_max" placeholder="150">

</div>
</div>


<!-- Bewegung -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Bewegung / Rotation
<span>▼</span>
</div>
<div class="sectionContent">

<h3 style="margin-top:0;color:#333;">Bewegung Einstellungen Bilder</h3>
<label>Flugmodus Bilder</label>
<select id="flight_path_mode_image">
<option value="random">Random Drift</option>
<option value="bounce">Bounce</option>
</select>
<label>Drift Stärke Bilder</label>
<input id="drift_strength_image" placeholder="0.2">
<label>Rotation Stärke Bilder</label>
<input id="rotation_image" placeholder="90">
<label>Rotation Richtung Bilder</label>
<select id="rotation_direction_image">
<option value="both">Beide</option>
<option value="left">Links</option>
<option value="right">Rechts</option>
</select>

<h3 style="margin-top:20px;color:#333;">Bewegung Einstellungen Videos</h3>
<label>Flugmodus Videos</label>
<select id="flight_path_mode_video">
<option value="random">Random Drift</option>
<option value="bounce">Bounce</option>
</select>
<label>Drift Stärke Videos</label>
<input id="drift_strength_video" placeholder="0.2">
<label>Rotation Stärke Videos</label>
<input id="rotation_video" placeholder="90">
<label>Rotation Richtung Videos</label>
<select id="rotation_direction_video">
<option value="both">Beide</option>
<option value="left">Links</option>
<option value="right">Rechts</option>
</select>

</div>
</div>


<!-- Geschwindigkeit -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Geschwindigkeit
<span>▼</span>
</div>
<div class="sectionContent">

<h3 style="margin-top:0;color:#333;">Geschwindigkeit Einstellungen Bilder</h3>
<label>Animationsdauer Bilder (Sekunden)</label>
<input id="animation_image" placeholder="30">
<div class="row">
<label>Speed Variation Bilder</label>
<input type="checkbox" id="speed_variation_image" class="checkbox">
</div>
<label>Speed Stärke Bilder</label>
<input id="speed_strength_image" placeholder="0.4">

<h3 style="margin-top:20px;color:#333;">Geschwindigkeit Einstellungen Videos</h3>
<label>Animationsdauer Videos (Sekunden)</label>
<input id="animation_video" placeholder="30">
<div class="row">
<label>Speed Variation Videos</label>
<input type="checkbox" id="speed_variation_video" class="checkbox">
</div>
<label>Speed Stärke Videos</label>
<input id="speed_strength_video" placeholder="0.4">

</div>
</div>


<!-- Highlight -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Highlight
<span>▼</span>
</div>
<div class="sectionContent">

<h3 style="margin-top:0;color:#333;">Highlight Einstellungen Bilder</h3>
<div class="row">
<label>Highlight neue Bilder</label>
<input type="checkbox" id="highlight_image" class="checkbox">
</div>
<label>Highlight Dauer Bilder (Sekunden)</label>
<input id="highlight_duration_image" placeholder="10">
<label>Highlight Farbe Bilder</label>
<input type="color" id="highlight_color_image">
<label>Max Highlights gleichzeitig (Bilder)</label>
<input id="max_highlights_image" placeholder="3">

<h3 style="margin-top:20px;color:#333;">Highlight Einstellungen Videos</h3>
<div class="row">
<label>Highlight neue Videos</label>
<input type="checkbox" id="highlight_video" class="checkbox">
</div>
<label>Highlight Dauer Videos (Sekunden)</label>
<input id="highlight_duration_video" placeholder="10">
<label>Highlight Farbe Videos</label>
<input type="color" id="highlight_color_video">
<label>Max Highlights gleichzeitig (Videos)</label>
<input id="max_highlights_video" placeholder="3">

</div>
</div>


<!-- Center Highlight -->

<div class="section">

<div class="sectionHeader" onclick="toggleSection(this)">
Center Highlight
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_highlight')">❓</span>
<span>▼</span>
</div>

<div class="sectionContent">

<div class="row">
<label>Center Highlight aktiv
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_highlight_enable')">❓</span>
</label>
<input type="checkbox" id="center_highlight" class="checkbox">
</div>
<div id="help_center_highlight_enable" class="helpText">
Schaltet den Modus ein, bei dem neue Bilder groß in der Mitte erscheinen.
</div>

<label>Modus
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_mode')">❓</span>
</label>
<div id="help_center_mode" class="helpText">
Wählt aus, wie das Center Highlight animiert wird (Durchflug oder Spotlight).
</div>
<select id="center_mode">
<option value="fly">Fly Through</option>
<option value="spotlight">Spotlight</option>
</select>
<label>Größe (% des Bildschirms)
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_scale')">❓</span>
</label>
<div id="help_center_scale" class="helpText">
Wie viel vom Bildschirm das Bild/Video in der Mitte einnimmt (z.B. 30 = füllt 30% der Bildschirmhöhe).
</div>
<input id="center_screen_percent" placeholder="30" type="number" min="5" max="100">
<label>Dauer (Sekunden)
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_duration')">❓</span>
</label>
<div id="help_center_duration" class="helpText">
Wie lange ein Bild im Center Highlight bleibt (Sekunden).
</div>
<input id="center_duration" placeholder="5">
<label>Max. gleichzeitig
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_max')">❓</span>
</label>
<div id="help_center_max" class="helpText">
Maximale Anzahl von Center Highlights, die gleichzeitig angezeigt werden dürfen.
</div>
<input id="center_max" placeholder="1">
<label>Positions-Variation (px)
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_variation')">❓</span>
</label>
<div id="help_center_variation" class="helpText">
Wie stark die Position von der Bildschirmmitte abweichen darf (0 = exakt mittig, z.B. 50 = leichte zufällige Versetzung).
</div>
<input id="center_variation" placeholder="30">
<label>Entry Speed (Sekunden)
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_entry')">❓</span>
</label>
<div id="help_center_entry" class="helpText">
Dauer der Einblendung ins Center (z.B. 0.2 = schnell, 2 = langsam). Wert in Sekunden.
</div>
<input id="center_entry" type="number" min="0.05" max="30" step="0.1" placeholder="1">
<label>Exit Speed (Sekunden)
<span class="help" onclick="event.stopPropagation();toggleHelp('help_center_exit')">❓</span>
</label>
<div id="help_center_exit" class="helpText">
Dauer des Abflugs vom Center nach unten (z.B. 0.5 = schnell, 3 = langsam). Wert in Sekunden.
</div>
<input id="center_exit" type="number" min="0.05" max="30" step="0.1" placeholder="1">

</div>
</div>


<!-- Hintergrund -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Hintergrund
<span>▼</span>
</div>
<div class="sectionContent">
<div class="sectionInfo">Hintergrund der Anzeige: Farbe oder Bild.</div>
<label>Modus</label>
<select id="background_mode">
<option value="color">Hintergrundfarbe</option>
<option value="image">Hintergrundbild</option>
</select>
<div id="background_color_row">
<label>Hintergrundfarbe</label>
<input type="color" id="background_color">
<input type="text" id="background_color_hex" placeholder="#000000" style="margin-top:5px;">
</div>
<div id="background_image_row" style="display:none;">
<label>Hintergrundbild</label>
<input type="file" id="background_upload_input" accept="image/*" style="margin-bottom:10px;">
<button type="button" id="background_upload_btn" style="background:#4CAF50;color:white;border:none;padding:8px 16px;border-radius:6px;margin-bottom:10px;">Bild hochladen</button>
<select id="background_image" style="margin-top:5px;">
<option value="">– Bild auswählen –</option>
</select>
<div id="background_image_preview" style="margin-top:10px;max-width:200px;height:120px;border:1px solid #ccc;border-radius:6px;overflow:hidden;background:#333;"></div>
</div>
</div>
</div>


<!-- QR Code -->

<div class="section">

<div class="sectionHeader" onclick="toggleSection(this)">
QR Code
<span>▼</span>
</div>

<div class="sectionContent">

<div class="row">
<label>QR Code anzeigen
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_show')">❓</span>
</label>
<input type="checkbox" id="qr_show" class="checkbox">
</div>
<div id="help_qr_show" class="helpText">
Schaltet den QR-Code auf der Wand ein oder aus.
</div>

<label>QR Text
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_text')">❓</span>
</label>
<div id="help_qr_text" class="helpText">
Text, der unterhalb des QR-Codes angezeigt wird (z.B. „Schick uns dein Bild!“).
</div>
<input id="qr_text">

<label>QR Größe
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_size')">❓</span>
</label>
<div id="help_qr_size" class="helpText">
Kantenlänge des QR-Codes in Pixeln.
</div>
<input id="qr_size">

<label>QR Textgröße
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_text_size')">❓</span>
</label>
<div id="help_qr_text_size" class="helpText">
Schriftgröße des Textes unterhalb des QR-Codes.
</div>
<input id="qr_text_size">

<label>QR Position
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_position')">❓</span>
</label>
<div id="help_qr_position" class="helpText">
Wo auf der Wand der QR-Code eingeblendet wird.
</div>
<select id="qr_position">
<option value="center-bottom">unten mittig</option>
<option value="top-left">oben links</option>
<option value="top-right">oben rechts</option>
<option value="bottom-left">unten links</option>
<option value="bottom-right">unten rechts</option>
</select>

<label>QR Textfarbe
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_text_color')">❓</span>
</label>
<div id="help_qr_text_color" class="helpText">
Farbe des Begleittextes unter dem QR-Code.
</div>
<input type="color" id="qr_text_color">

<div class="row">
<label>Dynamischer QR Code
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_dynamic')">❓</span>
</label>
<input type="checkbox" id="qr_dynamic" class="checkbox">
</div>
<div id="help_qr_dynamic" class="helpText">
Wenn aktiv, blendet die Wand den QR-Code im Wechsel ein und aus.
</div>

<label>QR Anzeige Dauer
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_show_duration')">❓</span>
</label>
<div id="help_qr_show_duration" class="helpText">
Wie lange der QR-Code jeweils sichtbar ist (Sekunden).
</div>
<input id="qr_show_duration">

<label>QR Pause Dauer
<span class="help" onclick="event.stopPropagation();toggleHelp('help_qr_hide_duration')">❓</span>
</label>
<div id="help_qr_hide_duration" class="helpText">
Wie lange der QR-Code jeweils ausgeblendet bleibt (Sekunden).
</div>
<input id="qr_hide_duration">

</div>
</div>


<!-- Banner -->

<div class="section">

<div class="sectionHeader" onclick="toggleSection(this)">
Banner
<span>▼</span>
</div>

<div class="sectionContent">

<div id="help_banner" class="sectionInfo">
Blendet einen Textbanner oben oder unten ein, z.B. mit dem Namen des Paares.
</div>

<div class="row">
<label>Banner aktiv</label>
<input type="checkbox" id="banner_enabled" class="checkbox">
</div>

<label>Banner Text (Markdown)</label>
<textarea id="banner_text"></textarea>

<label>Banner Position</label>
<select id="banner_position">
<option value="top">Oben</option>
<option value="bottom">Unten</option>
</select>

<label>Banner Höhe</label>
<input id="banner_height">

<label>Banner Farbe</label>
<input type="color" id="banner_color">

<label>Banner Textfarbe</label>
<input type="color" id="banner_text_color">

<label>Banner Anzeige Dauer</label>
<input id="banner_show_duration">

<label>Banner Pause Dauer</label>
<input id="banner_hide_duration">

</div>
</div>


<!-- Bildtext unter den Fotos -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Bildtext unter den Fotos
<span>▼</span>
</div>
<div class="sectionContent">

<div id="help_comment" class="sectionInfo">
Text, den Gäste beim Hochladen zu Fotos eingeben können. Wird unter dem Bild auf der Wand angezeigt.
</div>

<div class="row">
<label>Bildtext anzeigen</label>
<input type="checkbox" id="comments_enabled" class="checkbox">
</div>

<label>Textfarbe</label>
<input type="color" id="comment_color">

<label>Schriftart</label>
<input id="comment_font" placeholder="Pacifico">
<div class="helpText" style="margin-top:-10px;margin-bottom:10px;">Google Font Name (z.B. Pacifico, Caveat, Dancing Script)</div>

<label>Schriftgröße (px)</label>
<input id="comment_size" placeholder="22" type="number">

<label>Max. Zeichen pro Kommentar</label>
<input id="comment_max_length" placeholder="80" type="number">

<div class="row">
<label>Fett</label>
<input type="checkbox" id="comment_bold" class="checkbox">
</div>

<div class="row">
<label>Unterstrichen</label>
<input type="checkbox" id="comment_underline" class="checkbox">
</div>

</div>
</div>


<!-- Erweitert -->

<h2 class="sectionGroupTitle">Erweitert</h2>

<!-- Netzwerk -->

<div class="section">

<div class="sectionHeader" onclick="toggleSection(this)">
Netzwerk
<span>▼</span>
</div>

<div class="sectionContent">

<div id="help_network" class="sectionInfo">
Steuert, wer und wie auf den Server zugreifen kann.
</div>

<label>Netzwerkmodus</label>

<select id="network_mode">
    <option value="local">Local (nur dieser Computer)</option>
    <option value="network">Network (im WLAN sichtbar)</option>
    <option value="public">Public Internet (Router Port Forward)</option>
    <option value="tunnel">Public Internet (Cloudflare Tunnel)</option>
</select>

<div id="network_info" style="margin-top:15px;padding:10px;border:1px solid #ccc;">
<b>Network Info</b>
<div id="network_details">lädt...</div>
</div>

<button onclick="testNetwork()" style="margin-bottom:10px;">
Verbindung testen
</button>

<div id="network_test_result" style="
margin-top:10px;
background:#eef5ff;
padding:10px;
border-radius:6px;
font-family:monospace;
font-size:14px;
"></div>

<label>Public Base URL
<span class="help" onclick="event.stopPropagation();toggleHelp('help_public_base')">❓</span>
</label>
<div id="help_public_base" class="helpText">
Optionale öffentliche Basis-URL, die in Links verwendet wird (z.B. bei Reverse Proxy).
</div>
<input id="public_base_url">

</div>
</div>


<!-- Tunnel-Verwaltung -->
<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
    Tunnel-Verwaltung
    <span>▼</span>
  </div>
  <div class="sectionContent">
    <div id="help_tunnel" class="sectionInfo">
Cloudflare-Tunnel stellt die Wand ohne eigene Router-Konfiguration über das Internet bereit.
    </div>
    <p>Tunnel-Status: <span id="tunnel_status">...</span></p>
    <button onclick="startTunnel()">Tunnel starten</button>
    <button onclick="stopTunnel()">Tunnel stoppen</button>
  </div>
</div>


<!-- Extras -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Extras
<span>▼</span>
</div>
<div class="sectionContent">
<div class="row">
<label>Bildschirm wach halten (Wake Lock API)</label>
<input type="checkbox" id="screen_wake_lock" class="checkbox">
</div>
<div class="sectionInfo" style="margin-top:5px;">
Verwendet die Wake Lock API. Funktioniert in Chrome und einigen anderen Browsern.
</div>

<div class="row">
<label>Alternative Wachfunktion (Video-Fallback)</label>
<input type="checkbox" id="screen_wake_lock_alternative" class="checkbox">
</div>
<div class="sectionInfo" style="margin-top:5px;">
Spielt ein unsichtbares Video im Hintergrund. Funktioniert in Edge, Firefox und älteren Browsern, wenn die Wake Lock API nicht unterstützt wird.
</div>
</div>
</div>

<!-- Debug -->

<div class="section">

<div class="sectionHeader" onclick="toggleSection(this)">
Debug
<span>▼</span>
</div>

<div class="sectionContent">

<div id="help_debug" class="sectionInfo">
Zeigt ein technisches Overlay mit Status-Informationen zur Wand (nur für Fehlersuche).
</div>

<div class="row">
<label>Debug Overlay anzeigen</label>
<input type="checkbox" id="debug_overlay" class="checkbox">
</div>

</div>
</div>


<!-- Media-Cache -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Media-Cache
<span>▼</span>
</div>
<div class="sectionContent">

<div id="help_cache" class="sectionInfo">
Lädt Bilder und Videos beim ersten Abruf in den Browser-Cache. Bei Verbindungsabbruch werden sie aus dem Cache geladen (Fallback). TTL = wie lange Einträge gültig bleiben.
</div>

<div class="row">
<label>Cache aktivieren</label>
<input type="checkbox" id="cache_enabled" class="checkbox">
</div>

<label>Cache TTL (Minuten)</label>
<input id="cache_ttl_minutes" placeholder="30" type="number">

<label>Max. Bilder im Cache</label>
<input id="cache_max_images" placeholder="100" type="number">

<label>Max. Videos im Cache</label>
<input id="cache_max_videos" placeholder="20" type="number">

<label>Max. Cache-Größe (MB, 0 = unbegrenzt)</label>
<input id="cache_max_size_mb" placeholder="500" type="number">

</div>
</div>


<!-- Upload-Seite -->

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">
Upload-Seite
<span>▼</span>
</div>
<div class="sectionContent">

<div id="help_upload" class="sectionInfo">
Einstellungen für die Upload-Seite, auf die Gäste über den QR-Code zugreifen.
</div>

<label>Angezeigter Text</label>
<input id="upload_greeting" placeholder="Lade deine Fotos hoch ❤️">

<label>Button-Farbe</label>
<input type="color" id="upload_button_color">

<label>Header-Bild (optional)</label>
<input id="upload_image" placeholder="header.jpg">
<div class="helpText" style="margin-top:-10px;margin-bottom:10px;">Datei aus dem Ordner <code>header/</code> im Projekt (z.B. header.jpg → /header/header.jpg)</div>

<div class="row">
<label>Videos hochladen erlauben</label>
<input type="checkbox" id="upload_allow_videos" class="checkbox">
</div>

<label>Max. Anzahl Dateien pro Upload</label>
<input id="upload_max_files" placeholder="20" type="number">

<label>Max. Dateigröße (MB)</label>
<input id="upload_max_file_size_mb" placeholder="50" type="number">

</div>
</div>


<button onclick="save()">Einstellungen speichern</button>


<!-- Statusübersicht (unten) -->

<div id="status_section" style="background:#eef5ff;padding:20px;border-radius:8px;margin-top:30px;border:1px solid #c5d9f0;">

<h2 class="sectionGroupTitle" style="margin-top:0;">Statusübersicht</h2>

<div id="status_grid" style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
<div>
<b>Netzwerk</b><br>
Mode: <span id="stat_mode">–</span><br>
Port: <span id="stat_port">–</span><br>
Local IP: <span id="stat_local_ip">–</span><br>
External IP: <span id="stat_external_ip">–</span><br>
Tunnel: <span id="tunnel_url">...</span>
</div>
<div>
<b>Server</b><br>
Online seit: <span id="stat_online_since">–</span><br>
Wall verbunden: <span id="stat_wall_connected">–</span><br>
Bilder angezeigt: <span id="stat_images_displayed">–</span><br>
Videos angezeigt: <span id="stat_videos_displayed">–</span><br>
Bilder hochgeladen: <span id="stat_media_images">–</span><br>
Videos hochgeladen: <span id="stat_media_videos">–</span><br>
Upload-Seite offen: <span id="stat_upload_viewers">–</span><br>
Uploads laufen: <span id="stat_uploads_progress">–</span>
</div>
</div>

<b>Upload QR-Code</b><br>
<div id="qr_code" style="width:220px;height:220px;margin-top:10px;border:1px solid #ccc;padding:10px;background:white;border-radius:8px;"></div>

<br><br>

<button onclick="window.open('""" + net.get("upload_url","") + """','_blank')" style="margin-bottom:10px;">
Upload Seite öffnen
</button>

<button onclick="window.open('""" + net.get("wall_url","") + """','_blank')">
Wall öffnen
</button>

</div>

</div>


<script>

async function updateNetworkInfo(){

    let res = await fetch("/api/config")
    let cfg = await res.json()

    let mode = cfg.network_mode
    let port = cfg.port

    let res2 = await fetch("/api/tunnel/status")
    let tunnel = await res2.json()

    let txt = ""

    if(mode==="local"){
        txt="Server nur lokal erreichbar."
    }

    if(mode==="network"){
        txt="Server im lokalen Netzwerk erreichbar.<br>"
        txt+="Firewall Port muss geöffnet sein."
    }

    if(mode==="public"){
        txt="Öffentlicher Zugriff über Router Port Forward.<br>"
        txt+="Router Port: "+port
    }

    if(mode==="tunnel"){

        if(tunnel.running){
            txt="Tunnel aktiv:<br>"+tunnel.url
        }else{
            txt="Tunnel startet..."
        }
    }

    document.getElementById("network_details").innerHTML=txt
}

setInterval(updateNetworkInfo,2000)
updateNetworkInfo()

async function updateStatusOverview(){
try{
let res = await fetch("/api/admin/stats")
if(!res.ok) return
let s = await res.json()
document.getElementById("stat_mode").textContent = s.network_mode || "–"
document.getElementById("stat_port").textContent = s.network_port || "–"
document.getElementById("stat_local_ip").textContent = s.local_ip || "–"
document.getElementById("stat_external_ip").textContent = s.external_ip || "–"
document.getElementById("stat_online_since").textContent = s.server_online_since ? new Date(s.server_online_since*1000).toLocaleString("de-DE") : "–"
document.getElementById("stat_wall_connected").textContent = s.wall_connected ? "Ja ("+s.wall_clients+")" : "Nein"
document.getElementById("stat_images_displayed").textContent = s.wall_images_displayed ?? "–"
document.getElementById("stat_videos_displayed").textContent = s.wall_videos_displayed ?? "–"
document.getElementById("stat_media_images").textContent = s.media_images_count ?? "–"
document.getElementById("stat_media_videos").textContent = s.media_videos_count ?? "–"
document.getElementById("stat_upload_viewers").textContent = s.upload_page_viewers ?? "–"
document.getElementById("stat_uploads_progress").textContent = s.uploads_in_progress ?? "–"
}catch(e){}
}
setInterval(updateStatusOverview,2000)
updateStatusOverview()

async function renderUploadQR(){

    try{
        let res = await fetch("/api/upload_url")
        if(!res.ok) return
        let data = await res.json()

        let box = document.getElementById("qr_code")
        if(!box) return

        box.innerHTML = ""

        new QRCode(box,{
            text:data.url || "",
            width:200,
            height:200
        })
    }catch(e){
        console.error("QR Render Fehler",e)
    }
}

function toggleSection(header){

let content = header.nextElementSibling
content.style.display = content.style.display==="block" ? "none" : "block"

}

function toggleHelp(id){

let el=document.getElementById(id)
el.style.display=el.style.display==="block"?"none":"block"

}

function updateBackgroundModeVisibility(){
let modeEl=document.getElementById("background_mode")
let colorRow=document.getElementById("background_color_row")
let imageRow=document.getElementById("background_image_row")
if(!modeEl||!colorRow||!imageRow) return
let mode=modeEl.value
colorRow.style.display=mode==="color"?"block":"none"
imageRow.style.display=mode==="image"?"block":"none"
}

async function loadBackgroundList(){
let sel=document.getElementById("background_image")
let cur=sel.value
sel.innerHTML='<option value="">– Bild auswählen –</option>'
try{
let res=await fetch("/api/background/list")
let files=await res.json()
for(let f of files){
let opt=document.createElement("option")
opt.value=f
opt.textContent=f
sel.appendChild(opt)
}
if(cur) sel.value=cur
}catch(e){}
}

function updateBackgroundPreview(){
let sel=document.getElementById("background_image")
let prev=document.getElementById("background_image_preview")
if(!sel||!prev) return
if(!sel.value){ prev.style.backgroundImage=""; prev.style.background="#333"; return }
prev.style.backgroundImage="url(/background/"+encodeURIComponent(sel.value)+")"
prev.style.backgroundSize="cover"
prev.style.backgroundPosition="center"
}

document.addEventListener("DOMContentLoaded",()=>{
let bgMode=document.getElementById("background_mode")
let bgColor=document.getElementById("background_color")
let bgHex=document.getElementById("background_color_hex")
let bgUploadBtn=document.getElementById("background_upload_btn")
let bgUploadInput=document.getElementById("background_upload_input")
let bgImage=document.getElementById("background_image")
if(bgMode) bgMode.onchange=updateBackgroundModeVisibility
if(bgColor) bgColor.oninput=()=>{ if(bgHex) bgHex.value=bgColor.value }
if(bgHex) bgHex.oninput=()=>{ if(/^#[0-9A-Fa-f]{6}$/.test(bgHex.value)) bgColor.value=bgHex.value }
if(bgImage) bgImage.onchange=updateBackgroundPreview
if(bgUploadBtn&&bgUploadInput) bgUploadBtn.onclick=async()=>{
if(!bgUploadInput.files||!bgUploadInput.files[0]){ alert("Bitte zuerst ein Bild auswählen"); return }
let fd=new FormData()
fd.append("file",bgUploadInput.files[0])
try{
let r=await fetch("/api/background/upload",{method:"POST",body:fd})
let d=await r.json()
if(d.ok){ await loadBackgroundList(); bgImage.value=d.filename; updateBackgroundPreview(); bgUploadInput.value="" }
else alert(d.error||"Upload fehlgeschlagen")
}catch(e){ alert("Upload fehlgeschlagen") }
}
})

let config={}

async function load(){

let res=await fetch("/api/config")
config=await res.json()

wall_view_mode.value=config.wall_view_mode||"fly"
document.getElementById("grid_settings").style.display=(config.wall_view_mode||"fly")==="grid"?"block":"none"
wall_view_mode.onchange=function(){ document.getElementById("grid_settings").style.display=wall_view_mode.value==="grid"?"block":"none" }
grid_columns.value=config.grid_columns||4
grid_animation_duration.value=config.grid_animation_duration||config.grid_interval||8
grid_spacing_columns.value=config.grid_spacing_columns||config.grid_spacing_rows||20
grid_spacing_rows.value=config.grid_spacing_rows||config.grid_spacing||0
grid_show_frames.checked=config.grid_show_frames!==false

network_mode.value=config.network_mode
public_base_url.value=config.public_base_url

spawn_interval.value=config.image_spawn_interval
max_images.value=config.max_images_on_screen
image_min.value=config.image_min_size
image_max.value=config.image_max_size

max_videos.value=config.max_videos_on_screen
video_interval.value=config.video_spawn_interval
video_mode.value=config.video_playback_mode
video_min.value=config.video_min_size
video_max.value=config.video_max_size

flight_path_mode_image.value=config.image_flight_path_mode||"random"
drift_strength_image.value=config.image_drift_strength
rotation_image.value=config.image_rotation_strength
rotation_direction_image.value=config.image_rotation_direction_mode||"both"

flight_path_mode_video.value=config.video_flight_path_mode||"random"
drift_strength_video.value=config.video_drift_strength
rotation_video.value=config.video_rotation_strength
rotation_direction_video.value=config.video_rotation_direction_mode||"both"

animation_image.value=config.image_animation_duration
speed_variation_image.checked=config.image_speed_variation_enabled
speed_strength_image.value=config.image_speed_variation_strength

animation_video.value=config.video_animation_duration
speed_variation_video.checked=config.video_speed_variation_enabled
speed_strength_video.value=config.video_speed_variation_strength

highlight_image.checked=config.image_highlight_new
highlight_duration_image.value=config.image_highlight_duration
highlight_color_image.value=config.image_highlight_color||"#ffff00"
max_highlights_image.value=config.image_max_simultaneous_highlights

highlight_video.checked=config.video_highlight_new
highlight_duration_video.value=config.video_highlight_duration
highlight_color_video.value=config.video_highlight_color||"#ffff00"
max_highlights_video.value=config.video_max_simultaneous_highlights

center_highlight.checked=config.center_highlight_enabled
center_mode.value=config.center_highlight_mode
center_screen_percent.value=config.center_highlight_screen_percent??30
center_duration.value=config.center_highlight_duration
center_max.value=config.center_highlight_max_simultaneous
center_variation.value=config.center_highlight_position_variation
center_entry.value=config.center_highlight_entry_speed
center_exit.value=config.center_highlight_exit_speed

let bgMode=document.getElementById("background_mode")
let bgColor=document.getElementById("background_color")
let bgColorHex=document.getElementById("background_color_hex")
let bgImage=document.getElementById("background_image")
if(bgMode){ bgMode.value=config.background_mode||"color" }
if(bgColor){ bgColor.value=config.background_color||"#000000" }
if(bgColorHex){ bgColorHex.value=config.background_color||"#000000" }
if(bgImage){ bgImage.value=config.background_image||"" }
updateBackgroundModeVisibility()
await loadBackgroundList()
updateBackgroundPreview()

qr_show.checked=config.show_qr_code
qr_text.value=config.qr_text
qr_size.value=config.qr_size
qr_text_size.value=config.qr_text_size
qr_position.value=config.qr_position
qr_text_color.value=config.qr_text_color

qr_dynamic.checked=config.qr_dynamic_enabled
qr_show_duration.value=config.qr_show_duration
qr_hide_duration.value=config.qr_hide_duration

banner_enabled.checked=config.banner_enabled
banner_text.value=config.banner_text
banner_position.value=config.banner_position
banner_height.value=config.banner_height
banner_color.value=config.banner_color
banner_text_color.value=config.banner_text_color

banner_show_duration.value=config.banner_show_duration
banner_hide_duration.value=config.banner_hide_duration

comments_enabled.checked=config.comments_enabled !== false
comment_color.value=config.comment_color || "#e51515"
comment_font.value=config.comment_font || "Pacifico"
comment_size.value=config.comment_size || 22
comment_max_length.value=config.comment_max_length || 80
comment_bold.checked=config.comment_bold || false
comment_underline.checked=config.comment_underline || false

upload_greeting.value=config.upload_greeting || "Lade deine Fotos hoch ❤️"
upload_button_color.value=config.upload_button_color || "#ff4b5c"
upload_image.value=config.upload_image || ""
upload_allow_videos.checked=config.upload_allow_videos !== false
upload_max_files.value=config.upload_max_files || 20
upload_max_file_size_mb.value=config.upload_max_file_size_mb || 50

debug_overlay.checked=config.debug_overlay || false
let screenWakeLockEl=document.getElementById("screen_wake_lock")
if(screenWakeLockEl) screenWakeLockEl.checked=config.screen_wake_lock_enabled || false
let screenWakeLockAltEl=document.getElementById("screen_wake_lock_alternative")
if(screenWakeLockAltEl) screenWakeLockAltEl.checked=config.screen_wake_lock_alternative || false
cache_enabled.checked=config.cache_enabled || false
cache_ttl_minutes.value=config.cache_ttl_minutes || 30

}


async function save(){

function toFloat(value, fallback){
    let v=parseFloat(value)
    return isNaN(v)?fallback:v
}

function toInt(value, fallback){
    let v=parseInt(value)
    return isNaN(v)?fallback:v
}

let res=await fetch("/api/config")
let config=await res.json()

config.wall_view_mode = wall_view_mode.value
config.grid_columns = toInt(grid_columns.value, config.grid_columns || 4)
config.grid_animation_duration = toFloat(grid_animation_duration.value, config.grid_animation_duration || config.grid_interval || 8)
config.grid_spacing_columns = toInt(grid_spacing_columns.value, config.grid_spacing_columns || config.grid_spacing_rows || 20)
config.grid_spacing_rows = toInt(grid_spacing_rows.value, config.grid_spacing_rows || config.grid_spacing || 0)
config.grid_show_frames = grid_show_frames.checked

config.network_mode = network_mode.value
config.public_base_url = public_base_url.value

config.image_spawn_interval=toFloat(spawn_interval.value, config.image_spawn_interval || 6)
config.max_images_on_screen=toInt(max_images.value, config.max_images_on_screen || 10)
config.image_min_size=toInt(image_min.value, config.image_min_size || 100)
config.image_max_size=toInt(image_max.value, config.image_max_size || 150)

config.max_videos_on_screen=toInt(max_videos.value, config.max_videos_on_screen || 2)
config.video_spawn_interval=toFloat(video_interval.value, config.video_spawn_interval || 10)
config.video_playback_mode=video_mode.value
config.video_min_size=toInt(video_min.value, config.video_min_size || 100)
config.video_max_size=toInt(video_max.value, config.video_max_size || 150)

config.image_flight_path_mode=flight_path_mode_image.value
config.image_drift_strength=toFloat(drift_strength_image.value, config.image_drift_strength || 0.2)
config.image_rotation_strength=toFloat(rotation_image.value, config.image_rotation_strength || 90)
config.image_rotation_direction_mode=rotation_direction_image.value

config.video_flight_path_mode=flight_path_mode_video.value
config.video_drift_strength=toFloat(drift_strength_video.value, config.video_drift_strength || 0.2)
config.video_rotation_strength=toFloat(rotation_video.value, config.video_rotation_strength || 90)
config.video_rotation_direction_mode=rotation_direction_video.value

config.image_animation_duration=toFloat(animation_image.value, config.image_animation_duration || 30)
config.image_speed_variation_enabled=speed_variation_image.checked
config.image_speed_variation_strength=toFloat(speed_strength_image.value, config.image_speed_variation_strength || 0.4)

config.video_animation_duration=toFloat(animation_video.value, config.video_animation_duration || 30)
config.video_speed_variation_enabled=speed_variation_video.checked
config.video_speed_variation_strength=toFloat(speed_strength_video.value, config.video_speed_variation_strength || 0.4)

config.image_highlight_new=highlight_image.checked
config.image_highlight_duration=toFloat(highlight_duration_image.value, config.image_highlight_duration || 10)
config.image_highlight_color=highlight_color_image.value
config.image_max_simultaneous_highlights=toInt(max_highlights_image.value, config.image_max_simultaneous_highlights || 3)

config.video_highlight_new=highlight_video.checked
config.video_highlight_duration=toFloat(highlight_duration_video.value, config.video_highlight_duration || 10)
config.video_highlight_color=highlight_color_video.value
config.video_max_simultaneous_highlights=toInt(max_highlights_video.value, config.video_max_simultaneous_highlights || 3)

config.center_highlight_enabled=center_highlight.checked
config.center_highlight_mode=center_mode.value
config.center_highlight_screen_percent=toFloat(center_screen_percent.value, config.center_highlight_screen_percent ?? 30)
config.center_highlight_duration=toFloat(center_duration.value, config.center_highlight_duration || 5)
config.center_highlight_max_simultaneous=toInt(center_max.value, config.center_highlight_max_simultaneous || 1)
config.center_highlight_position_variation=toFloat(center_variation.value, config.center_highlight_position_variation || 30)
config.center_highlight_entry_speed=toFloat(center_entry.value, config.center_highlight_entry_speed || 1)
config.center_highlight_exit_speed=toFloat(center_exit.value, config.center_highlight_exit_speed || 1)

let bgModeEl=document.getElementById("background_mode")
let bgColorEl=document.getElementById("background_color")
let bgImageEl=document.getElementById("background_image")
config.background_mode=bgModeEl?bgModeEl.value:"color"
config.background_color=bgColorEl?bgColorEl.value:"#000000"
config.background_image=(bgModeEl&&bgModeEl.value==="image"&&bgImageEl)?bgImageEl.value:""

config.show_qr_code=qr_show.checked
config.qr_text=qr_text.value
config.qr_size=toInt(qr_size.value, config.qr_size || 220)
config.qr_text_size=toInt(qr_text_size.value, config.qr_text_size || 24)
config.qr_position=qr_position.value
config.qr_text_color=qr_text_color.value

config.qr_dynamic_enabled=qr_dynamic.checked
config.qr_show_duration=toFloat(qr_show_duration.value, config.qr_show_duration || 5)
config.qr_hide_duration=toFloat(qr_hide_duration.value, config.qr_hide_duration || 5)

config.banner_enabled=banner_enabled.checked
config.banner_text=banner_text.value.replace(/\\r\\n/g,"\\n")
config.banner_position=banner_position.value
config.banner_height=toInt(banner_height.value, config.banner_height || 120)
config.banner_color=banner_color.value
config.banner_text_color=banner_text_color.value
config.banner_show_duration=toFloat(banner_show_duration.value, config.banner_show_duration || 10)
config.banner_hide_duration=toFloat(banner_hide_duration.value, config.banner_hide_duration || 10)

config.comments_enabled=comments_enabled.checked
config.comment_color=comment_color.value || "#e51515"
config.comment_font=comment_font.value || "Pacifico"
config.comment_size=toInt(comment_size.value, config.comment_size || 22)
config.comment_max_length=toInt(comment_max_length.value, config.comment_max_length || 80)
config.comment_bold=comment_bold.checked
config.comment_underline=comment_underline.checked

config.upload_greeting=upload_greeting.value || "Lade deine Fotos hoch ❤️"
config.upload_button_color=upload_button_color.value || "#ff4b5c"
config.upload_image=upload_image.value || ""
config.upload_allow_videos=upload_allow_videos.checked
config.upload_max_files=toInt(upload_max_files.value, config.upload_max_files || 20)
config.upload_max_file_size_mb=toInt(upload_max_file_size_mb.value, config.upload_max_file_size_mb || 50)

config.debug_overlay=debug_overlay.checked
let screenWakeLockCb=document.getElementById("screen_wake_lock")
config.screen_wake_lock_enabled=screenWakeLockCb?screenWakeLockCb.checked:false
let screenWakeLockAltCb=document.getElementById("screen_wake_lock_alternative")
config.screen_wake_lock_alternative=screenWakeLockAltCb?screenWakeLockAltCb.checked:false
config.cache_enabled=cache_enabled.checked
config.cache_ttl_minutes=toInt(cache_ttl_minutes.value, config.cache_ttl_minutes || 30)
config.cache_max_images=toInt(cache_max_images.value, config.cache_max_images || 100)
config.cache_max_videos=toInt(cache_max_videos.value, config.cache_max_videos || 20)
config.cache_max_size_mb=toInt(cache_max_size_mb.value, config.cache_max_size_mb || 500)

let saveRes=await fetch("/api/config",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify(config)
})
let saveData=await saveRes.json()
if(saveData.view_changed){
alert("Einstellungen gespeichert. Ansicht geändert – Admin und Wall werden neu geladen.")
location.reload()
}else{
alert("Einstellungen gespeichert.")
}
}

async function testNetwork(){

let res = await fetch("/api/network_test")

let data = await res.json()

let box = document.getElementById("network_test_result")

let txt = ""

txt += "Local URL: " + data.local_url + "<br>"

if(data.local_ok){

txt += "Local Test: OK<br>"

}else{

txt += "Local Test: NICHT erreichbar<br>"
txt += "Mögliche Ursache: Firewall blockiert Port " + data.port + "<br>"

}

if(data.public_url){

txt += "<br>Public URL: " + data.public_url + "<br>"

if(data.public_ok){

txt += "Public Test: OK<br>"

}else{

txt += "Public Test: NICHT erreichbar<br>"
txt += "Router Portfreigabe nötig:<br>"
txt += "TCP " + data.port + " → Server IP"

}

}

box.innerHTML = txt

}

load()
fetch("/api/version").then(r=>r.json()).then(d=>{
let el=document.getElementById("app_version")
if(el) el.textContent="v"+d.version
}).catch(()=>{})

async function updateTunnel(){

let res = await fetch("/api/tunnel/status")
let data = await res.json()

let el = document.getElementById("tunnel_url")

if(data.running && data.url){

el.innerHTML = `<a href="${data.url}" target="_blank">${data.url}</a>`

}else{

el.innerText = "Tunnel nicht aktiv"

}

}

setInterval(updateTunnel,2000)
updateTunnel()
renderUploadQR()


</script>

<script>
async function updateTunnelStatus() {
    const res = await fetch('/api/tunnel/status');
    if (!res.ok) {
        document.getElementById('tunnel_status').innerText = 'Unavailable';
        return;
    }
    const data = await res.json();
    document.getElementById('tunnel_status').innerText = data.running ? 'Running' : 'Stopped';
}

async function startTunnel() {
    await fetch('/api/tunnel/start', {method: 'POST'});
    await updateTunnelStatus();
}

async function stopTunnel() {
    await fetch('/api/tunnel/stop', {method: 'POST'});
    await updateTunnelStatus();
}

// Status regelmäßig aktualisieren
updateTunnelStatus();
</script>


</body>
</html>

"""
@router.get("/api/admin/stats")
def admin_stats():
    """Status-Übersicht für Admin-Seite."""
    media_images = 0
    media_videos = 0
    if os.path.isdir(MEDIA_DIR):
        for f in os.listdir(MEDIA_DIR):
            ext = os.path.splitext(f)[1].lower()
            if ext in IMAGE_EXT:
                media_images += 1
            elif ext in VIDEO_EXT:
                media_videos += 1

    now = time.time()
    upload_viewers = sum(1 for t in stats.upload_page_viewers.values() if now - t <= stats.VIEWER_TIMEOUT)

    net = get_network_info()

    return {
        "wall_images_displayed": stats.wall_stats.get("images", 0),
        "wall_videos_displayed": stats.wall_stats.get("videos", 0),
        "media_images_count": media_images,
        "media_videos_count": media_videos,
        "upload_page_viewers": upload_viewers,
        "uploads_in_progress": stats.uploads_in_progress,
        "wall_connected": len(clients) > 0,
        "wall_clients": len(clients),
        "server_online_since": stats.server_start_time,
        "network_mode": net.get("mode", ""),
        "network_port": net.get("port", ""),
        "local_ip": net.get("local_ip", ""),
        "external_ip": net.get("external_ip", ""),
    }


@router.get("/api/network_test")
def network_test():

    info = get_network_info()

    port = info.get("port")
    local_ip = info.get("local_ip")
    external_ip = info.get("external_ip")

    result = {
        "local_ok": False,
        "public_ok": False,
        "local_url": f"http://{local_ip}:{port}",
        "public_url": f"http://{external_ip}:{port}" if external_ip else None,
        "port": port
    }

    # ----------------------
    # Local Test
    # ----------------------

    try:

        with socket.create_connection((local_ip, port), timeout=2):

            result["local_ok"] = True

    except:

        pass

    # ----------------------
    # Public Test
    # ----------------------

    if external_ip:

        try:

            with socket.create_connection((external_ip, port), timeout=2):

                result["public_ok"] = True

        except:

            pass

    return result


# ------------------------------------------------
# Hintergrund (Wall)
# ------------------------------------------------

BG_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


@router.get("/api/background/list")
def background_list():
    """Liste aller Hintergrundbilder im background-Ordner."""
    if not os.path.isdir(BACKGROUND_DIR):
        return []
    files = []
    for f in sorted(os.listdir(BACKGROUND_DIR)):
        if os.path.splitext(f)[1].lower() in BG_IMAGE_EXT:
            files.append(f)
    return files


@router.post("/api/background/upload")
async def background_upload(file: UploadFile = File(...)):
    """Hintergrundbild hochladen."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in BG_IMAGE_EXT:
        return {"ok": False, "error": "Nur Bilder erlaubt (jpg, png, webp, gif)"}
    safe_base = "".join(c for c in (os.path.splitext(file.filename or "image")[0]) if c.isalnum() or c in "._- ")
    if not safe_base:
        safe_base = "image"
    filename = f"{safe_base}_{uuid.uuid4().hex[:6]}{ext}"
    path = os.path.join(BACKGROUND_DIR, filename)
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20 MB
        return {"ok": False, "error": "Datei zu groß (max 20 MB)"}
    with open(path, "wb") as f:
        f.write(content)
    return {"ok": True, "filename": filename}