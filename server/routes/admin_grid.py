"""
Admin-HTML für Grid-Modus.

Wird von admin.py eingebunden, wenn wall_view_mode="grid".
Liefert get_admin_grid_html(net) mit der kompletten Admin-UI
für Grid-Einstellungen (Spalten, Abstände, etc.).
"""


def get_admin_grid_html(net: dict) -> str:
    """Liefert das Admin-HTML für die Grid-Ansicht."""
    return """

<!DOCTYPE html>
<html>

<head>
<title>Local-browser-based-Photo-Frame Admin (Grid)</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>

<style>
body{font-family:Arial;padding:40px;background:#f5f5f5;}
.container{background:white;padding:30px;border-radius:10px;max-width:950px;margin:auto;box-shadow:0 5px 20px rgba(0,0,0,0.15);}
h1{margin-top:0;}
.section{border-top:1px solid #ddd;margin-top:15px;padding-top:10px;}
.sectionHeader{font-size:20px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;}
.sectionContent{display:none;margin-top:15px;}
.sectionGroupTitle{font-size:22px;margin-top:25px;margin-bottom:10px;}
label{font-weight:bold;}
input,select,textarea{width:100%;padding:10px;margin-top:5px;margin-bottom:15px;}
textarea{height:120px;resize:vertical;}
.row{display:flex;align-items:center;justify-content:space-between;}
.checkbox{width:auto;transform:scale(1.3);}
.sectionInfo{background:#eef5ff;padding:10px;border-radius:6px;margin-bottom:10px;font-size:14px;}
button{background:#4CAF50;color:white;border:none;padding:15px;font-size:18px;border-radius:8px;width:100%;margin-top:25px;}
@media (max-width:600px){#status_grid{grid-template-columns:1fr !important;}}
</style>

</head>

<body>

<div class="container">

<h1>Local-browser-based-Photo-Frame Einstellungen <span id="app_version" style="font-size:0.5em;color:#666;font-weight:normal;"></span></h1>

<h2 class="sectionGroupTitle">Design</h2>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Ansicht <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Wählt die Darstellungsart. Nach dem Speichern werden Admin und Wall neu geladen.</div>
<label>Design</label>
<select id="wall_view_mode">
<option value="fly">Fliegend (Bilder fliegen über den Bildschirm)</option>
<option value="grid">Grid (Bilder nebeneinander)</option>
</select>
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Grid <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Mehrere Spalten mit Bildern. Jede Spalte wird von unten mit Bildern gefüllt, die nach oben durchlaufen. Durchlaufzeit = Zeit für eine Spalte von ganz unten bis ganz oben.</div>
<label>Spalten (gleichzeitig sichtbare Bilder)</label>
<input id="grid_columns" placeholder="4" type="number">
<label>Durchlaufzeit (Sekunden bis Bild oben verschwindet)</label>
<input id="grid_animation_duration" placeholder="8" type="number">
<label>Abstand zwischen Spalten (px)</label>
<input id="grid_spacing_columns" placeholder="20" type="number">
<label>Abstand zwischen Zeilen (px)</label>
<input id="grid_spacing_rows" placeholder="0" type="number">
<div class="row"><label>Fotorahmen anzeigen</label><input type="checkbox" id="grid_show_frames" class="checkbox"></div>
<label>Rahmen Innenabstand oben (px)</label>
<input id="frame_padding_top" placeholder="12" type="number">
<label>Rahmen Innenabstand seitlich (px)</label>
<input id="frame_padding_side" placeholder="12" type="number">
<label>Rahmen Innenabstand unten (px)</label>
<input id="frame_padding_bottom" placeholder="50" type="number">
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Hintergrund <span>▼</span></div>
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

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">QR Code <span>▼</span></div>
<div class="sectionContent">
<div class="row"><label>QR Code anzeigen</label><input type="checkbox" id="qr_show" class="checkbox"></div>
<label>QR Text</label><input id="qr_text">
<label>QR Größe</label><input id="qr_size">
<label>QR Textgröße</label><input id="qr_text_size">
<label>QR Position</label>
<select id="qr_position">
<option value="center-bottom">unten mittig</option>
<option value="top-left">oben links</option>
<option value="top-right">oben rechts</option>
<option value="bottom-left">unten links</option>
<option value="bottom-right">unten rechts</option>
</select>
<label>QR Textfarbe</label><input type="color" id="qr_text_color">
<div class="row"><label>Dynamischer QR Code</label><input type="checkbox" id="qr_dynamic" class="checkbox"></div>
<label>QR Anzeige Dauer</label><input id="qr_show_duration">
<label>QR Pause Dauer</label><input id="qr_hide_duration">
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Banner <span>▼</span></div>
<div class="sectionContent">
<div class="row"><label>Banner aktiv</label><input type="checkbox" id="banner_enabled" class="checkbox"></div>
<label>Banner Text (Markdown)</label><textarea id="banner_text"></textarea>
<label>Banner Position</label>
<select id="banner_position"><option value="top">Oben</option><option value="bottom">Unten</option></select>
<label>Banner Höhe</label><input id="banner_height">
<label>Banner Farbe</label><input type="color" id="banner_color">
<label>Banner Textfarbe</label><input type="color" id="banner_text_color">
<label>Banner Anzeige Dauer</label><input id="banner_show_duration">
<label>Banner Pause Dauer</label><input id="banner_hide_duration">
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Bildtext unter den Fotos <span>▼</span></div>
<div class="sectionContent">
<div class="row"><label>Bildtext anzeigen</label><input type="checkbox" id="comments_enabled" class="checkbox"></div>
<label>Textfarbe</label><input type="color" id="comment_color">
<label>Schriftart</label><input id="comment_font" placeholder="Pacifico">
<label>Schriftgröße (px)</label><input id="comment_size" placeholder="22" type="number">
<label>Max. Zeichen pro Kommentar</label><input id="comment_max_length" placeholder="80" type="number">
<div class="row"><label>Fett</label><input type="checkbox" id="comment_bold" class="checkbox"></div>
<div class="row"><label>Unterstrichen</label><input type="checkbox" id="comment_underline" class="checkbox"></div>
</div>
</div>

<h2 class="sectionGroupTitle">Erweitert</h2>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Netzwerk <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Steuert, wer und wie auf den Server zugreifen kann.</div>
<label>Netzwerkmodus</label>
<select id="network_mode">
<option value="local">Local (nur dieser Computer)</option>
<option value="network">Network (im WLAN sichtbar)</option>
<option value="public">Public Internet (Router Port Forward)</option>
<option value="tunnel">Public Internet (Cloudflare Tunnel)</option>
</select>
<div id="network_info" style="margin-top:15px;padding:10px;border:1px solid #ccc;"><b>Network Info</b><div id="network_details">lädt...</div></div>
<button onclick="testNetwork()" style="margin-bottom:10px;">Verbindung testen</button>
<div id="network_test_result" style="margin-top:10px;background:#eef5ff;padding:10px;border-radius:6px;font-family:monospace;font-size:14px;"></div>
<label>Public Base URL</label>
<input id="public_base_url">
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Tunnel-Verwaltung <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Cloudflare-Tunnel stellt die Wand ohne eigene Router-Konfiguration über das Internet bereit.</div>
<p>Tunnel-Status: <span id="tunnel_status">...</span></p>
<button onclick="startTunnel()">Tunnel starten</button>
<button onclick="stopTunnel()">Tunnel stoppen</button>
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Extras <span>▼</span></div>
<div class="sectionContent">
<div class="row"><label>Bildschirm wach halten (Wake Lock API)</label><input type="checkbox" id="screen_wake_lock" class="checkbox"></div>
<div class="sectionInfo" style="margin-top:5px;">Funktioniert in Chrome und einigen anderen Browsern.</div>
<div class="row"><label>Alternative Wachfunktion (Video-Fallback)</label><input type="checkbox" id="screen_wake_lock_alternative" class="checkbox"></div>
<div class="sectionInfo" style="margin-top:5px;">Spielt ein unsichtbares Video. Funktioniert in Edge, Firefox und älteren Browsern.</div>
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Debug <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Zeigt ein technisches Overlay mit Status-Informationen zur Wand.</div>
<div class="row"><label>Debug Overlay anzeigen</label><input type="checkbox" id="debug_overlay" class="checkbox"></div>
</div>
</div>

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Media-Cache <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Lädt Bilder und Videos beim ersten Abruf in den Browser-Cache. Bei Verbindungsabbruch werden sie aus dem Cache geladen (Fallback). TTL = wie lange Einträge gültig bleiben.</div>
<div class="row"><label>Cache aktivieren</label><input type="checkbox" id="cache_enabled" class="checkbox"></div>
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

<div class="section">
<div class="sectionHeader" onclick="toggleSection(this)">Upload-Seite <span>▼</span></div>
<div class="sectionContent">
<div class="sectionInfo">Einstellungen für die Upload-Seite, auf die Gäste über den QR-Code zugreifen.</div>
<label>Angezeigter Text</label>
<input id="upload_greeting" placeholder="Lade deine Fotos hoch ❤️">
<label>Button-Farbe</label>
<input type="color" id="upload_button_color">
<label>Header-Bild (optional)</label>
<input id="upload_image" placeholder="header.jpg">
<div class="row"><label>Videos hochladen erlauben</label><input type="checkbox" id="upload_allow_videos" class="checkbox"></div>
<label>Max. Anzahl Dateien pro Upload</label>
<input id="upload_max_files" placeholder="20" type="number">
<label>Max. Dateigröße (MB)</label>
<input id="upload_max_file_size_mb" placeholder="50" type="number">
</div>
</div>

<button onclick="save()">Einstellungen speichern</button>

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
Bilder hochgeladen: <span id="stat_media_images">–</span><br>
Upload-Seite offen: <span id="stat_upload_viewers">–</span><br>
</div>
</div>
<b>Upload QR-Code</b><br>
<div id="qr_code" style="width:220px;height:220px;margin-top:10px;border:1px solid #ccc;padding:10px;background:white;border-radius:8px;"></div>
<br><br>
<button onclick="window.open('""" + net.get("upload_url","") + """','_blank')" style="margin-bottom:10px;">Upload Seite öffnen</button>
<button onclick="window.open('""" + net.get("wall_url","") + """','_blank')">Wall öffnen</button>
</div>

</div>

<script>

async function updateNetworkInfo(){
let res=await fetch("/api/config")
let cfg=await res.json()
let mode=cfg.network_mode
let port=cfg.port
let res2=await fetch("/api/tunnel/status")
let tunnel=await res2.json()
let txt=""
if(mode==="local") txt="Server nur lokal erreichbar."
if(mode==="network") txt="Server im lokalen Netzwerk erreichbar.<br>Firewall Port muss geöffnet sein."
if(mode==="public") txt="Öffentlicher Zugriff über Router Port Forward.<br>Router Port: "+port
if(mode==="tunnel") txt=tunnel.running?"Tunnel aktiv:<br>"+tunnel.url:"Tunnel startet..."
document.getElementById("network_details").innerHTML=txt
}
setInterval(updateNetworkInfo,2000)
updateNetworkInfo()

async function updateStatusOverview(){
try{
let res=await fetch("/api/admin/stats")
if(!res.ok) return
let s=await res.json()
document.getElementById("stat_mode").textContent=s.network_mode||"–"
document.getElementById("stat_port").textContent=s.network_port||"–"
document.getElementById("stat_local_ip").textContent=s.local_ip||"–"
document.getElementById("stat_external_ip").textContent=s.external_ip||"–"
document.getElementById("stat_online_since").textContent=s.server_online_since?new Date(s.server_online_since*1000).toLocaleString("de-DE"):"–"
document.getElementById("stat_wall_connected").textContent=s.wall_connected?"Ja ("+s.wall_clients+")":"Nein"
document.getElementById("stat_images_displayed").textContent=s.wall_images_displayed??"–"
document.getElementById("stat_media_images").textContent=s.media_images_count??"–"
document.getElementById("stat_upload_viewers").textContent=s.upload_page_viewers??"–"
}catch(e){}
}
setInterval(updateStatusOverview,2000)
updateStatusOverview()

async function renderUploadQR(){
try{
let res=await fetch("/api/upload_url")
if(!res.ok) return
let data=await res.json()
let box=document.getElementById("qr_code")
if(!box) return
box.innerHTML=""
new QRCode(box,{text:data.url||"",width:200,height:200})
}catch(e){}
}

function toggleSection(header){
let content=header.nextElementSibling
content.style.display=content.style.display==="block"?"none":"block"
}

function updateBackgroundModeVisibility(){
let mode=document.getElementById("background_mode").value
document.getElementById("background_color_row").style.display=mode==="color"?"block":"none"
document.getElementById("background_image_row").style.display=mode==="image"?"block":"none"
}
async function loadBackgroundList(){
let sel=document.getElementById("background_image")
let cur=sel.value
sel.innerHTML='<option value="">– Bild auswählen –</option>'
try{
let res=await fetch("/api/background/list")
let files=await res.json()
for(let f of files){let o=document.createElement("option");o.value=f;o.textContent=f;sel.appendChild(o)}
if(cur) sel.value=cur
}catch(e){}
}
function updateBackgroundPreview(){
let sel=document.getElementById("background_image")
let prev=document.getElementById("background_image_preview")
if(!sel||!prev) return
if(!sel.value){prev.style.backgroundImage="";prev.style.background="#333";return}
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
if(bgColor) bgColor.oninput=()=>{if(bgHex) bgHex.value=bgColor.value}
if(bgHex) bgHex.oninput=()=>{if(/^#[0-9A-Fa-f]{6}$/.test(bgHex.value)) bgColor.value=bgHex.value}
if(bgImage) bgImage.onchange=updateBackgroundPreview
if(bgUploadBtn&&bgUploadInput) bgUploadBtn.onclick=async()=>{
if(!bgUploadInput.files||!bgUploadInput.files[0]){alert("Bitte zuerst ein Bild auswählen");return}
let fd=new FormData()
fd.append("file",bgUploadInput.files[0])
try{
let r=await fetch("/api/background/upload",{method:"POST",body:fd})
let d=await r.json()
if(d.ok){await loadBackgroundList();bgImage.value=d.filename;updateBackgroundPreview();bgUploadInput.value=""}
else alert(d.error||"Upload fehlgeschlagen")
}catch(e){alert("Upload fehlgeschlagen")}
}
})

let config={}

async function load(){
let res=await fetch("/api/config")
config=await res.json()

network_mode.value=config.network_mode
public_base_url.value=config.public_base_url

wall_view_mode.value=config.wall_view_mode||"grid"

grid_columns.value=config.grid_columns||4
grid_animation_duration.value=config.grid_animation_duration||config.grid_interval||8
grid_spacing_columns.value=config.grid_spacing_columns||config.grid_spacing_rows||20
grid_spacing_rows.value=config.grid_spacing_rows||config.grid_spacing||0
grid_show_frames.checked=config.grid_show_frames!==false
frame_padding_top.value=config.frame_padding_top||12
frame_padding_side.value=config.frame_padding_side||12
frame_padding_bottom.value=config.frame_padding_bottom||50

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

let bgMode=document.getElementById("background_mode")
let bgColor=document.getElementById("background_color")
let bgColorHex=document.getElementById("background_color_hex")
let bgImage=document.getElementById("background_image")
if(bgMode) bgMode.value=config.background_mode||"color"
if(bgColor) bgColor.value=config.background_color||"#000000"
if(bgColorHex) bgColorHex.value=config.background_color||"#000000"
if(bgImage) bgImage.value=config.background_image||""
updateBackgroundModeVisibility()
await loadBackgroundList()
updateBackgroundPreview()

comments_enabled.checked=config.comments_enabled!==false
comment_color.value=config.comment_color||"#e51515"
comment_font.value=config.comment_font||"Pacifico"
comment_size.value=config.comment_size||22
comment_max_length.value=config.comment_max_length||80
comment_bold.checked=config.comment_bold||false
comment_underline.checked=config.comment_underline||false

upload_greeting.value=config.upload_greeting||"Lade deine Fotos hoch ❤️"
upload_button_color.value=config.upload_button_color||"#ff4b5c"
upload_image.value=config.upload_image||""
upload_allow_videos.checked=config.upload_allow_videos!==false
upload_max_files.value=config.upload_max_files||20
upload_max_file_size_mb.value=config.upload_max_file_size_mb||50

debug_overlay.checked=config.debug_overlay||false
let swl=document.getElementById("screen_wake_lock");if(swl) swl.checked=config.screen_wake_lock_enabled||false
let swlAlt=document.getElementById("screen_wake_lock_alternative");if(swlAlt) swlAlt.checked=config.screen_wake_lock_alternative||false
cache_enabled.checked=config.cache_enabled||false
cache_ttl_minutes.value=config.cache_ttl_minutes||30
}

async function save(){
function toFloat(v,f){let x=parseFloat(v);return isNaN(x)?f:x}
function toInt(v,f){let x=parseInt(v);return isNaN(x)?f:x}

let res=await fetch("/api/config")
let cfg=await res.json()

cfg.wall_view_mode=wall_view_mode.value
cfg.grid_columns=toInt(grid_columns.value,cfg.grid_columns||4)
cfg.grid_animation_duration=toFloat(grid_animation_duration.value,cfg.grid_animation_duration||cfg.grid_interval||8)
cfg.grid_spacing_columns=toInt(grid_spacing_columns.value,cfg.grid_spacing_columns||cfg.grid_spacing_rows||20)
cfg.grid_spacing_rows=toInt(grid_spacing_rows.value,cfg.grid_spacing_rows||cfg.grid_spacing||0)
cfg.grid_show_frames=grid_show_frames.checked
cfg.frame_padding_top=toInt(frame_padding_top.value,cfg.frame_padding_top||12)
cfg.frame_padding_side=toInt(frame_padding_side.value,cfg.frame_padding_side||12)
cfg.frame_padding_bottom=toInt(frame_padding_bottom.value,cfg.frame_padding_bottom||50)

cfg.network_mode=network_mode.value
cfg.public_base_url=public_base_url.value

cfg.show_qr_code=qr_show.checked
cfg.qr_text=qr_text.value
cfg.qr_size=toInt(qr_size.value,cfg.qr_size||220)
cfg.qr_text_size=toInt(qr_text_size.value,cfg.qr_text_size||24)
cfg.qr_position=qr_position.value
cfg.qr_text_color=qr_text_color.value
cfg.qr_dynamic_enabled=qr_dynamic.checked
cfg.qr_show_duration=toFloat(qr_show_duration.value,cfg.qr_show_duration||5)
cfg.qr_hide_duration=toFloat(qr_hide_duration.value,cfg.qr_hide_duration||5)

cfg.banner_enabled=banner_enabled.checked
cfg.banner_text=banner_text.value.replace(/\\r\\n/g,"\\n")
cfg.banner_position=banner_position.value
cfg.banner_height=toInt(banner_height.value,cfg.banner_height||120)
cfg.banner_color=banner_color.value
cfg.banner_text_color=banner_text_color.value
cfg.banner_show_duration=toFloat(banner_show_duration.value,cfg.banner_show_duration||10)
cfg.banner_hide_duration=toFloat(banner_hide_duration.value,cfg.banner_hide_duration||10)

let bgModeEl=document.getElementById("background_mode")
let bgColorEl=document.getElementById("background_color")
let bgImageEl=document.getElementById("background_image")
cfg.background_mode=bgModeEl?bgModeEl.value:"color"
cfg.background_color=bgColorEl?bgColorEl.value:"#000000"
cfg.background_image=(bgModeEl&&bgModeEl.value==="image"&&bgImageEl)?bgImageEl.value:""

cfg.comments_enabled=comments_enabled.checked
cfg.comment_color=comment_color.value||"#e51515"
cfg.comment_font=comment_font.value||"Pacifico"
cfg.comment_size=toInt(comment_size.value,cfg.comment_size||22)
cfg.comment_max_length=toInt(comment_max_length.value,cfg.comment_max_length||80)
cfg.comment_bold=comment_bold.checked
cfg.comment_underline=comment_underline.checked

cfg.upload_greeting=upload_greeting.value||"Lade deine Fotos hoch ❤️"
cfg.upload_button_color=upload_button_color.value||"#ff4b5c"
cfg.upload_image=upload_image.value||""
cfg.upload_allow_videos=upload_allow_videos.checked
cfg.upload_max_files=toInt(upload_max_files.value,cfg.upload_max_files||20)
cfg.upload_max_file_size_mb=toInt(upload_max_file_size_mb.value,cfg.upload_max_file_size_mb||50)

cfg.debug_overlay=debug_overlay.checked
let swlCb=document.getElementById("screen_wake_lock");cfg.screen_wake_lock_enabled=swlCb?swlCb.checked:false
let swlAltCb=document.getElementById("screen_wake_lock_alternative");cfg.screen_wake_lock_alternative=swlAltCb?swlAltCb.checked:false
cfg.cache_enabled=cache_enabled.checked
cfg.cache_ttl_minutes=toInt(cache_ttl_minutes.value,cfg.cache_ttl_minutes||30)
cfg.cache_max_images=toInt(cache_max_images.value,cfg.cache_max_images||100)
cfg.cache_max_videos=toInt(cache_max_videos.value,cfg.cache_max_videos||20)
cfg.cache_max_size_mb=toInt(cache_max_size_mb.value,cfg.cache_max_size_mb||500)

let saveRes=await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(cfg)})
let saveData=await saveRes.json()
if(saveData.view_changed){
alert("Einstellungen gespeichert. Ansicht geändert – Admin und Wall werden neu geladen.")
location.reload()
}else{
alert("Einstellungen gespeichert.")
}
}

async function testNetwork(){
let res=await fetch("/api/network_test")
let data=await res.json()
let box=document.getElementById("network_test_result")
let txt="Local URL: "+data.local_url+"<br>"
if(data.local_ok) txt+="Local Test: OK<br>"
else txt+="Local Test: NICHT erreichbar<br>Mögliche Ursache: Firewall blockiert Port "+data.port+"<br>"
if(data.public_url){
txt+="<br>Public URL: "+data.public_url+"<br>"
if(data.public_ok) txt+="Public Test: OK<br>"
else txt+="Public Test: NICHT erreichbar<br>Router Portfreigabe nötig: TCP "+data.port+" → Server IP"
}
box.innerHTML=txt
}

async function updateTunnel(){
let res=await fetch("/api/tunnel/status")
let data=await res.json()
let el=document.getElementById("tunnel_url")
el.innerHTML=data.running&&data.url?`<a href="${data.url}" target="_blank">${data.url}</a>`:"Tunnel nicht aktiv"
}
setInterval(updateTunnel,2000)
updateTunnel()

async function updateTunnelStatus(){
const res=await fetch("/api/tunnel/status")
if(!res.ok){document.getElementById("tunnel_status").innerText="Unavailable";return}
const data=await res.json()
document.getElementById("tunnel_status").innerText=data.running?"Running":"Stopped"
}
async function startTunnel(){await fetch("/api/tunnel/start",{method:"POST"});await updateTunnelStatus()}
async function stopTunnel(){await fetch("/api/tunnel/stop",{method:"POST"});await updateTunnelStatus()}
updateTunnelStatus()

load()
renderUploadQR()
fetch("/api/version").then(r=>r.json()).then(d=>{
let el=document.getElementById("app_version")
if(el) el.textContent="v"+d.version
}).catch(()=>{})

</script>

</body>
</html>

"""
