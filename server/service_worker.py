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
const PROGRAM_CACHE = 'wall-program-v1';
const VIDEO_EXT = ['mp4','mov','webm'];
const QUOTA_HEADROOM = 0.18;
const PHOTO_QUOTA_SHARE = 0.72;
const SERVE_PROTECT_MS = 90000;
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

function hasRange(request){
  try { return !!(request.headers && request.headers.get('range')); }
  catch (e) { return false; }
}

function isQuotaError(err){
  if (!err) return false;
  const n = err.name || '';
  const m = String(err.message || err);
  return n === 'QuotaExceededError' || n === 'NS_ERROR_DOM_QUOTA_REACHED' || m.indexOf('Quota') >= 0 || m.indexOf('quota') >= 0;
}

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    await self.clients.claim();
    await trimPhotoCache();
  })());
});
self.addEventListener('message', (e) => {
  if (!e.data || e.data.type !== 'trim_now') return;
  e.waitUntil((async () => {
    await trimPhotoCache();
    const clients = await self.clients.matchAll();
    clients.forEach(c => c.postMessage({type: 'trim_done'}));
  })());
});

self.addEventListener('fetch', (e) => {
  if (!CACHE_ENABLED || !e.request.url.includes('/media/')) return;
  if (e.request.url.endsWith('.txt')) return;
  if (e.request.method && e.request.method !== 'GET') return;
  e.respondWith(handleMediaFetch(e.request, e.clientId));
});

async function photoBudget() {
  let cap = CACHE_MAX_BYTES;
  try {
    if (self.navigator && navigator.storage && navigator.storage.estimate) {
      const est = await navigator.storage.estimate();
      const quota = Number(est.quota) || 0;
      if (quota > 0) {
        const usable = Math.floor(quota * (1 - QUOTA_HEADROOM));
        const share = Math.floor(usable * PHOTO_QUOTA_SHARE);
        if (share > 0) cap = Math.min(cap, share);
      }
    }
  } catch (err) {}
  return cap;
}

async function entryMeta(cache, metaCache, request) {
  let t = 0;
  let sz = 0;
  try {
    const m = await metaCache.match(request.url);
    if (m) {
      const j = await m.json();
      t = Number(j.t) || 0;
      sz = Number(j.s) || 0;
    }
  } catch (e) {}
  if (sz > 0) return {t, s: sz};
  try {
    const res = await cache.match(request);
    if (res) {
      const cl = Number(res.headers.get('Content-Length')) || 0;
      if (cl > 0) sz = cl;
    }
  } catch (e) {}
  return {t, s: sz};
}

let evictLock = Promise.resolve();
async function evictIfNeeded(cache, metaCache, newUrl, newIsVideo, newSize, budget) {
  let unlock;
  const prev = evictLock;
  evictLock = new Promise(function (r) { unlock = r; });
  try {
    await prev;
    return await evictNow(cache, metaCache, newUrl, newIsVideo, newSize, budget);
  } finally {
    unlock();
  }
}

async function evictNow(cache, metaCache, newUrl, newIsVideo, newSize, budget) {
  const maxBytes = budget || CACHE_MAX_BYTES;
  if (newUrl && newSize > maxBytes) return false;
  const keys = await cache.keys();
  const entries = [];
  let totalBytes = 0;
  let imgCount = 0;
  let vidCount = 0;
  const now = Date.now();
  for (const k of keys) {
    if (newUrl && k.url === newUrl) continue;
    const j = await entryMeta(cache, metaCache, k);
    totalBytes += j.s;
    const vid = isVideo(k.url);
    if (vid) vidCount++; else imgCount++;
    const served = lastCacheServeByFile.get((k.url.split('/').pop() || '').split('?')[0]) || 0;
    entries.push({
      url: k.url,
      t: j.t,
      isVideo: vid,
      size: j.s,
      expired: (now - j.t >= CACHE_TTL_MS) ? 1 : 0,
      protected: (now - served) < SERVE_PROTECT_MS
    });
  }
  if (newUrl) {
    if (newIsVideo) vidCount++; else imgCount++;
    totalBytes += newSize;
  }
  entries.sort((a, b) => {
    if (a.expired !== b.expired) return b.expired - a.expired;
    if (a.protected !== b.protected) return a.protected ? 1 : -1;
    return a.t - b.t;
  });
  const toRemove = [];
  for (const e of entries) {
    const overBytes = totalBytes > maxBytes;
    const overVid = vidCount > CACHE_MAX_VIDEOS;
    const overImg = imgCount > CACHE_MAX_IMAGES;
    if (!overBytes && !overVid && !overImg) break;
    const helps = overBytes || (e.isVideo && overVid) || (!e.isVideo && overImg);
    if (!helps) continue;
    toRemove.push(e);
    totalBytes -= e.size;
    if (e.isVideo) vidCount--; else imgCount--;
  }
  for (const e of toRemove) {
    await cache.delete(e.url);
    await metaCache.delete(e.url);
  }
  if (newUrl && (totalBytes > maxBytes || imgCount > CACHE_MAX_IMAGES || vidCount > CACHE_MAX_VIDEOS)) return false;
  return true;
}

