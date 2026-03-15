from fastapi import APIRouter, WebSocket
from fastapi.responses import HTMLResponse
import os
import json
import time

from server.main import PROJECT_DIR
from server.network import get_upload_url
from server import stats

router = APIRouter()

clients = []

UPLOAD_FOLDER = os.path.join(PROJECT_DIR, "media")
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")


# ------------------------------------------------
# Broadcast helpers
# ------------------------------------------------

async def broadcast(filename):

    dead=[]

    for ws in clients:
        try:
            await ws.send_text(filename)
        except:
            dead.append(ws)

    for d in dead:
        clients.remove(d)


async def broadcast_config():

    dead=[]

    for ws in clients:
        try:
            await ws.send_text("__config_reload__")
        except:
            dead.append(ws)

    for d in dead:
        clients.remove(d)


# ------------------------------------------------
# Websocket
# ------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()
    clients.append(websocket)

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "stats":
                    stats.wall_stats["images"] = data.get("images", 0)
                    stats.wall_stats["videos"] = data.get("videos", 0)
                    stats.wall_stats["updated"] = time.time()
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception:
        if websocket in clients:
            clients.remove(websocket)


# ------------------------------------------------
# API
# ------------------------------------------------

@router.get("/api/upload_url")
def upload_url():

    return {"url": get_upload_url()}


@router.get("/api/images")
def list_images():

    files=os.listdir(UPLOAD_FOLDER)

    media=[]

    for f in files:
        if f.lower().endswith((
            ".jpg",".jpeg",".png",".webp",".gif",
            ".mp4",".mov",".webm"
        )):
            media.append(f)

    return media


@router.get("/api/config")
def get_config():

    with open(CONFIG_FILE,"r") as f:
        return json.load(f)


@router.post("/api/config")
async def save_config(config:dict):

    with open(CONFIG_FILE,"w") as f:
        json.dump(config,f,indent=4)

    await broadcast_config()

    return {"status":"saved"}


# ------------------------------------------------
# Wall Page
# ------------------------------------------------

