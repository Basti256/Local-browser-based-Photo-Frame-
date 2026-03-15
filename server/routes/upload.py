from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
import os
import shutil
import json
import uuid
import time

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from server.routes.wall import broadcast
from server.main import PROJECT_DIR
from server import stats

register_heif_opener()

router = APIRouter()

# ------------------------------------------------
# Paths (Projektabhängig!)
# ------------------------------------------------

UPLOAD_FOLDER = os.path.join(PROJECT_DIR, "media")
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------------------------------------
# Config Loader
# ------------------------------------------------

def load_config():

    if not os.path.exists(CONFIG_FILE):
        return {
            "upload_greeting": "Lade deine Fotos hoch ❤️",
            "upload_image": "",
            "upload_button_color": "#ff4b5c",
            "upload_allow_videos": True,
            "upload_max_files": 20,
            "upload_max_file_size_mb": 50,
        }

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------
# File Type Validation (Magic Bytes)
# ------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}

# Magic bytes für Video-Validierung
VIDEO_SIGNATURES = [
    (b"ftyp", 4),   # MP4, MOV
    (b"\x1a\x45\xdf\xa3", 0),  # WebM (EBML)
]


def is_valid_image(file_path: str) -> bool:
    """Prüft ob die Datei ein gültiges Bild ist (via PIL)."""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def is_valid_video(file_path: str) -> bool:
    """Prüft ob die Datei ein gültiges Video ist (Magic Bytes)."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(32)
        for sig, offset in VIDEO_SIGNATURES:
            if header[offset:offset + len(sig)] == sig:
                return True
        return False
    except Exception:
        return False

# ------------------------------------------------
# Unique Filename
# ------------------------------------------------

def generate_unique_filename(original_name):

    name, ext = os.path.splitext(original_name)
    unique = uuid.uuid4().hex[:6]

    return f"{name}_{unique}{ext}"

# ------------------------------------------------
# Image Processing
# ------------------------------------------------

def process_image(file_path):

    try:

        ext = os.path.splitext(file_path)[1].lower()

        img = Image.open(file_path)

        # iPhone Rotation fix
        img = ImageOps.exif_transpose(img)

        # Wenn bereits JPG → nur Rotation fix speichern
        if ext in [".jpg", ".jpeg"]:

            img = img.convert("RGB")
            img.save(file_path, "JPEG", quality=95)

            return os.path.basename(file_path)

        # sonst konvertieren
        new_path = os.path.splitext(file_path)[0] + ".jpg"

        img = img.convert("RGB")
        img.save(new_path, "JPEG", quality=95)

        if os.path.exists(new_path):
            os.remove(file_path)
            return os.path.basename(new_path)

        else:
            print("ERROR: JPEG conversion failed")
            return os.path.basename(file_path)

    except Exception as e:

        print("Image processing error:", e)

        return os.path.basename(file_path)

# ------------------------------------------------
# Upload Page
# ------------------------------------------------

@router.get("/upload", response_class=HTMLResponse)
def upload_page():

    config = load_config()

    greeting = config.get("upload_greeting", "Lade deine Fotos hoch ❤️")
    image_raw = config.get("upload_image", "")
    # Header-Bild: aus /header/ wenn kein absoluter Pfad oder URL
    image = image_raw if (image_raw.startswith("/") or image_raw.startswith("http")) else (f"/header/{image_raw}" if image_raw else "")
    button_color = config.get("upload_button_color", "#ff4b5c")
    allow_videos = config.get("upload_allow_videos", True)
    max_files = config.get("upload_max_files", 20)
    max_size_mb = config.get("upload_max_file_size_mb", 50)
    comment_max_length = config.get("comment_max_length", 80)

    # Accept-String für file input
    accept_str = "image/*" + (",video/*" if allow_videos else "")

    return f"""
<!DOCTYPE html>
<html>
<head>

<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Foto Upload</title>

<style>

body {{
font-family: system-ui;
background:#f5f7fb;
margin:0;
padding:0;
text-align:center;
}}

.container {{
max-width:700px;
margin:auto;
padding:20px;
}}

.header-img {{
max-width:100%;
border-radius:10px;
margin-bottom:15px;
}}

.upload-card {{
background:white;
padding:25px;
border-radius:12px;
box-shadow:0 6px 20px rgba(0,0,0,0.1);
}}

#previewContainer {{
display:flex;
flex-wrap:wrap;
gap:16px;
justify-content:center;
margin-top:20px;
}}

.preview {{
position:relative;
width:150px;
background:#fafafa;
padding:10px;
border-radius:10px;
box-shadow:0 3px 10px rgba(0,0,0,0.08);
}}

.preview img,
.preview video {{
width:100%;
border-radius:8px;
display:block;
}}

.comment-hint {{
font-size:12px;
color:#c00;
margin-top:16px;
margin-bottom:8px;
}}

.removeBtn {{
position:absolute;
top:6px;
right:6px;
background:#ff4b5c;
color:white;
border:none;
border-radius:50%;
width:24px;
height:24px;
cursor:pointer;
font-size:14px;
line-height:24px;
padding:0;
}}