let lastTrimAt = 0;
async function trimPhotoCache() {
  const cache = await caches.open(CACHE_NAME);
  const metaCache = await caches.open(META_NAME);
  await evictIfNeeded(cache, metaCache, '', false, 0, await photoBudget());
}

async function maybeTrimPhotoCache() {
  const now = Date.now();
  if (now - lastTrimAt < 1500) return;
  lastTrimAt = now;
  await trimPhotoCache();
}

const lastCacheServeByFile = new Map();
const CACHE_SERVE_DEBOUNCE_MS = 300;
function notifyCacheServe(file, expired, clientId) {
  const now = Date.now();
  lastCacheServeByFile.set(file, now);
  if (lastCacheServeByFile.size > 400) {
    lastCacheServeByFile.forEach((v, k) => {
      if (typeof v === 'number' && now - v > SERVE_PROTECT_MS * 2) lastCacheServeByFile.delete(k);
    });
  }
  const last = lastCacheServeByFile.get('log:' + file) || 0;
  if (now - last < CACHE_SERVE_DEBOUNCE_MS) return;
  lastCacheServeByFile.set('log:' + file, now);
  setTimeout(() => lastCacheServeByFile.delete('log:' + file), CACHE_SERVE_DEBOUNCE_MS);
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

async function matchCached(cache, request) {
  let hit = await cache.match(request.url);
  if (hit) return {res: hit, url: request.url};
  hit = await cache.match(request);
  if (hit) return {res: hit, url: request.url};
  const fn = (request.url.split('/').pop() || '').split('?')[0];
  if (!fn) return null;
  const keys = await cache.keys();
  for (const k of keys) {
    const kfn = (k.url.split('/').pop() || '').split('?')[0];
    if (kfn === fn) {
      hit = await cache.match(k);
      if (hit) return {res: hit, url: k.url};
    }
  }
  return null;
}

async function readMeta(metaCache, urls) {
  for (const u of urls) {
    if (!u) continue;
    const m = await metaCache.match(u);
    if (m) {
      try { return await m.json(); } catch (e) {}
    }
  }
  return {};
}

async function sliceRange(fullRes, request) {
  const blob = await fullRes.blob();
  const size = blob.size;
  const rangeHeader = (request.headers && request.headers.get('range')) || '';
  const m = /^bytes=(\d*)-(\d*)$/i.exec(String(rangeHeader).trim());
  const type = fullRes.headers.get('Content-Type') || 'application/octet-stream';
  if (!m) {
    return new Response(blob, {status: 200, headers: {'Content-Type': type, 'Content-Length': String(size), 'Accept-Ranges': 'bytes'}});
  }
  let start = m[1] === '' ? 0 : parseInt(m[1], 10);
  let end = m[2] === '' ? (size - 1) : parseInt(m[2], 10);
  if (!isFinite(start) || !isFinite(end) || start < 0 || start >= size || end < start) {
    return new Response('', {status: 416, headers: {'Content-Range': 'bytes */' + size}});
  }
  end = Math.min(end, size - 1);
  const slice = blob.slice(start, end + 1);
  return new Response(slice, {
    status: 206,
    headers: {
      'Content-Type': type,
      'Content-Length': String(slice.size),
      'Content-Range': 'bytes ' + start + '-' + end + '/' + size,
      'Accept-Ranges': 'bytes'
    }
  });
}

async function storeFull(cache, metaCache, url, response, clientId) {
  if (!response || response.status !== 200) return false;
  let size = Number(response.headers.get('Content-Length')) || 0;
  const toPut = response.clone();
  if (!size) {
    try {
      const buf = await response.clone().arrayBuffer();
      size = buf.byteLength;
    } catch (e) { return false; }
  }
  const alreadyCached = await cache.match(url);
  const budget = await photoBudget();
  const ok = await evictIfNeeded(cache, metaCache, url, isVideo(url), size, budget);
  if (!ok) return false;
  try {
    await cache.put(url, toPut);
    await metaCache.put(url, new Response(JSON.stringify({t: Date.now(), s: size})));
    if (!alreadyCached) notifyCacheStore((url.split('/').pop() || '?').split('?')[0], clientId);
    return true;
  } catch (err) {
    if (!isQuotaError(err)) return false;
    const retryOk = await evictIfNeeded(cache, metaCache, url, isVideo(url), size, Math.min(budget, size + 1024));
    if (!retryOk) return false;
    try {
      const again = response.clone();
      await cache.put(url, again);
      await metaCache.put(url, new Response(JSON.stringify({t: Date.now(), s: size})));
      if (!alreadyCached) notifyCacheStore((url.split('/').pop() || '?').split('?')[0], clientId);
      return true;
    } catch (e2) {
      return false;
    }
  }
}

function fetchTimeoutMs(url, range) {
  if (isVideo(url) || range) return 180000;
  return 15000;
}

async function fetchNetwork(request, ms) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ms);
  try {
    const netRes = await fetch(request, { cache: 'no-store', signal: controller.signal });
    clearTimeout(timeout);
    return netRes;
  } catch (err) {
    clearTimeout(timeout);
    return null;
  }
}

