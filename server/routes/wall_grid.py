"""
Wall Grid-Modus: Spalten-Layout für den Local-browser-based-Photo-Frame.

Mehrere Spalten, jede Spalte wird von unten mit Bildern gefüllt.
Bilder laufen nach oben durch. Wird von wall.py eingebunden, wenn
wall_view_mode="grid". Liefert get_grid_html() mit komplettem HTML+JS.
"""


def get_grid_html() -> str:
    """Liefert das HTML für die Grid-Ansicht."""
    return """

<!DOCTYPE html>
<html>

<head>
<meta charset="UTF-8">

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

#gridContainer{
position:absolute;
top:0;
left:0;
right:0;
bottom:0;
pointer-events:none;
z-index:50;
background:#000;
}

.gridCell{
position:absolute;
z-index:100;
box-sizing:border-box;
display:flex;
flex-direction:column;
margin:0;
padding:0;
}

.gridCellInner{
position:relative;
background:white;
border-radius:4px;
box-shadow:0 4px 15px rgba(0,0,0,0.5);
overflow:hidden;
flex-shrink:0;
margin:0;
}

.gridCell img{
display:block;
width:100%;
height:auto;
margin:0;
padding:0;
}

.gridCell.from-cache{
outline:4px solid #ff6600;
outline-offset:3px;
box-shadow:0 0 16px rgba(255,102,0,0.8);
z-index:150;
}

.frameDebugFilename{
position:absolute;
bottom:4px;
left:4px;
right:4px;
font-size:10px;
color:#fff;
background:rgba(0,0,0,0.8);
padding:2px 6px;
text-align:center;
overflow:hidden;
text-overflow:ellipsis;
white-space:nowrap;
z-index:10;
}

.gridCellSpacer{
display:block;
width:100%;
flex-shrink:0;
}
</style>

</head>

<body>

<div id="debugOverlay"></div>

<div id="connectionStatus"></div>

<div id="gridContainer"></div>

<script>

let images=[]
let config={}
let ws=null

let wallStartTime=Date.now()
let debugLogs=[]

const imageTypes=["jpg","jpeg","png","webp","gif"]

let serverStateChannel=null
let serverOnline=true
let wakeLockSentinel=null
let wakeLockActive=false
let altWakeLockVideo=null
let altWakeLockCanvas=null
let altWakeLockActive=false
let altWakeLockTick=null
let cachedImages=new Set()
let lastConnectionBroadcast=0
const CONNECTION_BROADCAST_DEBOUNCE_MS=500

function setConnection(state){
let icon=document.getElementById("connectionStatus")
if(!icon) return
serverOnline=state==="online"
if(state==="online"){
icon.style.background="lime"
setTimeout(()=>{ icon.style.opacity=0 },5000)
}else{
icon.style.opacity=1
icon.style.background="red"
}
if(config&&config.cache_enabled){
if(!serverStateChannel) serverStateChannel=new BroadcastChannel("wall-server-state")
const now=Date.now()
if(now-lastConnectionBroadcast<CONNECTION_BROADCAST_DEBOUNCE_MS) return
lastConnectionBroadcast=now
serverStateChannel.postMessage({state:state})
}
}

function addDebugLog(msg){
if(!config.debug_overlay) return
let elapsed=((Date.now()-wallStartTime)/1000).toFixed(1)
let line="["+elapsed+"s] "+msg
if(debugLogs.length>0&&debugLogs[debugLogs.length-1].replace(/\[\d+\.\d+s\] /,"")===msg) return
debugLogs.push(line)
if(debugLogs.length>10) debugLogs.shift()
console.log("[WALL GRID DEBUG]",line)
}

function updateDebug(){
let box=document.getElementById("debugOverlay")
document.body.classList.toggle("debug-mode",!!config.debug_overlay)
document.querySelectorAll(".frameDebugFilename").forEach(el=>{el.style.display=config.debug_overlay?"block":"none"})
if(!config.debug_overlay){
box.style.display="none"
return
}
box.style.display="block"
let cols=Math.max(1,parseInt(config.grid_columns)||4)
let duration=parseFloat(config.grid_animation_duration||config.grid_interval)||8
let total=0
document.querySelectorAll(".gridCell").forEach(c=>{ if(c.dataset.colIndex!==undefined) total++ })
let spCol="grid_spacing_columns"in config?Math.max(0,parseInt(config.grid_spacing_columns)||0):(config.grid_spacing_rows!=null?Math.max(0,parseInt(config.grid_spacing_rows)||0):20)
let spRow="grid_spacing_rows"in config?Math.max(0,parseInt(config.grid_spacing_rows)||0):(config.grid_spacing!=null?Math.max(0,parseInt(config.grid_spacing)||0):0)
let cacheOn=config.cache_enabled?"aktiv":"aus"
let cacheTtl=config.cache_ttl_minutes||30
let wakeLockEnabled=config.screen_wake_lock_enabled
let altWakeEnabled=config.screen_wake_lock_alternative
let wakeLockStatus="aus"
if(wakeLockEnabled&&wakeLockActive) wakeLockStatus="aktiv (Wake Lock)"
else if(altWakeEnabled&&altWakeLockActive) wakeLockStatus="aktiv (Alternative)"
else if(wakeLockEnabled) wakeLockStatus="aktiv (Wake Lock, API nicht verfügbar)"
else if(altWakeEnabled) wakeLockStatus="aktiv (Alternative, nicht verfügbar)"
box.innerHTML=
"Grid Mode<br>"+
"Spalten: "+cols+" | Abstand Spalten: "+spCol+"px | Abstand Zeilen: "+spRow+"px<br>"+
"Bilder gesamt: "+total+"<br>"+
"Durchlaufzeit: "+duration+"s<br>"+
"Pool: "+images.length+" (Wiederholung erlaubt)<br>"+
"Cache: "+cacheOn+(config.cache_enabled?" (TTL "+cacheTtl+"min)":"")+"<br>"+
"Bildschirm wach: "+wakeLockStatus
if(debugLogs.length){
box.innerHTML+="<br>Log:<br>"+debugLogs.join("<br>")
}
}

let reconnectTimeout=null
function connectWebSocket(){
ws=new WebSocket((location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws")
ws.onopen=()=>{ setConnection("online"); sendStats() }
ws.onclose=()=>{
setConnection("offline")
if(reconnectTimeout) clearTimeout(reconnectTimeout)
reconnectTimeout=setTimeout(()=>{
reconnectTimeout=null
connectWebSocket()
},3000)
}
ws.onerror=()=>{ setConnection("offline") }

function sendStats(){
if(ws&&ws.readyState===WebSocket.OPEN){
let n=document.querySelectorAll(".gridCell").length
try{ ws.send(JSON.stringify({type:"stats",images:n,videos:0})) }catch(e){}
}
}
setInterval(sendStats,5000)

function markFromCache(file){
if(!config.debug_overlay) return
const fn=(file||"").split("?")[0]
function tryMark(){
document.querySelectorAll(".gridCell").forEach(c=>{
if((c.dataset.file||"").split("?")[0]===fn) c.classList.add("from-cache")
})
}
tryMark()
setTimeout(tryMark,100)
setTimeout(tryMark,400)
}
let lastCacheLog={}
const CACHE_LOG_DEBOUNCE_MS=1000
if("serviceWorker"in navigator){
navigator.serviceWorker.addEventListener("message",e=>{
if(e.data&&e.data.type==="cache_serve"){
const key="serve:"+e.data.file
if(Date.now()-(lastCacheLog[key]||0)<CACHE_LOG_DEBOUNCE_MS) return
lastCacheLog[key]=Date.now()
addDebugLog("Cache geladen: "+e.data.file+(e.data.expired?" (abgelaufen)":""))
cachedImages.add((e.data.file||"").split("?")[0])
markFromCache(e.data.file)
}else if(e.data&&e.data.type==="cache_store"){
const key="store:"+e.data.file
if(Date.now()-(lastCacheLog[key]||0)<CACHE_LOG_DEBOUNCE_MS) return
lastCacheLog[key]=Date.now()
addDebugLog("Cache gespeichert: "+e.data.file)
cachedImages.add((e.data.file||"").split("?")[0])
}else if(e.data&&e.data.type==="cache_list"){
const list=e.data.files||[]
list.forEach(f=>cachedImages.add((f||"").split("?")[0]))
if(config.debug_overlay&&list.length>0){
const key="cache_list"
if(Date.now()-(lastCacheLog[key]||0)<CACHE_LOG_DEBOUNCE_MS) return
lastCacheLog[key]=Date.now()
addDebugLog("Cache-Liste: "+list.length+" Bilder verfügbar")
}
}
})
}
ws.onmessage=async(event)=>{
if(event.data==="__config_reload__"){ location.reload(); return }
if(event.data==="__config_updated__"){
let r=await fetch("/api/config"); config=await r.json()
applyBackground()
applyWakeLock()
await updateCacheSw()
return
}
let file=event.data
if(file&&!images.includes(file)){
let ext=file.split(".").pop().toLowerCase()
if(imageTypes.includes(ext)){ images.push(file); addDebugLog("new image: "+file) }
}
}
}

function addMedia(file){
if(images.includes(file)) return
let ext=file.split(".").pop().toLowerCase()
if(imageTypes.includes(ext)) images.push(file)
}

let reservedImages=new Set()
function getDisplayedImages(){
return new Set(Array.from(document.querySelectorAll(".gridCell")).map(c=>c.dataset.file).filter(Boolean))
}
function chooseRandomImage(){
if(images.length===0) return null
let displayed=getDisplayedImages()
let pool=images
if(config.cache_enabled&&!serverOnline&&cachedImages.size>0){
pool=images.filter(f=>cachedImages.has(f.split("?")[0]))
if(pool.length===0) return null
}
let available=pool.filter(f=>!displayed.has(f)&&!reservedImages.has(f))
if(available.length===0) return null
let chosen=available[Math.floor(Math.random()*available.length)]
reservedImages.add(chosen)
return chosen
}

function spawnImage(colIndex,spawnTop){
let file=chooseRandomImage()
if(!file) return

addDebugLog("spawn col "+colIndex+": "+file)

let cols=Math.max(1,parseInt(config.grid_columns)||4)
let spacingCol="grid_spacing_columns"in config?Math.max(0,parseInt(config.grid_spacing_columns)||0):(config.grid_spacing_rows!=null?Math.max(0,parseInt(config.grid_spacing_rows)||0):20)
let spacingRow="grid_spacing_rows"in config?Math.max(0,parseInt(config.grid_spacing_rows)||0):(config.grid_spacing!=null?Math.max(0,parseInt(config.grid_spacing)||0):0)
let colWidth=Math.max(1,(window.innerWidth-(cols-1)*spacingCol)/cols)
let size=colWidth
let startX=colIndex*(colWidth+spacingCol)

let cell=document.createElement("div")
cell.className="gridCell"
cell.dataset.file=file
cell.dataset.colIndex=colIndex

let inner=document.createElement("div")
inner.className="gridCellInner"

let img=document.createElement("img")
img.loading="eager"
img.src="/media/"+file
inner.appendChild(img)
let dbg=document.createElement("div")
dbg.className="frameDebugFilename"
dbg.textContent=file
inner.appendChild(dbg)

if(config.grid_show_frames!==false){
let padT=config.frame_padding_top||0
let padS=config.frame_padding_side||0
let padB=config.frame_padding_bottom||0
inner.style.padding=padT+"px "+padS+"px "+padB+"px "+padS+"px"
inner.style.boxSizing="border-box"
if(spacingCol>0||spacingRow>0){
inner.style.boxShadow="0 4px 15px rgba(0,0,0,0.5)"
}else{
inner.style.boxShadow="none"
}
}else{
inner.style.background="transparent"
inner.style.boxShadow="none"
}

cell.appendChild(inner)

if(spacingRow>0){
let spacer=document.createElement("div")
spacer.className="gridCellSpacer"
spacer.style.height=spacingRow+"px"
spacer.style.minHeight=spacingRow+"px"
cell.appendChild(spacer)
}

let startY=spawnTop!=null?spawnTop:window.innerHeight+50

cell.style.width=size+"px"
cell.style.left=startX+"px"
cell.style.top=startY+"px"

document.getElementById("gridContainer").appendChild(cell)

let duration=(parseFloat(config.grid_animation_duration||config.grid_interval)||8)*1000
let travelDist=window.innerHeight+200
let speedPxPerSec=travelDist/(duration/1000)

let spawnTime=Date.now()

function startAnimation(){
let loadDelay=Date.now()-spawnTime
let startTime=Date.now()-loadDelay

function animate(){
if(!document.body.contains(cell)) return

let elapsed=(Date.now()-startTime)/1000
let y=startY-speedPxPerSec*elapsed
cell.style.top=y+"px"

let rect=cell.getBoundingClientRect()
if(rect.bottom<-50) return

requestAnimationFrame(animate)
}

requestAnimationFrame(animate)
}

function startExitWatcher(){
function check(){
if(!document.body.contains(cell)) return

let rect=cell.getBoundingClientRect()
let col=parseInt(cell.dataset.colIndex,10)

if(rect.bottom<-50){
reservedImages.delete(file)
cell.remove()
addDebugLog("removed col "+col+" after leaving: "+file+" rect="+JSON.stringify({
top:Math.round(rect.top),
bottom:Math.round(rect.bottom),
left:Math.round(rect.left),
right:Math.round(rect.right)
}))
let spacingRow="grid_spacing_rows"in config?Math.max(0,parseInt(config.grid_spacing_rows)||0):(config.grid_spacing!=null?Math.max(0,parseInt(config.grid_spacing)||0):0)
let cellsLeft=Array.from(document.querySelectorAll(".gridCell")).filter(c=>parseInt(c.dataset.colIndex,10)===col)
let spawnTop=null
if(cellsLeft.length>0){
let maxBottom=-Infinity
for(let c of cellsLeft){ let b=c.getBoundingClientRect().bottom; if(b>maxBottom) maxBottom=b }
spawnTop=maxBottom+spacingRow
}
spawnImage(col,spawnTop)
return
}

requestAnimationFrame(check)
}
requestAnimationFrame(check)
}

img.onload=()=>{
startAnimation()
startExitWatcher()
}
img.onerror=()=>{
let col=parseInt(cell.dataset.colIndex,10)
reservedImages.delete(file)
cell.remove()
addDebugLog("removed (load error) col "+col+": "+file)
let spacingRow="grid_spacing_rows"in config?Math.max(0,parseInt(config.grid_spacing_rows)||0):(config.grid_spacing!=null?Math.max(0,parseInt(config.grid_spacing)||0):0)
let cellsLeft=Array.from(document.querySelectorAll(".gridCell")).filter(c=>parseInt(c.dataset.colIndex,10)===col)
let spawnTop=null
if(cellsLeft.length>0){
let maxBottom=-Infinity
for(let c of cellsLeft){ let b=c.getBoundingClientRect().bottom; if(b>maxBottom) maxBottom=b }
spawnTop=maxBottom+spacingRow
}
spawnImage(col,spawnTop)
}
}

async function updateCacheSw(){
if(config.cache_enabled&&"serviceWorker"in navigator){
try{
await navigator.serviceWorker.register("/sw.js?t="+Date.now(),{scope:"/"})
addDebugLog("Cache SW registriert (TTL "+ (config.cache_ttl_minutes||30) +"min)")
console.log("[WALL GRID] Cache SW registriert")
}catch(e){ addDebugLog("Cache SW Fehler: "+e.message); console.error("[WALL GRID] Cache SW:",e) }
}else if("serviceWorker"in navigator){
try{
let regs=await navigator.serviceWorker.getRegistrations()
for(let r of regs) await r.unregister()
addDebugLog("Cache SW deaktiviert")
console.log("[WALL GRID] Cache SW deaktiviert")
}catch(e){}
}
}

async function applyWakeLock(){
let enabled=config.screen_wake_lock_enabled
let altEnabled=config.screen_wake_lock_alternative

if(!altEnabled){
if(altWakeLockVideo){ altWakeLockVideo.pause(); altWakeLockVideo.srcObject=null; altWakeLockVideo.remove(); altWakeLockVideo=null }
if(altWakeLockCanvas){ altWakeLockCanvas.remove(); altWakeLockCanvas=null }
if(altWakeLockTick){ cancelAnimationFrame(altWakeLockTick); altWakeLockTick=null }
altWakeLockActive=false
}

if(!enabled){
if(wakeLockSentinel){ try{ await wakeLockSentinel.release() }catch(e){} wakeLockSentinel=null }
wakeLockActive=false
}else{
if(!navigator.wakeLock){ wakeLockActive=false }
else if(document.visibilityState==="visible"){
try{
wakeLockSentinel=await navigator.wakeLock.request("screen")
wakeLockActive=true
wakeLockSentinel.addEventListener("release",()=>{ wakeLockActive=false })
}catch(e){ wakeLockActive=false }
}
}

if(altEnabled&&typeof HTMLCanvasElement!=="undefined"&&HTMLCanvasElement.prototype.captureStream){
if(altWakeLockVideo) return
try{
let canvas=document.createElement("canvas")
canvas.width=2
canvas.height=2
canvas.style.cssText="position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;opacity:0;pointer-events:none;"
document.body.appendChild(canvas)
let ctx=canvas.getContext("2d")
let stream=canvas.captureStream(1)
let video=document.createElement("video")
video.srcObject=stream
video.muted=true
video.autoplay=true
video.playsInline=true
video.setAttribute("playsinline","")
video.style.cssText="position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;opacity:0;pointer-events:none;"
document.body.appendChild(video)
video.play().catch(()=>{})
altWakeLockVideo=video
altWakeLockCanvas=canvas
altWakeLockActive=true
function tick(){
if(!altWakeLockCanvas) return
ctx.fillStyle="#000"
ctx.fillRect(0,0,2,2)
altWakeLockTick=requestAnimationFrame(tick)
}
tick()
}catch(e){ altWakeLockActive=false }
}
}
document.addEventListener("visibilitychange",async()=>{
if(document.visibilityState==="visible"&&config.screen_wake_lock_enabled&&navigator.wakeLock){
try{
wakeLockSentinel=await navigator.wakeLock.request("screen")
wakeLockActive=true
wakeLockSentinel.addEventListener("release",()=>{ wakeLockActive=false })
}catch(e){ wakeLockActive=false }
}
})

function applyBackground(){
let mode=config.background_mode||"color"
let el=document.body
let grid=document.getElementById("gridContainer")
let target=grid||el
if(mode==="image"&&config.background_image){
target.style.background="#000"
target.style.backgroundImage="url(/background/"+encodeURIComponent(config.background_image)+")"
target.style.backgroundSize="cover"
target.style.backgroundPosition="center"
target.style.backgroundRepeat="no-repeat"
}else{
target.style.background=config.background_color||"#000000"
target.style.backgroundImage=""
}
}

async function init(){
connectWebSocket()

let cfgRes=await fetch("/api/config")
config=await cfgRes.json()||{}

applyBackground()
if(config.cache_enabled&&ws) setConnection(ws.readyState===WebSocket.OPEN?"online":"offline")
updateDebug()
await updateCacheSw()

let res=await fetch("/api/images")
let files=await res.json()
if(!Array.isArray(files)) files=[]

for(let f of files) addMedia(f)

setInterval(updateDebug,500)

let cols=Math.max(1,parseInt(config.grid_columns)||4)

function checkSpawnNextRow(){
let spacingRow="grid_spacing_rows"in config?Math.max(0,parseInt(config.grid_spacing_rows)||0):(config.grid_spacing!=null?Math.max(0,parseInt(config.grid_spacing)||0):0)
for(let col=0;col<cols;col++){
let cellsInCol=Array.from(document.querySelectorAll(".gridCell")).filter(c=>parseInt(c.dataset.colIndex,10)===col)
if(cellsInCol.length===0) continue
let bottomMost=null
let maxBottom=-Infinity
for(let c of cellsInCol){
let b=c.getBoundingClientRect().bottom
if(b>maxBottom){ maxBottom=b; bottomMost=c }
}
let spawnThreshold=window.innerHeight+200
if(bottomMost&&maxBottom<=spawnThreshold&&!bottomMost.dataset.spawnedNext){
bottomMost.dataset.spawnedNext="1"
let spawnTop=maxBottom+spacingRow
spawnImage(col,spawnTop)
}
}
}
setInterval(checkSpawnNextRow,300)

for(let c=0;c<cols;c++){
spawnImage(c)
}
}

init()

</script>

</body>

</html>

"""