textarea {{
width:100%;
height:50px;
margin-top:8px;
resize:none;
border-radius:6px;
border:1px solid #ddd;
padding:5px;
font-size:13px;
}}

.upload-btn {{
margin-top:20px;
margin-right:8px;
padding:12px 20px;
border:none;
border-radius:8px;
background:{button_color};
color:white;
font-size:16px;
cursor:pointer;
}}

.upload-btn:hover {{
filter:brightness(1.1);
}}

.upload-btn:disabled {{
opacity:0.7;
cursor:not-allowed;
}}

#uploadProgress {{
margin-top:15px;
font-size:14px;
color:#666;
}}

</style>

</head>

<body>

<div class="container">

{f'<img class="header-img" src="{image}">' if image else ""}

<h2>{greeting}</h2>

<div class="upload-card">

<input id="fileInput" type="file" multiple accept="{accept_str}">

<input id="cameraInput" type="file" accept="image/*" capture="environment" style="display:none">

<input id="videoInput" type="file" accept="video/*" capture="environment" style="display:none">

<br>

<button class="upload-btn" onclick="openCamera()">📷 Foto aufnehmen</button>

{"<button class=\"upload-btn\" onclick=\"openVideoCamera()\">🎬 Video aufnehmen</button>" if allow_videos else ""}

<div id="commentHint" class="comment-hint" style="display:none;"></div>
<div id="previewContainer"></div>

<div id="uploadProgress"></div>

<button id="uploadBtn" class="upload-btn" onclick="upload()">Upload starten</button>

</div>

</div>

<script>

let MAX_COMMENT_LENGTH = 80
const MAX_FILES = {max_files}
const MAX_FILE_SIZE_MB = {max_size_mb}
const ALLOW_VIDEOS = {str(allow_videos).lower()}
let selectedFiles = []

let configLoaded=false
async function loadUploadConfig(){{
if(configLoaded) return
try{{
const res=await fetch("/api/config")
const cfg=await res.json()
MAX_COMMENT_LENGTH=cfg.comment_max_length||80
configLoaded=true
}}catch(e){{ configLoaded=true }}
}}

function heartbeat(){{
fetch("/api/upload_heartbeat").catch(()=>{{}})
}}
loadUploadConfig().then(()=>{{}})
heartbeat()
setInterval(heartbeat,10000)

function openCamera(){{
document.getElementById("cameraInput").click()
}}

function openVideoCamera(){{
document.getElementById("videoInput").click()
}}

document.getElementById("cameraInput").addEventListener("change",e=>handleFiles(e.target.files).catch(()=>{{}}))
document.getElementById("videoInput").addEventListener("change",e=>handleFiles(e.target.files).catch(()=>{{}}))
document.getElementById("fileInput").addEventListener("change",e=>handleFiles(e.target.files).catch(()=>{{}}))

function isValidFile(file){{
if(file.type.startsWith("image/")) return true
if(ALLOW_VIDEOS && file.type.startsWith("video/")) return true
return false
}}

function removeFile(index){{
selectedFiles.splice(index,1)
renderPreview()
}}

function renderPreview(){{
let hint=document.getElementById("commentHint")
let container=document.getElementById("previewContainer")
container.innerHTML=""
if(selectedFiles.length>0){{
hint.textContent="Max. "+MAX_COMMENT_LENGTH+" Zeichen erlaubt"
hint.style.display="block"
}}else{{
hint.style.display="none"
}}
selectedFiles.forEach((file,index)=>{{
let div=document.createElement("div")
div.className="preview"
let remove=document.createElement("button")
remove.innerHTML="✕"
remove.className="removeBtn"
remove.onclick=()=>removeFile(index)
div.appendChild(remove)
if(file.type.startsWith("image")){{
let img=document.createElement("img")
img.src=URL.createObjectURL(file)
div.appendChild(img)
}}
if(file.type.startsWith("video")){{
let vid=document.createElement("video")
vid.src=URL.createObjectURL(file)
vid.controls=true
div.appendChild(vid)
}}
let textarea=document.createElement("textarea")
textarea.placeholder="Kommentar"
textarea.maxLength=MAX_COMMENT_LENGTH
textarea.id="comment_"+index
div.appendChild(textarea)
container.appendChild(div)
}})
}}

async function handleFiles(files){{
await loadUploadConfig()
const maxBytes = MAX_FILE_SIZE_MB * 1024 * 1024
const rejected = []
for(let f of files){{
if(!isValidFile(f)){{
rejected.push(f.name + ": Kein Bild oder Video")
}} else if(f.size > maxBytes){{
rejected.push(f.name + ": Zu groß (max " + MAX_FILE_SIZE_MB + " MB)")
}} else if(selectedFiles.length >= MAX_FILES){{
rejected.push(f.name + ": Max. " + MAX_FILES + " Dateien erlaubt")
}} else {{
selectedFiles.push(f)
}}
}}
if(rejected.length > 0){{
alert("Folgende Dateien wurden verworfen:\\n\\n" + rejected.join("\\n") + "\\n\\nBitte nur Bilder und Videos hochladen.")
}}
renderPreview()
}}

