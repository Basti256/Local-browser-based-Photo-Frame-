"""Service Worker mit Cache-Parametern aus der Projektconfig."""
from fastapi.responses import Response

from server.project import get_paths, load_project_config

SW_SCRIPT = r"""
const CACHE_ENABLED = %(cache_enabled)s;
const CACHE_TTL_MS = %(cache_ttl_ms)s;
const CACHE_MAX_IMAGES = %(cache_max_images)s;
const CACHE_MAX_VIDEOS = %(cache_max_videos)s;
const CACHE_MAX_BYTES = %(cache_max_bytes)s;
const CACHE_NAME = 'wall-media-v1';
const META_NAME = 'wall-media-meta-v1';
const VIDEO_EXT = ['mp4','mov','webm'];
let serverOnline = true;
const bc = new BroadcastChannel('wall-server-state');
let lastCacheListSent = 0;
const CACHE_LIST_DEBOUNCE_MS = 500;
bc.onmessage = async (e) => {
  if (!e.data || !e.data.state) return;
  serverOnline = e.data.state === 'online';
  if (!serverOnline) {
    const now = Date.now();
    if (now - lastCacheListSent < CACHE_LIST_DEBOUNCE_MS) return;
    lastCacheListSent = now;
    const cache = await caches.open(CACHE_NAME);
    const keys = await cache.keys();
    const files = keys.map(k => (k.url.split('/').pop() || '?').split('?')[0]).filter(f => !f.endsWith('.txt'));
    const clients = await self.clients.matchAll();
    clients.forEach(c => c.postMessage({type: 'cache_list', files}));
  }
};

function isVideo(url){
  const ext = (url.split('.').pop() || '').toLowerCase().split('?')[0];
  return VIDEO_EXT.includes(ext);
}

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });

self.addEventListener('fetch', (e) => {
  if (!CACHE_ENABLED || !e.request.url.includes('/media/')) return;
  if (e.request.url.endsWith('.txt')) return;
  e.respondWith(handleMediaFetch(e.request, e.clientId));
});

async function evictIfNeeded(cache, metaCache, newUrl, newIsVideo, newSize) {
  const keys = await cache.keys();
  const entries = [];
  let totalBytes = 0;
  for (const k of keys) {
    const m = await metaCache.match(k);
    const j = m ? await m.json() : {};
    const t = j.t || 0;
    const sz = j.s || 0;
    totalBytes += sz;
    entries.push({url: k.url, t, isVideo: isVideo(k.url), size: sz});
  }
  let imgCount = entries.filter(e => !e.isVideo).length;
  let vidCount = entries.filter(e => e.isVideo).length;
  if (newIsVideo) vidCount++; else imgCount++;
  totalBytes += newSize;
  const toRemove = [];
  entries.sort((a,b) => a.t - b.t);
  for (const e of entries) {
    if (totalBytes > CACHE_MAX_BYTES || (e.isVideo && vidCount > CACHE_MAX_VIDEOS) || (!e.isVideo && imgCount > CACHE_MAX_IMAGES)) {
      toRemove.push(e);
      totalBytes -= e.size;
      if (e.isVideo) vidCount--; else imgCount--;
    }
  }
  for (const e of toRemove) {
    await cache.delete(e.url);
    await metaCache.delete(e.url);
  }
}

const lastCacheServeByFile = new Map();
const CACHE_SERVE_DEBOUNCE_MS = 300;
function notifyCacheServe(file, expired, clientId) {
  const now = Date.now();
  const last = lastCacheServeByFile.get(file) || 0;
  if (now - last < CACHE_SERVE_DEBOUNCE_MS) return;
  lastCacheServeByFile.set(file, now);
  setTimeout(() => lastCacheServeByFile.delete(file), CACHE_SERVE_DEBOUNCE_MS);
  const msg = {type:'cache_serve', file, expired};
  if (clientId) {
    self.clients.get(clientId).then(c => { if (c) c.postMessage(msg); }).catch(() => {});
  } else {
    self.clients.matchAll().then(clients => { clients.forEach(c => c.postMessage(msg)); });
  }
}
const lastCacheStoreByFile = new Map();
const CACHE_STORE_DEBOUNCE_MS = 300;
function notifyCacheStore(file, clientId) {
  const now = Date.now();
  const last = lastCacheStoreByFile.get(file) || 0;
  if (now - last < CACHE_STORE_DEBOUNCE_MS) return;
  lastCacheStoreByFile.set(file, now);
  setTimeout(() => lastCacheStoreByFile.delete(file), CACHE_STORE_DEBOUNCE_MS);
  const msg = {type:'cache_store', file};
  if (clientId) {
    self.clients.get(clientId).then(c => { if (c) c.postMessage(msg); }).catch(() => {});
  } else {
    self.clients.matchAll().then(clients => { clients.forEach(c => c.postMessage(msg)); });
  }
}

const fetchInFlight = new Map();

async function handleMediaFetch(request, clientId) {
  const cache = await caches.open(CACHE_NAME);
  const metaCache = await caches.open(META_NAME);
  const fn = (request.url.split('/').pop() || '?').split('?')[0];

  if (!serverOnline) {
    const cached = await cache.match(request.url);
    if (cached) {
      const metaRes = await metaCache.match(request.url);
      let expired = false;
      if (metaRes) {
        const meta = await metaRes.json();
        expired = Date.now() - meta.t >= CACHE_TTL_MS;
      }
      notifyCacheServe(fn, expired, clientId);
      return cached;
    }
    return new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  const url = request.url;
  const inFlight = fetchInFlight.get(url);
  if (inFlight) {
    const res = await inFlight;
    if (res) return res.clone();
    const fallback = await cache.match(request.url);
    return fallback || new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  async function doFetch() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    try {
      const netRes = await fetch(request, { cache: 'no-store', signal: controller.signal });
      clearTimeout(timeout);
      if (netRes && netRes.ok) {
        const alreadyCached = await cache.match(request.url);
        const clone = netRes.clone();
        const buf = await clone.arrayBuffer();
        const size = buf.byteLength;
        await evictIfNeeded(cache, metaCache, request.url, isVideo(request.url), size);
        await cache.put(request.url, netRes.clone());
        await metaCache.put(request.url, new Response(JSON.stringify({t: Date.now(), s: size})));
        if (!alreadyCached) notifyCacheStore(fn, clientId);
        return netRes;
      }
      return netRes;
    } catch (err) {
      clearTimeout(timeout);
      const cached = await cache.match(request.url);
      if (cached) {
        const metaRes = await metaCache.match(request.url);
        let expired = false;
        if (metaRes) {
          const meta = await metaRes.json();
          expired = Date.now() - meta.t >= CACHE_TTL_MS;
        }
        notifyCacheServe(fn, expired, clientId);
        return cached;
      }
      return null;
    }
  }

  const promise = doFetch();
  fetchInFlight.set(url, promise);
  try {
    const res = await promise;
    if (res) return res;
    return new Response('', {status: 503, statusText: 'Service Unavailable'});
  } finally {
    fetchInFlight.delete(url);
  }
}
"""


def service_worker_response() -> Response:
    paths = get_paths()
    cfg = load_project_config(paths) if paths else {}
    enabled = cfg.get("cache_enabled", False)
    ttl_min = cfg.get("cache_ttl_minutes", 30)
    ttl_ms = ttl_min * 60 * 1000
    max_img = int(cfg.get("cache_max_images", 100))
    max_vid = int(cfg.get("cache_max_videos", 20))
    max_mb = float(cfg.get("cache_max_size_mb", 500))
    max_bytes = int(max_mb * 1024 * 1024) if max_mb > 0 else 4294967296
    body = SW_SCRIPT % {
        "cache_enabled": "true" if enabled else "false",
        "cache_ttl_ms": ttl_ms,
        "cache_max_images": max_img,
        "cache_max_videos": max_vid,
        "cache_max_bytes": max_bytes,
    }
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    from server.context import get_url_prefix
    prefix = get_url_prefix()
    if prefix:
        headers["Service-Worker-Allowed"] = prefix + "/"
    return Response(
        content=body,
        media_type="application/javascript",
        headers=headers,
    )