function cacheFullInBackground(url, clientId) {
  const key = 'bg:' + url;
  if (fetchInFlight.has(key)) return;
  const work = (async () => {
    try {
      const res = await fetchNetwork(new Request(url, {cache: 'no-store'}), fetchTimeoutMs(url, false));
      if (res && res.ok && res.status === 200) {
        const cache = await caches.open(CACHE_NAME);
        const metaCache = await caches.open(META_NAME);
        await storeFull(cache, metaCache, url, res, clientId);
      }
    } catch (e) {}
  })();
  fetchInFlight.set(key, work);
  work.finally(() => fetchInFlight.delete(key));
}

async function handleMediaFetch(request, clientId) {
  maybeTrimPhotoCache();
  const cache = await caches.open(CACHE_NAME);
  const metaCache = await caches.open(META_NAME);
  const fn = (request.url.split('/').pop() || '?').split('?')[0];
  const range = hasRange(request);
  const hit = await matchCached(cache, request);

  if (!serverOnline) {
    if (hit && hit.res) {
      const meta = await readMeta(metaCache, [request.url, hit.url]);
      const expired = Date.now() - (meta.t || 0) >= CACHE_TTL_MS;
      notifyCacheServe(fn, expired, clientId);
      return range ? sliceRange(hit.res, request) : hit.res;
    }
    return new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  if (hit && hit.res) {
    const meta = await readMeta(metaCache, [request.url, hit.url]);
    const expired = Date.now() - (meta.t || 0) >= CACHE_TTL_MS;
    if (!expired) {
      notifyCacheServe(fn, false, clientId);
      return range ? sliceRange(hit.res, request) : hit.res;
    }
  }

  const url = request.url;
  const inFlight = fetchInFlight.get(url);
  if (inFlight && !range) {
    const res = await inFlight;
    if (res) return res.clone();
    if (hit && hit.res) {
      notifyCacheServe(fn, true, clientId);
      return hit.res;
    }
    return new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  if (range) {
    const netRes = await fetchNetwork(request, fetchTimeoutMs(url, true));
    if (netRes && (netRes.ok || netRes.status === 206)) {
      if (!hit || Date.now() - ((await readMeta(metaCache, [url, hit && hit.url])).t || 0) >= CACHE_TTL_MS) {
        cacheFullInBackground(url.split('?')[0], clientId);
      }
      return netRes;
    }
    if (hit && hit.res) {
      notifyCacheServe(fn, true, clientId);
      return sliceRange(hit.res, request);
    }
    return netRes || new Response('', {status: 503, statusText: 'Service Unavailable'});
  }

  async function doFetch() {
    const netRes = await fetchNetwork(request, fetchTimeoutMs(url, false));
    if (netRes && netRes.ok && netRes.status === 200) {
      await storeFull(cache, metaCache, request.url, netRes.clone(), clientId);
      return netRes;
    }
    if (hit && hit.res) {
      notifyCacheServe(fn, true, clientId);
      return hit.res;
    }
    return netRes;
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
    if paths is None:
        try:
            from server.project_runner import runner
            names = list(runner.running_names() or [])
            if len(names) == 1:
                paths = get_paths(names[0])
        except Exception:
            paths = None
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