@router.get("/wall",response_class=HTMLResponse)
def wall():

    return """

<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<link href="https://fonts.googleapis.com/css2?family=Caveat&display=swap" rel="stylesheet">

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<style>

body{
margin:0;
overflow:hidden;
background:black;
font-family:Arial;
}

#debugOverlay{

position:absolute;
top:10px;
left:10px;

background:rgba(0,0,0,0.6);
color:white;

padding:8px 12px;
border-radius:6px;

font-size:14px;
font-family:monospace;

z-index:5000;

display:none;

}

#connectionStatus{

position:absolute;
top:10px;
right:10px;

width:14px;
height:14px;

border-radius:50%;

background:red;

box-shadow:0 0 6px rgba(0,0,0,0.6);

z-index:6000;

transition:opacity 1s;

}

.photoFrame{
position:absolute;
background:white;
border-radius:4px;
box-shadow:
0 12px 30px rgba(0,0,0,0.7),
0 4px 10px rgba(0,0,0,0.5);

pointer-events:none;

z-index:100;
}

.photoFrame img,
.photoFrame video{
display:block;
width:100%;
height:auto;
}

.photoComment{

position:absolute;
bottom:8px;
left:8px;
right:8px;

text-align:center;

font-family:'Caveat', cursive;

white-space:pre-wrap;
word-break:break-word;
line-height:1.2;

}

.highlight{
z-index:200;
}

#qrContainer{

position:absolute;
z-index:3000;

padding:14px;

background:rgba(0,0,0,0.55);

border-radius:12px;

text-align:center;

opacity:1;

transition:opacity 1s ease;

}

#banner{

position:absolute;
left:0;
right:0;

display:flex;
align-items:center;
justify-content:center;

z-index:3000;

opacity:0;

transition:opacity 1s ease;

white-space:pre-wrap;

}

.bannerContent{
display:flex;
flex-direction:column;
align-items:center;
text-align:center;
width:100%;
}

.bannerContent h1{
margin:4px 0;
font-size:2.4em;
}

.bannerContent h2{
margin:4px 0;
font-size:1.8em;
}

.bannerContent p{
margin:4px 0;
}

</style>

</head>


<body>

<div id="debugOverlay"></div>

<div id="connectionStatus"></div>

<div id="banner"></div>

<div id="qrContainer">
<div id="qrCode"></div>
<div id="qrText"></div>
</div>



<script>

let images=[]
let videos=[]
let imageHighlightQueue=[]
let videoHighlightQueue=[]
let highlightWorkerRunning=false

let knownFiles=new Set()

let config={}

let imageSlideshowTimer = null
let videoSlideshowTimer = null
let qrTimer = null
let bannerTimer = null

let currentImages=0
let currentVideos=0
let currentImageHighlights=0
let currentVideoHighlights=0
let currentCenterHighlights=0
let wallStartTime = Date.now()

let debugLogs=[]

function setConnection(state){

let icon=document.getElementById("connectionStatus")

if(!icon) return

if(state==="online"){

icon.style.background="lime"

setTimeout(()=>{
icon.style.opacity=0
},5000)

}else{

icon.style.opacity=1
icon.style.background="red"

}

}

const imageTypes=["jpg","jpeg","png","webp","gif"]
const videoTypes=["mp4","mov","webm"]

let ws=null

function connectWebSocket(){

ws=new WebSocket(
(location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws"
)

ws.onopen = () => {

setConnection("online")
sendStats()

}

ws.onclose = () => {

setConnection("offline")

setTimeout(connectWebSocket,3000)

}

ws.onerror = () => {

setConnection("offline")

}

function sendStats(){
if(ws && ws.readyState===WebSocket.OPEN){
try{ ws.send(JSON.stringify({type:"stats",images:currentImages,videos:currentVideos})) }catch(e){}
}
}
setInterval(sendStats,5000)

ws.onmessage=async(event)=>{

let msg=event.data

if(msg==="__config_reload__"){

await loadConfig()
setupQR()
return

}

addMedia(msg)

let ext=msg.split(".").pop().toLowerCase()
let isVid=videoTypes.includes(ext)
if(isVid && config.video_highlight_new){
videoHighlightQueue.push(msg)
processHighlightQueue()
}else if(!isVid && config.image_highlight_new){
imageHighlightQueue.push(msg)
processHighlightQueue()
}

}

}



function addMedia(file){

if(knownFiles.has(file)) return

knownFiles.add(file)

let ext=file.split(".").pop().toLowerCase()

if(videoTypes.includes(ext))
videos.push(file)
else
images.push(file)

}

function updateDebug(){

let box=document.getElementById("debugOverlay")

if(!config.debug_overlay){
box.style.display="none"
return
}

box.style.display="block"

box.innerHTML =
"Images: "+currentImages+" (max: "+config.max_images_on_screen+")<br>"+
"Videos: "+currentVideos+" (max: "+config.max_videos_on_screen+")<br>"+
"ImageHighlights: "+currentImageHighlights+" (Queue: "+imageHighlightQueue.length+")<br>"+
"VideoHighlights: "+currentVideoHighlights+" (Queue: "+videoHighlightQueue.length+")<br>"+
"CenterHighlights: "+currentCenterHighlights

if(debugLogs.length){
box.innerHTML += "<br>Log:<br>"+debugLogs.join("<br>")
}

}

function addDebugLog(msg){

if(!config.debug_overlay) return

let elapsed = ((Date.now()-wallStartTime)/1000).toFixed(1)
let line = "["+elapsed+"s] "+msg

debugLogs.push(line)
if(debugLogs.length>10) debugLogs.shift()

console.log("[WALL DEBUG]",line)

}


async function loadImages(){

let res=await fetch("/api/images")
let files=await res.json()

for(let f of files) addMedia(f)

}



async function loadConfig(){

let res=await fetch("/api/config")
config=await res.json()
if(imageSlideshowTimer) clearInterval(imageSlideshowTimer)
if(videoSlideshowTimer) clearInterval(videoSlideshowTimer)
if(qrTimer) clearInterval(qrTimer)
if(bannerTimer) clearInterval(bannerTimer)

applyFrameStyle()
loadCommentFont()
setupQR()
setupBanner()

// Slideshow-Timer nach Config-Änderung neu starten
imageSlideshowTimer = setInterval(showRandomImage,config.image_spawn_interval*1000)
videoSlideshowTimer = setInterval(showRandomVideo,config.video_spawn_interval*1000)

}



function applyFrameStyle(){

let style=document.createElement("style")

style.innerHTML=`

.photoFrame{

padding:${config.frame_padding_top||0}px ${config.frame_padding_side||0}px ${config.frame_padding_bottom||0}px ${config.frame_padding_side||0}px;

}

`

document.head.appendChild(style)

}



function loadCommentFont(){

let old=document.getElementById("commentFontLink")

if(old) old.remove()

let font=config.comment_font

if(!font) return

let link=document.createElement("link")

link.id="commentFontLink"

link.rel="stylesheet"

link.href="https://fonts.googleapis.com/css2?family="+encodeURIComponent(font.replace(/\s/g,"+"))+"&display=swap"

document.head.appendChild(link)

}



function setupQR(){

let box=document.getElementById("qrContainer")

if(!config.show_qr_code){

box.style.display="none"
return

}

box.style.display="block"


fetch("/api/upload_url")
.then(r=>r.json())
.then(data=>{

let qrBox=document.getElementById("qrCode")
qrBox.innerHTML=""

new QRCode(qrBox,{

text:data.url,
width:config.qr_size,
height:config.qr_size

})

})


let text=document.getElementById("qrText")

text.innerText=config.qr_text
text.style.color=config.qr_text_color
text.style.fontSize=config.qr_text_size+"px"


setQRPosition()

if(config.qr_dynamic_enabled){

cycleQR()

}

}



function setQRPosition(){

let box=document.getElementById("qrContainer")

let p=config.qr_position

box.style.top=""
box.style.bottom=""
box.style.left=""
box.style.right=""
box.style.transform=""

if(p==="center-bottom"){

box.style.left="50%"
box.style.bottom="20px"
box.style.transform="translateX(-50%)"

}

if(p==="top-left"){

box.style.top="20px"
box.style.left="20px"

}

if(p==="top-right"){

box.style.top="20px"
box.style.right="20px"

}

if(p==="bottom-left"){

box.style.bottom="20px"
box.style.left="20px"

}

if(p==="bottom-right"){

box.style.bottom="20px"
box.style.right="20px"

}

}



function cycleQR(){

let box=document.getElementById("qrContainer")

if(qrTimer) clearInterval(qrTimer)

qrTimer = setInterval(()=>{

let elapsed=(Date.now()-wallStartTime)/1000

let cycle=config.qr_show_duration+config.qr_hide_duration

let phase=elapsed%cycle

if(phase<config.qr_show_duration){
box.style.opacity=1
}else{
box.style.opacity=0
}

},500)

}



function setupBanner(){

let banner=document.getElementById("banner")

if(!config.banner_enabled){

banner.style.display="none"
return

}

banner.style.display="flex"

banner.style.background=config.banner_color
banner.style.color=config.banner_text_color
banner.style.height=config.banner_height+"px"

banner.innerHTML = "<div class='bannerContent'>" + marked.parse(config.banner_text) + "</div>"

if(config.banner_position==="top"){

banner.style.top=0

}

if(config.banner_position==="bottom"){

banner.style.bottom=0

}


cycleBanner()

}



function cycleBanner(){

let banner=document.getElementById("banner")

if(bannerTimer) clearInterval(bannerTimer)

bannerTimer = setInterval(()=>{

let elapsed=(Date.now()-wallStartTime)/1000

let cycle=config.banner_show_duration+config.banner_hide_duration

let phase=elapsed%cycle

if(phase<config.banner_show_duration){
banner.style.opacity=1
}else{
banner.style.opacity=0
}

},500)

}



function processHighlightQueue(){

if(highlightWorkerRunning) return

highlightWorkerRunning=true

let imageMax=config.image_max_simultaneous_highlights||3
let videoMax=config.video_max_simultaneous_highlights||3
let centerMax=config.center_highlight_max_simultaneous||1
let centerLimit=config.center_highlight_enabled?(currentCenterHighlights>=centerMax):false

while(
currentImageHighlights<imageMax &&
imageHighlightQueue.length>0 &&
currentImages<config.max_images_on_screen &&
!centerLimit
){

let file=imageHighlightQueue.shift()
currentImageHighlights++
if(config.center_highlight_enabled) currentCenterHighlights++
spawnMedia(file,true)
centerLimit=config.center_highlight_enabled&&(currentCenterHighlights>=centerMax)

}

while(
currentVideoHighlights<videoMax &&
videoHighlightQueue.length>0 &&
currentVideos<config.max_videos_on_screen &&
!centerLimit
){

let file=videoHighlightQueue.shift()
currentVideoHighlights++
if(config.center_highlight_enabled) currentCenterHighlights++
spawnMedia(file,true)
centerLimit=config.center_highlight_enabled&&(currentCenterHighlights>=centerMax)

}

highlightWorkerRunning=false

}



function chooseRandomImage(){

if(images.length===0) return null
return images[Math.floor(Math.random()*images.length)]

}

function chooseRandomVideo(){

if(videos.length===0) return null
return videos[Math.floor(Math.random()*videos.length)]

}


function showRandomImage(){

if(currentImages>=config.max_images_on_screen) return

let file = chooseRandomImage()

if(!file) return

spawnMedia(file,false)

}

function showRandomVideo(){

if(currentVideos>=config.max_videos_on_screen) return

let file = chooseRandomVideo()

if(!file) return

spawnMedia(file,false)

}



function spawnMedia(file,isHighlight=false){

let ext=file.split(".").pop().toLowerCase()

let isVideo = videoTypes.includes(ext)
let videoMode = config.video_playback_mode
let isLoopVideo = isVideo && videoMode === "loop"
let isBounceVideo = isVideo && videoMode === "bounce"
// Loop-ähnliche Videos: gleiche Flug-/Rotationslogik wie Loop,
// nur unterschiedliche Abspiel-Strategie (loop vs. bounce)
let isLoopLikeVideo = isLoopVideo || isBounceVideo

if(isVideo){

if(currentVideos>=config.max_videos_on_screen) return

currentVideos++

}else{

if(currentImages>=config.max_images_on_screen) return

currentImages++

}

addDebugLog("spawn "+(isVideo?"video":"image")+": "+file)


let frame=document.createElement("div")
frame.classList.add("photoFrame")

let cfg=isVideo?{
drift_strength:config.video_drift_strength,
rotation_strength:config.video_rotation_strength,
rotation_direction_mode:config.video_rotation_direction_mode,
animation_duration:config.video_animation_duration,
speed_variation_enabled:config.video_speed_variation_enabled,
speed_variation_strength:config.video_speed_variation_strength,
highlight_duration:config.video_highlight_duration,
highlight_color:config.video_highlight_color,
flight_path_mode:config.video_flight_path_mode||"random"
}:{
drift_strength:config.image_drift_strength,
rotation_strength:config.image_rotation_strength,
rotation_direction_mode:config.image_rotation_direction_mode,
animation_duration:config.image_animation_duration,
speed_variation_enabled:config.image_speed_variation_enabled,
speed_variation_strength:config.image_speed_variation_strength,
highlight_duration:config.image_highlight_duration,
highlight_color:config.image_highlight_color,
flight_path_mode:config.image_flight_path_mode||"random"
}

let drift=(Math.random()*2-1)*(window.innerWidth*(cfg.drift_strength||0.2))
let rot=Math.random()*(cfg.rotation_strength||90)
if(cfg.rotation_direction_mode==="left") rot=-Math.abs(rot)
if(cfg.rotation_direction_mode==="right") rot=Math.abs(rot)
if(cfg.rotation_direction_mode==="both") rot=(Math.random()<0.5?-1:1)*rot
let duration=cfg.animation_duration||30
if(cfg.speed_variation_enabled) duration=duration*(1+(Math.random()*2-1)*(cfg.speed_variation_strength||0.4))

let element
let loopStartTop = null
let loopFlightStarted = false
let loopRotationStarted = false
let exitWatcherStarted = false

function startExitWatcher(){

if(exitWatcherStarted) return
exitWatcherStarted = true

function check(){

if(!document.body.contains(frame)){
    return
}

let rect = frame.getBoundingClientRect()

// Entfernen, sobald der Frame klar außerhalb des sichtbaren Bereichs liegt
if(
    rect.bottom < -50 ||                    // komplett über dem Bildschirm
    rect.top    > window.innerHeight + 50 ||// weit unterhalb
    rect.right  < -50 ||                    // weit links draußen
    rect.left   > window.innerWidth + 50    // weit rechts draußen
){

    // Positionsbasierter Exit nur für Bilder, nicht für Videos
    if(!isVideo){

        frame.remove()
        currentImages--

        addDebugLog(
            "removed image after leaving screen: "+file+
            " rect="+JSON.stringify({
              top:Math.round(rect.top),
              bottom:Math.round(rect.bottom),
              left:Math.round(rect.left),
              right:Math.round(rect.right)
            })
        )
    }

    return
}

requestAnimationFrame(check)
}

requestAnimationFrame(check)
}

function startLoopFlight(startTop, size){

// Ziel deutlich oberhalb des sichtbaren Bereichs,
// damit der Exit-Watcher Videos sicher erwischt
let endTop = -size - window.innerHeight
let startTime = Date.now()
let durationMs = 90000  // 90 Sekunden für die komplette Flugbahn

function step(){

if(!document.body.contains(frame)) return

let t = (Date.now()-startTime)/durationMs
if(t>1) t=1

let y = startTop + (endTop-startTop)*t
frame.style.top = y+"px"

if(t<1) requestAnimationFrame(step)
}

requestAnimationFrame(step)
}

function startLoopRotation(initialRot){

let startTime = Date.now()
let periodMs = 20000  // eine komplette Wipp-Bewegung in 20s
let maxAngle = Math.abs(initialRot)||10

function step(){

if(!document.body.contains(frame)) return

let t = (Date.now()-startTime)/periodMs
// Sinusförmige Rotation zwischen -maxAngle und +maxAngle
let angle = Math.sin(t*2*Math.PI)*maxAngle

frame.style.transform = "rotate("+angle+"deg)"

requestAnimationFrame(step)
}

requestAnimationFrame(step)
}

function startBounceFlight(startX, startY, size, durationSec, rot){

let x = startX
let y = startY
let totalDist = window.innerHeight + 400
let velocityY = totalDist / durationSec
let velocityX = (window.innerWidth * (cfg.drift_strength||0.2)) / durationSec
if(drift<0) velocityX = -velocityX
let lastTime = performance.now()

function step(now){

if(!document.body.contains(frame)) return

let dt = (now - lastTime) / 1000
lastTime = now

x += velocityX * dt
y -= velocityY * dt

let rect = frame.getBoundingClientRect()
let w = rect.width
let h = rect.height

if(x <= 0){ velocityX = Math.abs(velocityX); x = 0 }
if(x + w >= window.innerWidth){ velocityX = -Math.abs(velocityX); x = window.innerWidth - w }

frame.style.left = x + "px"
frame.style.top = y + "px"
frame.style.transform = "rotate("+rot+"deg)"

if(y + h < -50) return

requestAnimationFrame(step)
}

requestAnimationFrame(step)
}

function startExitWatcher(){

function check(){

if(!document.body.contains(frame)){
    return
}

let rect = frame.getBoundingClientRect()

// Entfernen, sobald der Frame klar außerhalb des sichtbaren Bereichs liegt
if(
    rect.bottom < -50 ||                    // komplett über dem Bildschirm
    rect.top    > window.innerHeight + 50 ||// weit unterhalb
    rect.right  < -50 ||                    // weit links draußen
    rect.left   > window.innerWidth + 50    // weit rechts draußen
){

    // Positionsbasierter Exit jetzt für Bilder und Videos
    frame.remove()

    if(!videoTypes.includes(ext)) currentImages = Math.max(0, currentImages-1)
    if(videoTypes.includes(ext))  currentVideos = Math.max(0, currentVideos-1)

    addDebugLog(
        "removed "+(videoTypes.includes(ext)?"video":"image")+" after leaving screen: "+file+
        " rect="+JSON.stringify({
          top:Math.round(rect.top),
          bottom:Math.round(rect.bottom),
          left:Math.round(rect.left),
          right:Math.round(rect.right)
        })
    )

    return
}

requestAnimationFrame(check)
}

requestAnimationFrame(check)
}

if(isVideo){

element=document.createElement("video")


element.autoplay=true
element.muted=true
element.playsInline=true


let videoCanPlayHandled=false
element.oncanplay = () => {

if(videoCanPlayHandled) return
videoCanPlayHandled=true

frame.appendChild(element)
document.body.appendChild(frame)

element.play()

// Loop-ähnliche Videos: Fluganimation nur wenn KEIN Center Highlight
if(!useCenterHighlight && isLoopLikeVideo && loopStartTop!==null){
    if(!loopFlightStarted){
        loopFlightStarted = true
        startLoopFlight(loopStartTop, size)
    }
    if(!loopRotationStarted){
        loopRotationStarted = true
        startLoopRotation(rot)
    }
}

/* Highlight / Center Highlight */

if(isHighlight){

frame.classList.add("highlight")
frame.style.boxShadow="0 0 60px "+cfg.highlight_color

if(useCenterHighlight){

let entryMs=(config.center_highlight_entry_speed||1)*1000
let exitMs=(config.center_highlight_exit_speed||1)*1000
let centerDur=config.center_highlight_duration*1000
let mode=config.center_highlight_mode||"fly"

frame.style.transition="opacity "+entryMs+"ms ease"
requestAnimationFrame(()=>{ frame.style.opacity="1" })

setTimeout(()=>{

if(mode==="spotlight"){

frame.style.transition="opacity "+exitMs+"ms ease"
frame.style.opacity="0"
setTimeout(()=>{
frame.remove()
currentCenterHighlights=Math.max(0,currentCenterHighlights-1)
currentVideoHighlights=Math.max(0,currentVideoHighlights-1)
currentVideos=Math.max(0,currentVideos-1)
processHighlightQueue()
},exitMs)

}else{

frame.style.transition="all "+exitMs+"ms ease"
frame.style.left=startX+"px"
frame.style.top=(isLoopLikeVideo?loopStartTop:window.innerHeight)+"px"
frame.style.transform="translate(0,0) scale(1)"
frame.style.zIndex="100"

setTimeout(()=>{

frame.classList.remove("highlight")
frame.style.boxShadow=""
currentCenterHighlights=Math.max(0,currentCenterHighlights-1)
currentVideoHighlights=Math.max(0,currentVideoHighlights-1)
processHighlightQueue()

if(isLoopLikeVideo && loopStartTop!==null){
if(!loopFlightStarted){ loopFlightStarted=true; startLoopFlight(loopStartTop, size) }
if(!loopRotationStarted){ loopRotationStarted=true; startLoopRotation(rot) }
}else{
if(cfg.flight_path_mode==="bounce"){
startBounceFlight(startX, window.innerHeight, size, duration, rot)
}else{
frame.style.transition="transform "+(duration*1000)+"ms linear"
frame.style.transform="translate("+drift+"px,-"+(window.innerHeight+400)+"px) rotate("+rot+"deg)"
}
}
startExitWatcher()

},exitMs)

}

},centerDur)

}else{

setTimeout(()=>{
frame.classList.remove("highlight")
frame.style.boxShadow=""
currentVideoHighlights=Math.max(0,currentVideoHighlights-1)
processHighlightQueue()
},cfg.highlight_duration*1000)

}

}

if(!useCenterHighlight){

if(!isLoopLikeVideo){

setTimeout(()=>{

if(cfg.flight_path_mode==="bounce"){

startBounceFlight(startX, window.innerHeight, size, duration, rot)

}else{

frame.style.transition="transform "+(duration*1000)+"ms linear"

frame.style.transform =
"translate("+drift+"px,-"+(window.innerHeight+400)+"px) rotate("+rot+"deg)"

}

startExitWatcher()

},50)

}

startExitWatcher()

}

}

element.src="/media/"+file

if(config.video_playback_mode==="loop") element.loop=true

/* Bounce Video */
if(config.video_playback_mode==="bounce"){

let reversing=false

function reverseStep(){

if(!reversing) return

element.currentTime-=0.04

if(element.currentTime<=0){

reversing=false
element.currentTime=0
element.play()

return
}

requestAnimationFrame(reverseStep)

}

element.addEventListener("timeupdate",()=>{

if(!reversing && element.currentTime>=element.duration-0.08){

element.pause()
reversing=true
reverseStep()

}

})

}

}else{

element=document.createElement("img")
element.loading="eager"

element.src="/media/"+file

}



/* Kommentar */

if(config.comments_enabled){

fetch("/media/"+file.replace(/\\.[^/.]+$/,"")+".txt")
.then(r=>r.ok?r.text():"")
.then(comment=>{

if(!comment) return

let text=document.createElement("div")

text.classList.add("photoComment")

text.innerText=comment.substring(0,config.comment_max_length)

text.style.fontFamily=config.comment_font
text.style.color=config.comment_color
text.style.fontSize=config.comment_size+"px"

if(config.comment_bold) text.style.fontWeight="bold"
if(config.comment_underline) text.style.textDecoration="underline"

frame.appendChild(text)

})

}



let size=isVideo
?(config.video_min_size||100)+Math.random()*((config.video_max_size||150)-(config.video_min_size||100))
:(config.image_min_size||100)+Math.random()*((config.image_max_size||150)-(config.image_min_size||100))

frame.style.width=size+"px"


let startX=Math.random()*(window.innerWidth-size)

let useCenterHighlight=isHighlight && config.center_highlight_enabled

if(useCenterHighlight){

let centerScale=config.center_highlight_scale||1.6
let centerVar=config.center_highlight_position_variation||0
let centerOffsetX=(Math.random()*2-1)*centerVar
let centerOffsetY=(Math.random()*2-1)*centerVar

frame.style.left="50%"
frame.style.top="50%"
frame.style.transform="translate("+centerOffsetX+"px,"+centerOffsetY+"px) translate(-50%,-50%) scale("+centerScale+")"
frame.style.opacity="0"
frame.style.zIndex="400"
if(isLoopLikeVideo){
let margin=40
loopStartTop=window.innerHeight+margin
}

}else if(isLoopLikeVideo){

let margin=40
let startTop = window.innerHeight + margin
loopStartTop = startTop
frame.style.left = startX+"px"
frame.style.top  = startTop+"px"

}else{

frame.style.left=startX+"px"
frame.style.top=window.innerHeight+"px"

}


element.onload = () => {

frame.appendChild(element)
document.body.appendChild(frame)

/* Highlight / Center Highlight */

if(isHighlight){

frame.classList.add("highlight")
frame.style.boxShadow="0 0 60px "+cfg.highlight_color

if(useCenterHighlight){

let entryMs=(config.center_highlight_entry_speed||1)*1000
let exitMs=(config.center_highlight_exit_speed||1)*1000
let centerDur=config.center_highlight_duration*1000
let mode=config.center_highlight_mode||"fly"

frame.style.transition="opacity "+entryMs+"ms ease"
requestAnimationFrame(()=>{ frame.style.opacity="1" })

setTimeout(()=>{

if(mode==="spotlight"){

frame.style.transition="opacity "+exitMs+"ms ease"
frame.style.opacity="0"
setTimeout(()=>{
frame.remove()
currentCenterHighlights=Math.max(0,currentCenterHighlights-1)
currentImageHighlights=Math.max(0,currentImageHighlights-1)
currentImages=Math.max(0,currentImages-1)
processHighlightQueue()
},exitMs)

}else{

frame.style.transition="all "+exitMs+"ms ease"
frame.style.left=startX+"px"
frame.style.top=window.innerHeight+"px"
frame.style.transform="translate(0,0) scale(1)"
frame.style.zIndex="100"

setTimeout(()=>{

frame.classList.remove("highlight")
frame.style.boxShadow=""
currentCenterHighlights=Math.max(0,currentCenterHighlights-1)
currentImageHighlights=Math.max(0,currentImageHighlights-1)
processHighlightQueue()

if(cfg.flight_path_mode==="bounce"){
startBounceFlight(startX, window.innerHeight, size, duration, rot)
}else{
frame.style.transition="transform "+(duration*1000)+"ms linear"
frame.style.transform="translate("+drift+"px,-"+(window.innerHeight+400)+"px) rotate("+rot+"deg)"
}

startExitWatcher()

},exitMs)

}

},centerDur)

}else{

setTimeout(()=>{

frame.classList.remove("highlight")
frame.style.boxShadow=""

currentImageHighlights=Math.max(0,currentImageHighlights-1)

processHighlightQueue()

},cfg.highlight_duration*1000)

}

}

if(!useCenterHighlight){

setTimeout(()=>{

if(cfg.flight_path_mode==="bounce"){

startBounceFlight(startX, window.innerHeight, size, duration, rot)

}else{

frame.style.transition="transform "+(duration*1000)+"ms linear"

frame.style.transform =
"translate("+drift+"px,-"+(window.innerHeight+400)+"px) rotate("+rot+"deg)"

}

},50)

startExitWatcher()

}


}

}



async function init(){

await loadConfig()
await loadImages()

connectWebSocket()

setInterval(updateDebug,500)

/* Highlight Queue Watcher */
setInterval(processHighlightQueue,500)

}

init()

</script>

</body>

</html>

"""