function uploadWithProgress(file, comment, onProgress){{
return new Promise((resolve, reject)=>{{
const formData = new FormData()
formData.append("file", file)
formData.append("comment", comment)
const xhr = new XMLHttpRequest()
xhr.upload.addEventListener("progress", e=>{{
if(e.lengthComputable){{
const pct = Math.round((e.loaded / e.total) * 100)
onProgress(pct)
}}
}})
xhr.addEventListener("load", ()=>{{
if(xhr.status >= 200 && xhr.status < 300) resolve()
else {{
let msg = "Upload fehlgeschlagen"
try{{ const j=JSON.parse(xhr.responseText); if(j.detail) msg=j.detail }}catch(e){{}}
reject(new Error(msg))
}}
}})
xhr.addEventListener("error", ()=>reject(new Error("Netzwerkfehler")))
xhr.open("POST", "/upload")
xhr.send(formData)
}})
}}

async function upload(){{
if(selectedFiles.length === 0){{
alert("Bitte zuerst Fotos oder Videos auswählen.")
return
}}
const btn = document.getElementById("uploadBtn")
const progressEl = document.getElementById("uploadProgress")
btn.disabled = true
const total = selectedFiles.length
let completed = 0
function updateProgress(pct){{
const overall = total > 1 ? Math.round(((completed + pct/100) / total) * 100) : pct
progressEl.textContent = "Wird hochgeladen... (" + overall + "%)"
btn.textContent = "Wird hochgeladen... (" + overall + "%)"
}}
try{{
for(let i=0;i<selectedFiles.length;i++){{
const file = selectedFiles[i]
const commentField = document.getElementById("comment_"+i)
const comment = commentField ? commentField.value : ""
await uploadWithProgress(file, comment, (pct)=>updateProgress(pct))
completed++
updateProgress(100)
}}
btn.textContent = "Upload starten"
progressEl.textContent = ""
alert("Upload erfolgreich 🎉")
location.reload()
}} catch(err){{
btn.disabled = false
btn.textContent = "Upload starten"
progressEl.textContent = ""
alert("Fehler beim Upload: " + (err.message || "Unbekannter Fehler"))
}}
}}

</script>

</body>
</html>
"""

# ------------------------------------------------
# Upload Endpoint
# ------------------------------------------------

@router.get("/api/upload_heartbeat")
def upload_heartbeat(request: Request):
    """Zählt Besucher der Upload-Seite (Heartbeat alle ~10s)."""
    ip = request.client.host if request.client else "unknown"
    stats.upload_page_viewers[ip] = time.time()
    # Alte Einträge bereinigen
    now = time.time()
    expired = [k for k, v in stats.upload_page_viewers.items() if now - v > stats.VIEWER_TIMEOUT]
    for k in expired:
        del stats.upload_page_viewers[k]
    return {"ok": True}


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    comment: str = Form("")
):

    stats.uploads_in_progress += 1
    try:
        return await _do_upload(file, comment)
    finally:
        stats.uploads_in_progress = max(0, stats.uploads_in_progress - 1)


async def _do_upload(file: UploadFile, comment: str):
    config = load_config()
    allow_videos = config.get("upload_allow_videos", True)
    max_size_mb = config.get("upload_max_file_size_mb", 50)
    max_size_bytes = max_size_mb * 1024 * 1024

    allowed_extensions = list(IMAGE_EXTENSIONS)
    if allow_videos:
        allowed_extensions.extend(VIDEO_EXTENSIONS)

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Diese Datei ist kein Bild oder Video. Bitte nur Fotos und Videos hochladen."
        )

    # Größenprüfung (Content-Length falls vorhanden)
    if file.size and file.size > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximal {max_size_mb} MB erlaubt."
        )

    filename = generate_unique_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Größenprüfung nach dem Schreiben
    if os.path.getsize(file_path) > max_size_bytes:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximal {max_size_mb} MB erlaubt."
        )

    # Inhalt validieren: Muss echtes Bild oder Video sein
    if ext in IMAGE_EXTENSIONS:
        if not is_valid_image(file_path):
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Diese Datei ist kein gültiges Bild. Bitte nur Fotos und Videos hochladen."
            )
    elif ext in VIDEO_EXTENSIONS:
        if not allow_videos:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Video-Upload ist deaktiviert.")
        if not is_valid_video(file_path):
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="Diese Datei ist kein gültiges Video. Bitte nur Fotos und Videos hochladen."
            )
    else:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Dateityp nicht erlaubt.")

    # Bildverarbeitung
    if ext in IMAGE_EXTENSIONS:
        filename = process_image(file_path)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Kommentar speichern
    if comment:
        config = load_config()
        max_len = config.get("comment_max_length", 80)
        name = os.path.splitext(filename)[0]
        comment_file = os.path.join(UPLOAD_FOLDER, name + ".txt")

        with open(comment_file,"w",encoding="utf-8") as f:
            f.write(comment[:max_len])

    # Broadcast nur wenn Datei existiert
    final_path = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(final_path):
        await broadcast(filename)
    else:
        print("ERROR: broadcast skipped, file missing:", filename)

    return {"status": "success"}