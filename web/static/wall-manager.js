(function (global) {
  "use strict";

  var CACHE = "wall-program-v1";
  var META = "wall-program-meta-v1";
  var PHOTO_CACHE = "wall-media-v1";
  var PROGRAM_MAX_FILES = 16;
  var QUOTA_HEADROOM = 0.18;
  var PROGRAM_QUOTA_SHARE = 0.22;
  var state = {
    enabled: false,
    prefetch: "next",
    muteAll: false,
    assets: [],
    playlist: [],
    idx: 0,
    gen: 0,
    layer: null,
    black: null,
    stage: null,
    tap: null,
    media: null,
    audioUnlocked: false,
    cacheFiles: 0,
    cacheBytes: 0,
    quotaBytes: 0,
    quotaUsage: 0,
    currentLabel: "aus",
    wallArmed: false,
    following: false,
    followTimer: 0,
    clock: "",
    appliedIndex: -1,
    mediaAssetId: null,
    fadeHalf: "",
    fxMode: "",
    slotId: null,
    mountingAssetId: null,
    applyBusy: false,
    applyQueued: null,
    wipeRaf: 0,
    wipeGen: 0,
    poppedSlot: null,
    prefetchBusy: {},
    blobUrls: [],
    prefetchChain: 0
  };

  function $(id) {
    return document.getElementById(id);
  }

  function pf(path) {
    return typeof global.pfUrl === "function" ? global.pfUrl(path) : path;
  }

  function assetById(id) {
    for (var i = 0; i < state.assets.length; i++) {
      if (state.assets[i].id === id) return state.assets[i];
    }
    return null;
  }

  function debugLog(msg) {
    if (typeof global.addDebugLog === "function") global.addDebugLog(msg);
  }

  function isMedia(it) {
    return it && (it.kind === "video" || it.kind === "image" || it.kind === "photowall");
  }

  function isEffect(it) {
    return it && it.kind === "effect";
  }

  function firstMediaIdx() {
    for (var i = 0; i < state.playlist.length; i++) {
      if (isMedia(state.playlist[i])) return i;
    }
    return -1;
  }

  function nextMediaIdx(from) {
    var n = state.playlist.length;
    if (!n) return from;
    for (var k = 1; k <= n; k++) {
      var j = (from + k) % n;
      if (isMedia(state.playlist[j])) return j;
    }
    return from;
  }

  function effectsAfter(from) {
    var out = [];
    var n = state.playlist.length;
    for (var k = 1; k < n; k++) {
      var j = (from + k) % n;
      var it = state.playlist[j];
      if (isEffect(it)) out.push(it);
      else break;
    }
    return out;
  }

  function fadeMs(fx) {
    return fxMs(fx, "fade");
  }

  function fxMs(fx, name) {
    for (var i = 0; i < fx.length; i++) {
      if (fx[i].effect === name) return Math.max(200, (Number(fx[i].duration_sec) || 5) * 1000);
    }
    return 0;
  }

  function wipeDir(fx) {
    for (var i = 0; i < fx.length; i++) {
      if (fx[i].effect === "wipe") {
        var d = fx[i].direction || "ltr";
        if (d === "rtl" || d === "ttb" || d === "btt") return d;
        return "ltr";
      }
    }
    return "ltr";
  }

  function hasPop(fx) {
    for (var i = 0; i < fx.length; i++) {
      if (fx[i].effect === "pop") return true;
    }
    return false;
  }

  function wipeClip(p, direction) {
    var rest = ((1 - Math.max(0, Math.min(1, p))) * 100).toFixed(2) + "%";
    if (direction === "rtl") return "inset(0% 0% 0% " + rest + ")";
    if (direction === "ttb") return "inset(0% 0% " + rest + " 0%)";
    if (direction === "btt") return "inset(" + rest + " 0% 0% 0%)";
    return "inset(0% " + rest + " 0% 0%)";
  }

  function wipeOutgoing(p, direction) {
    var gone = (Math.max(0, Math.min(1, p)) * 100).toFixed(2) + "%";
    if (direction === "rtl") return "inset(0% " + gone + " 0% 0%)";
    if (direction === "ttb") return "inset(0% 0% " + gone + " 0%)";
    if (direction === "btt") return "inset(" + gone + " 0% 0% 0%)";
    return "inset(0% 0% 0% " + gone + ")";
  }

  function cancelWipeTick() {
    state.wipeGen += 1;
    if (state.wipeRaf) {
      try { cancelAnimationFrame(state.wipeRaf); } catch (e) {}
      state.wipeRaf = 0;
    }
  }

  function setWipeClip(p, direction) {
    if (!state.stage) return;
    var incoming = state.stage.querySelector(".wmIncoming");
    if (incoming) {
      incoming.style.opacity = "1";
      incoming.style.transition = "none";
      incoming.style.clipPath = wipeClip(p, direction);
      return;
    }
    var outs = state.stage.querySelectorAll(".wmOutgoing");
    for (var i = 0; i < outs.length; i++) {
      outs[i].style.transition = "none";
      outs[i].style.clipPath = wipeOutgoing(p, direction);
    }
  }

  function markOutgoing() {
    if (!state.stage) return;
    var kids = state.stage.querySelectorAll("img, video");
    for (var i = 0; i < kids.length; i++) {
      kids[i].classList.remove("wmIncoming");
      kids[i].classList.add("wmOutgoing");
    }
  }

  function setElFade(el, to, ms, from) {
    if (!el) return;
    el.style.transition = "none";
    if (from != null) el.style.opacity = String(from);
    void el.offsetWidth;
    el.style.transition = "opacity " + (Math.max(50, ms) / 1000) + "s linear";
    el.style.opacity = String(to);
  }

  function unwrapPopFrame() {
    var frame = $("wmFrame");
    if (!frame) return;
    var host = frame.parentNode;
    var child = frame.firstElementChild;
    if (host && child) {
      host.insertBefore(child, frame);
      state.media = child;
    }
    if (frame.parentNode) {
      try { frame.parentNode.removeChild(frame); } catch (e) {}
    }
  }

  function mediaConnected() {
    return !!(state.media && state.media.isConnected);
  }

  function endOverlap() {
    cancelWipeTick();
    unwrapPopFrame();
    if (!state.stage) return;
    var keep = state.media;
    var kids = Array.prototype.slice.call(state.stage.childNodes);
    for (var i = 0; i < kids.length; i++) {
      var node = kids[i];
      if (keep && node !== keep) {
        revokeElSrc(node);
        if (node.querySelectorAll) {
          var nested = node.querySelectorAll("img, video");
          for (var n = 0; n < nested.length; n++) revokeElSrc(nested[n]);
        }
        try { state.stage.removeChild(node); } catch (e) {}
        continue;
      }
      if (node && node.style) {
        node.style.opacity = "";
        node.style.clipPath = "";
        node.style.transition = "";
      }
      if (node && node.classList) {
        node.classList.remove("wmOutgoing", "wmIncoming");
      }
    }
    state.stage.classList.remove("has-overlap");
  }

  function startDissolveAnim(fromP, remainMs) {
    var outgoing = state.stage ? state.stage.querySelectorAll(".wmOutgoing") : [];
    var incoming = state.stage && state.stage.querySelector(".wmIncoming");
    var ms = Math.max(80, remainMs);
    var startOut = 1 - fromP;
    for (var i = 0; i < outgoing.length; i++) setElFade(outgoing[i], 0, ms, startOut);
    if (incoming) setElFade(incoming, 1, ms, fromP);
    else if (!outgoing.length && state.media) setElFade(state.media, 0, ms, startOut);
  }

  function startWipeAnim(fromP, remainMs, direction) {
    cancelWipeTick();
    var from = Math.max(0, Math.min(1, Number(fromP) || 0));
    var ms = Math.max(80, Number(remainMs) || 80);
    var dir = direction || "ltr";
    var gen = state.wipeGen;
    var t0 = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
    setWipeClip(from, dir);
    var step = function (now) {
      if (gen !== state.wipeGen) return;
      var t = Math.min(1, (now - t0) / ms);
      setWipeClip(from + (1 - from) * t, dir);
      if (t < 1) state.wipeRaf = requestAnimationFrame(step);
      else state.wipeRaf = 0;
    };
    state.wipeRaf = requestAnimationFrame(step);
  }

  function ensureLayer() {
    var stageRoot = $("wallStage") || document.body;
    var layer = $("wmLayer");
    if (!layer) {
      layer = document.createElement("div");
      layer.id = "wmLayer";
      layer.innerHTML = '<div id="wmBlack"></div><div id="wmStage"></div><button type="button" id="wmTap">Tippen für Ton</button>';
      stageRoot.appendChild(layer);
    }
    state.layer = layer;
    state.black = $("wmBlack");
    state.stage = $("wmStage");
    state.tap = $("wmTap");
    if (state.tap && !state.tap.dataset.bound) {
      state.tap.dataset.bound = "1";
      state.tap.addEventListener("click", unlockAudio);
    }
    document.addEventListener("pointerdown", unlockAudio, { once: false });
  }

  function unlockAudio() {
    state.audioUnlocked = true;
    if (state.tap) state.tap.classList.remove("is-on");
    if (state.media && state.media.tagName === "VIDEO") {
      try {
        state.media.muted = wantMute(state.playlist[state.idx] || {});
        state.media.play().catch(function () {});
      } catch (e) {}
    }
  }

  function wantMute(item) {
    return !!(state.muteAll || (item && item.mute));
  }

  function setChrome(item) {
    var banner = $("banner");
    var qr = $("qrContainer");
    var showB = true;
    var showQ = true;
    if (item && item.kind !== "photowall" && item.kind !== "effect") {
      showB = !!item.show_banner;
      showQ = !!item.show_qr;
    }
    if (banner) banner.style.visibility = showB ? "" : "hidden";
    if (qr) qr.style.visibility = showQ ? "" : "hidden";
  }

  function waitMs(ms, gen) {
    return new Promise(function (resolve) {
      if (gen !== state.gen) return resolve(false);
      setTimeout(function () {
        resolve(gen === state.gen);
      }, Math.max(0, ms));
    });
  }

  function blackOpacity() {
    if (!state.black) return 0;
    var inline = parseFloat(state.black.style.opacity);
    if (isFinite(inline)) return Math.max(0, Math.min(1, inline));
    try {
      return Math.max(0, Math.min(1, parseFloat(window.getComputedStyle(state.black).opacity) || 0));
    } catch (e) {
      return 0;
    }
  }

  function setFadeDuration(ms) {
    if (!state.black) return;
    state.black.style.transition = "opacity " + (Math.max(50, ms) / 1000) + "s linear";
  }

  function snapBlack(p) {
    if (!state.black) return;
    var v = Math.max(0, Math.min(1, Number(p) || 0));
    state.black.style.transition = "none";
    state.black.style.opacity = String(v);
    void state.black.offsetWidth;
    if (v > 0.02) state.black.classList.add("is-on");
    else state.black.classList.remove("is-on");
  }

  function animateBlackTo(target, ms, from) {
    if (!state.black) return;
    var to = Math.max(0, Math.min(1, Number(target)));
    var start = from == null ? blackOpacity() : Math.max(0, Math.min(1, Number(from)));
    snapBlack(start);
    if (Math.abs(to - start) < 0.012) {
      snapBlack(to);
      return;
    }
    setFadeDuration(ms || 200);
    state.black.style.opacity = String(to);
    if (to > 0.02) state.black.classList.add("is-on");
    else state.black.classList.remove("is-on");
  }

  function fadeBlack(on, ms, gen) {
    if (!state.black) return Promise.resolve(gen === state.gen);
    animateBlackTo(on ? 1 : 0, ms || 5000, on ? 0 : 1);
    return waitMs(ms || 5000, gen);
  }

  function revokeBlobs() {
    var list = state.blobUrls || [];
    for (var i = 0; i < list.length; i++) {
      try { URL.revokeObjectURL(list[i]); } catch (e) {}
    }
    state.blobUrls = [];
  }

  function revokeElSrc(el) {
    if (!el) return;
    var s = el.getAttribute && (el.getAttribute("src") || el.src) || "";
    if (s && String(s).indexOf("blob:") === 0) {
      try { URL.revokeObjectURL(s); } catch (e) {}
    }
  }

  function clearStage() {
    cancelWipeTick();
    if (!state.stage) return;
    var kids = state.stage.querySelectorAll("img, video");
    for (var i = 0; i < kids.length; i++) revokeElSrc(kids[i]);
    state.stage.innerHTML = "";
    state.stage.classList.remove("is-pop", "has-overlap");
    state.media = null;
  }

  function hideLayer() {
    if (state.layer) state.layer.classList.remove("is-on");
    clearStage();
    snapBlack(0);
    state.mediaAssetId = null;
  }

  function showLayer() {
    if (state.layer) state.layer.classList.add("is-on");
  }

  function keepProgramUrls() {
    var keep = {};
    var cur = state.playlist[state.idx];
    if (cur && cur.asset_id) {
      var a = assetById(cur.asset_id);
      if (a && a.display) keep[pf("/wm/" + a.display)] = true;
    }
    var nxt = nextMediaIdx(state.idx);
    var it = state.playlist[nxt];
    if (it && it.asset_id) {
      var b = assetById(it.asset_id);
      if (b && b.display) keep[pf("/wm/" + b.display)] = true;
    }
    return keep;
  }

  function playlistUrlSet() {
    var set = {};
    for (var i = 0; i < state.playlist.length; i++) {
      var it = state.playlist[i];
      if (!it || !it.asset_id) continue;
      var a = assetById(it.asset_id);
      if (a && a.display) set[pf("/wm/" + a.display)] = true;
    }
    return set;
  }

  async function programBudget() {
    var cap = 256 * 1024 * 1024;
    try {
      if (navigator.storage && navigator.storage.estimate) {
        var est = await navigator.storage.estimate();
        state.quotaBytes = est.quota || 0;
        state.quotaUsage = est.usage || 0;
        var quota = Number(est.quota) || 0;
        if (quota > 0) {
          var usable = quota * (1 - QUOTA_HEADROOM);
          cap = Math.floor(usable * PROGRAM_QUOTA_SHARE);
          var free = Math.max(0, usable - (Number(est.usage) || 0));
          cap = Math.min(cap, (state.cacheBytes || 0) + free);
        }
      }
    } catch (e) {}
    return Math.max(8 * 1024 * 1024, cap);
  }

  function isQuotaErr(err) {
    if (!err) return false;
    var n = err.name || "";
    var m = String(err.message || err);
    return n === "QuotaExceededError" || n === "NS_ERROR_DOM_QUOTA_REACHED" || m.indexOf("Quota") >= 0 || m.indexOf("quota") >= 0;
  }

  async function evictProgram(cache, metaCache, newUrl, newSize, budget) {
    if (newSize > budget) return false;
    var keys = await cache.keys();
    var keep = keepProgramUrls();
    var inPl = playlistUrlSet();
    var entries = [];
    var total = 0;
    for (var i = 0; i < keys.length; i++) {
      var u = keys[i].url;
      if (u === newUrl) continue;
      var sz = 0;
      var t = 0;
      try {
        var m = await metaCache.match(u);
        if (m) {
          var j = await m.json();
          sz = Number(j.s) || 0;
          t = Number(j.t) || 0;
        }
      } catch (e) {}
      if (!sz) {
        try {
          var res = await cache.match(keys[i]);
          if (res) {
            var b = await res.blob();
            sz = b.size || 0;
          }
        } catch (e2) {}
      }
      total += sz;
      entries.push({ url: u, size: sz, t: t, keep: !!keep[u], stale: !inPl[u] });
    }
    total += newSize;
    var files = entries.length + 1;
    entries.sort(function (a, b) {
      if (a.keep !== b.keep) return a.keep ? 1 : -1;
      if (a.stale !== b.stale) return a.stale ? -1 : 1;
      return a.t - b.t;
    });
    var toRemove = [];
    for (var k = 0; k < entries.length; k++) {
      if (total <= budget && files <= PROGRAM_MAX_FILES) break;
      if (entries[k].keep) continue;
      toRemove.push(entries[k]);
      total -= entries[k].size;
      files--;
    }
    if (total > budget || files > PROGRAM_MAX_FILES) return false;
    for (var r = 0; r < toRemove.length; r++) {
      await cache.delete(toRemove[r].url);
      await metaCache.delete(toRemove[r].url);
    }
    return true;
  }

  async function cachePut(url) {
    if (!("caches" in window) || !url) return false;
    if (url.indexOf("/media/") >= 0) return false;
    if (state.prefetchBusy[url]) return state.prefetchBusy[url];
    var work = (async function () {
      var cache = await caches.open(CACHE);
      var metaCache = await caches.open(META);
      var hit = await cache.match(url);
      if (hit) return true;
      var budget = await programBudget();
      var res = await fetch(url, { cache: "no-store" });
      if (!res.ok || res.status !== 200) return false;
      var clone = res.clone();
      var buf = await res.arrayBuffer();
      var size = buf.byteLength || 0;
      var ok = await evictProgram(cache, metaCache, url, size, budget);
      if (!ok) return false;
      try {
        await cache.put(url, clone);
        await metaCache.put(url, new Response(JSON.stringify({ t: Date.now(), s: size })));
      } catch (err) {
        if (!isQuotaErr(err)) return false;
        ok = await evictProgram(cache, metaCache, url, size, Math.min(budget, size + 1024));
        if (!ok) return false;
        try {
          var hdrs = {};
          try {
            var ct = clone.headers && clone.headers.get("Content-Type");
            if (ct) hdrs["Content-Type"] = ct;
          } catch (e3) {}
          await cache.put(url, new Response(buf, { headers: hdrs }));
          await metaCache.put(url, new Response(JSON.stringify({ t: Date.now(), s: size })));
        } catch (e2) {
          return false;
        }
      }
      return true;
    })();
    state.prefetchBusy[url] = work;
    try {
      return await work;
    } catch (e) {
      return false;
    } finally {
      delete state.prefetchBusy[url];
      refreshCacheStats();
    }
  }

  function mediaMime(asset) {
    var name = String((asset && asset.display) || "").toLowerCase();
    if (asset && asset.type === "video") {
      if (name.indexOf(".webm") >= 0) return "video/webm";
      return "video/mp4";
    }
    if (name.indexOf(".png") >= 0) return "image/png";
    if (name.indexOf(".webp") >= 0) return "image/webp";
    if (name.indexOf(".gif") >= 0) return "image/gif";
    return "image/jpeg";
  }

  async function srcFor(asset) {
    var url = pf("/wm/" + asset.display);
    if (!("caches" in window)) return url;
    try {
      var cache = await caches.open(CACHE);
      var hit = await cache.match(url);
      if (!hit) {
        await cachePut(url);
        cache = await caches.open(CACHE);
        hit = await cache.match(url);
      }
      if (hit) {
        var blob = await hit.blob();
        if (!blob || !blob.size) return url;
        var mime = mediaMime(asset);
        if (!blob.type || blob.type.indexOf("octet") >= 0 || (asset.type === "video" && blob.type.indexOf("video") < 0) || (asset.type === "image" && blob.type.indexOf("image") < 0)) {
          blob = new Blob([await blob.arrayBuffer()], { type: mime });
        }
        var blobUrl = URL.createObjectURL(blob);
        state.blobUrls.push(blobUrl);
        return blobUrl;
      }
    } catch (e) {}
    return url;
  }

  async function refreshCacheStats() {
    state.cacheFiles = 0;
    state.cacheBytes = 0;
    try {
      if (navigator.storage && navigator.storage.estimate) {
        var est = await navigator.storage.estimate();
        state.quotaBytes = est.quota || 0;
        state.quotaUsage = est.usage || 0;
      }
      if (!("caches" in window)) return;
      var cache = await caches.open(CACHE);
      var metaCache = await caches.open(META);
      var keys = await cache.keys();
      state.cacheFiles = keys.length;
      var n = 0;
      for (var i = 0; i < keys.length; i++) {
        try {
          var sz = 0;
          var m = await metaCache.match(keys[i].url);
          if (m) {
            var j = await m.json();
            sz = Number(j.s) || 0;
          }
          if (!sz) {
            var res = await cache.match(keys[i]);
            if (res) {
              var b = await res.blob();
              sz = b.size || 0;
            }
          }
          n += sz;
        } catch (e) {}
      }
      state.cacheBytes = n;
    } catch (e) {}
    if (typeof global.updateDebug === "function") global.updateDebug();
  }

  function prefetchAround(i) {
    if (!state.enabled || !state.playlist.length) return;
    var cur = state.playlist[i];
    var ids = [];
    var n = state.playlist.length;
    if (state.prefetch === "all") {
      if (!cur || cur.kind !== "photowall") return;
      for (var k = 1; k < n; k++) {
        var rest = state.playlist[(i + k) % n];
        if (rest && rest.asset_id) ids.push(rest.asset_id);
      }
    } else {
      var nxt = nextMediaIdx(i);
      var it = state.playlist[nxt];
      if (it && it.asset_id) ids.push(it.asset_id);
    }
    var seen = {};
    var urls = [];
    ids.forEach(function (id) {
      if (!id || seen[id]) return;
      seen[id] = true;
      var a = assetById(id);
      if (a && a.display) urls.push(pf("/wm/" + a.display));
    });
    if (!urls.length) return;
    var chain = ++state.prefetchChain;
    (async function () {
      for (var u = 0; u < urls.length; u++) {
        if (chain !== state.prefetchChain) return;
        var ok = await cachePut(urls[u]);
        if (!ok) return;
      }
    })();
  }

  function photowall() {
    return global.pfPhotowall || null;
  }

  function ensureWall(item) {
    var pw = photowall();
    if (!pw || !item) return;
    var running = state.wallArmed && pw.isPaused && !pw.isPaused();
    if (running) return;
    if (item.enter === "resume" && pw.resume) pw.resume();
    else if (pw.start) pw.start();
    state.wallArmed = true;
  }

  function finishWall(item) {
    var pw = photowall();
    if (!pw || !item) return;
    if (item.exit === "pause" && pw.pause) pw.pause();
    else if (item.exit === "stop") {
      if (pw.pause) pw.pause();
      if (pw.clear) pw.clear();
      state.wallArmed = false;
    }
  }

  function armPreload(nextItem, clipMs, gen) {
    if (!nextItem || nextItem.kind !== "photowall") return;
    var pre = (Number(nextItem.photowall_preload_sec) || 15) * 1000;
    var delay = Math.max(0, clipMs - pre);
    waitMs(delay, gen).then(function (ok) {
      if (!ok) return;
      debugLog("Wall Manager: Photowall lädt vor");
      ensureWall(nextItem);
    });
  }

  function clipMs(item, asset) {
    if (item.kind === "photowall") return (Number(item.photowall_minutes) || 12) * 60 * 1000;
    if (item.kind === "image" || (asset && asset.type === "image")) {
      if (item.playback === "loop") return (Number(item.loop_minutes) || 5) * 60 * 1000;
      if (item.playback === "repeat") return (Number(item.repeat_count) || 1) * (Number(item.image_seconds) || 8) * 1000;
      return (Number(item.image_seconds) || 8) * 1000;
    }
    if (item.playback === "loop") return (Number(item.loop_minutes) || 5) * 60 * 1000;
    var once = (asset && Number(asset.duration_sec) > 0) ? Number(asset.duration_sec) * 1000 : 8000;
    if (item.playback === "repeat") return (Number(item.repeat_count) || 1) * once;
    return once;
  }

  function popFrame(el, done) {
    var called = false;
    var finish = function () {
      if (called) return;
      called = true;
      if (done) done();
    };
    var frame = document.createElement("div");
    frame.id = "wmFrame";
    var size = 150;
    try {
      if (global.config && global.config.image_max_size) size = Number(global.config.image_max_size) || 150;
    } catch (e) {}
    frame.style.width = size + "px";
    frame.style.left = "50%";
    frame.style.top = "50%";
    frame.style.transform = "translate(-50%,-50%)";
    frame.appendChild(el);
    state.stage.appendChild(frame);
    void frame.offsetWidth;
    var vw = (state.stage && state.stage.clientWidth) || window.innerWidth;
    var vh = (state.stage && state.stage.clientHeight) || window.innerHeight;
    frame.style.transition = "width .8s ease, height .8s ease, transform .8s ease, left .8s ease, top .8s ease";
    frame.style.width = vw + "px";
    frame.style.height = vh + "px";
    frame.style.left = "0";
    frame.style.top = "0";
    frame.style.transform = "none";
    el.style.width = "100%";
    el.style.height = "100%";
    el.style.objectFit = "contain";
    setTimeout(function () {
      unwrapPopFrame();
      finish();
    }, 850);
  }

  function waitMediaReady(el, ms) {
    return new Promise(function (resolve) {
      if (!el) return resolve();
      var limit = Math.max(200, Number(ms) || 800);
      var done = function () {
        el.removeEventListener("loadeddata", done);
        el.removeEventListener("canplay", done);
        el.removeEventListener("playing", done);
        el.removeEventListener("load", done);
        el.removeEventListener("error", done);
        resolve();
      };
      if (el.tagName === "IMG") {
        if (el.complete && el.naturalWidth) return resolve();
        el.addEventListener("load", done);
        el.addEventListener("error", done);
        setTimeout(done, limit);
        return;
      }
      if (el.readyState >= 2) return resolve();
      el.addEventListener("loadeddata", done);
      el.addEventListener("canplay", done);
      el.addEventListener("playing", done);
      el.addEventListener("error", done);
      if (typeof el.requestVideoFrameCallback === "function") {
        try { el.requestVideoFrameCallback(function () { done(); }); } catch (e) {}
      }
      setTimeout(done, limit);
    });
  }

  function keepStageEl(el) {
    unwrapPopFrame();
    if (!state.stage || !el) return;
    var kids = Array.prototype.slice.call(state.stage.childNodes);
    for (var i = 0; i < kids.length; i++) {
      if (kids[i] !== el) {
        revokeElSrc(kids[i]);
        if (kids[i].querySelectorAll) {
          var nested = kids[i].querySelectorAll("img, video");
          for (var n = 0; n < nested.length; n++) revokeElSrc(nested[n]);
        }
        state.stage.removeChild(kids[i]);
      }
    }
    state.stage.classList.remove("is-pop");
  }

  async function putMediaEl(item, asset, pop, opts) {
    opts = opts || {};
    var isVideo = asset.type === "video";
    var el = document.createElement(isVideo ? "video" : "img");
    if (isVideo) {
      el.playsInline = true;
      el.setAttribute("playsinline", "");
      el.preload = "auto";
      el.autoplay = !opts.hold;
      el.muted = !state.audioUnlocked || wantMute(item);
      if (!state.audioUnlocked && !wantMute(item) && state.tap) state.tap.classList.add("is-on");
    }
    showLayer();
    if (!opts.hold && !pop) snapBlack(0);
    if (pop) clearStage();
    else if (!opts.overlap && !opts.hold) clearStage();
    var url = await srcFor(asset);
    if (pop) {
      await new Promise(function (resolve) {
        var started = false;
        var go = function () {
          if (started) return;
          started = true;
          popFrame(el, resolve);
        };
        el.onload = go;
        el.oncanplay = go;
        el.src = url;
        if (!isVideo && el.complete) go();
        setTimeout(go, 2000);
      });
    } else {
      if (opts.overlap) {
        markOutgoing();
        if (state.stage) {
          state.stage.classList.add("has-overlap");
          state.stage.appendChild(el);
        }
        el.classList.add("wmIncoming");
        if (opts.wipe) {
          el.style.opacity = "1";
          el.style.clipPath = wipeClip(0, opts.direction || "ltr");
        } else {
          el.style.opacity = "0";
        }
      } else if (opts.hold && state.stage) state.stage.appendChild(el);
      else if (state.stage) state.stage.appendChild(el);
      el.src = url;
      try { if (isVideo && el.load) el.load(); } catch (e) {}
      if (isVideo && !opts.hold) {
        try { el.play(); } catch (e) {}
      }
      var pauseHold = function () {
        if (!isVideo) return;
        try { el.pause(); } catch (e) {}
        try { if (el.currentTime > 0.05) el.currentTime = 0; } catch (e) {}
      };
      if (opts.hold) {
        if (opts.wipe) waitMediaReady(el, 800).then(pauseHold);
        else {
          await waitMediaReady(el, 800);
          pauseHold();
        }
      }
      if (!opts.overlap) keepStageEl(el);
    }
    state.media = el;
    if (isVideo && !opts.hold) {
      try { await el.play(); } catch (e) {
        if (!wantMute(item) && state.tap) state.tap.classList.add("is-on");
      }
    }
  }

  function playThrough(video) {
    return new Promise(function (resolve) {
      if (!video) return resolve();
      var finished = false;
      var done = function () {
        if (finished) return;
        finished = true;
        video.removeEventListener("ended", done);
        video.removeEventListener("error", done);
        resolve();
      };
      video.addEventListener("ended", done);
      video.addEventListener("error", done);
      var dur = Number(video.duration);
      var ms = (dur && isFinite(dur) ? dur * 1000 : 120000) + 4000;
      setTimeout(done, ms);
      if (video.ended) done();
    });
  }

  async function waitClipPlayback(item, asset, gen) {
    var media = state.media;
    if (item.kind === "image" || (asset && asset.type === "image")) {
      await waitMs(clipMs(item, asset), gen);
      return;
    }
    if (!media || media.tagName !== "VIDEO") {
      await waitMs(clipMs(item, asset), gen);
      return;
    }
    if (item.playback === "loop") {
      media.loop = true;
      try { await media.play(); } catch (e) {}
      await waitMs(clipMs(item, asset), gen);
      try { media.pause(); } catch (e) {}
      return;
    }
    var times = item.playback === "repeat" ? (Number(item.repeat_count) || 1) : 1;
    for (var n = 0; n < times; n++) {
      if (gen !== state.gen) return;
      try {
        if (n > 0 || (media.currentTime || 0) > 0.2) media.currentTime = 0;
        await media.play();
      } catch (e) {}
      await playThrough(media);
    }
  }

  async function animateOverlap(ms, mode, direction, gen) {
    var remain = Math.max(80, ms);
    if (mode === "wipe") startWipeAnim(0, remain, direction);
    else startDissolveAnim(0, remain);
    await waitMs(remain, gen);
    endOverlap();
  }

  async function crossTo(nextKind, putFn, fx, gen) {
    var ms = fadeMs(fx);
    var dissolve = fxMs(fx, "dissolve");
    var wipe = fxMs(fx, "wipe");
    var dir = wipeDir(fx);
    var pop = hasPop(fx) && nextKind !== "photowall";
    showLayer();
    if (ms) {
      await fadeBlack(true, ms, gen);
      if (gen !== state.gen) return;
      if (nextKind === "photowall") {
        clearStage();
        await fadeBlack(false, ms, gen);
        hideLayer();
        return;
      }
      if (putFn) await putFn(pop, { hold: true });
      await fadeBlack(false, ms, gen);
      return;
    }
    if (dissolve) {
      if (nextKind === "photowall") {
        markOutgoing();
        await animateOverlap(dissolve, "dissolve", dir, gen);
        hideLayer();
        return;
      }
      if (putFn) await putFn(pop, { hold: true, overlap: true });
      if (gen !== state.gen) return;
      await animateOverlap(dissolve, "dissolve", dir, gen);
      return;
    }
    if (wipe) {
      if (nextKind === "photowall") {
        markOutgoing();
        await animateOverlap(wipe, "wipe", dir, gen);
        hideLayer();
        return;
      }
      if (putFn) await putFn(pop, { hold: true, overlap: true, wipe: true, direction: dir });
      if (gen !== state.gen) return;
      await animateOverlap(wipe, "wipe", dir, gen);
      return;
    }
    if (nextKind === "photowall") {
      hideLayer();
      return;
    }
    if (putFn) await putFn(pop);
  }

  function setBlack(p) {
    snapBlack(p);
  }

  function nextMediaFrom(idx) {
    var n = state.playlist.length;
    for (var k = 1; k <= n; k++) {
      var j = (idx + k) % n;
      if (isMedia(state.playlist[j])) return { item: state.playlist[j], index: j };
    }
    return null;
  }

  function precedingEffects(idx) {
    var out = [];
    var n = state.playlist.length;
    if (!n || idx < 0) return out;
    for (var k = 1; k < n; k++) {
      var j = (idx - k + n) % n;
      var it = state.playlist[j];
      if (isEffect(it)) out.unshift(it);
      else break;
    }
    return out;
  }

  function skippedBetween(fromIdx, toIdx) {
    var out = [];
    var n = state.playlist.length;
    if (!n || fromIdx < 0 || toIdx < 0 || fromIdx === toIdx) return out;
    var j = (fromIdx + 1) % n;
    var hops = 0;
    while (j !== toIdx && hops < n) {
      out.push(state.playlist[j]);
      j = (j + 1) % n;
      hops += 1;
    }
    return out;
  }

  function fxListHas(fx, name) {
    for (var i = 0; i < fx.length; i++) {
      if (fx[i] && fx[i].effect === name) return true;
    }
    return false;
  }

  function onlyShortFx(items) {
    if (!items.length) return false;
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (!it || it.kind !== "effect") return false;
      if (it.effect !== "cut" && it.effect !== "pop") return false;
    }
    return true;
  }

  function seekMedia(item, asset, elapsed) {
    var media = state.media;
    if (!media || media.tagName !== "VIDEO" || !asset) return;
    var once = Number(asset.duration_sec) > 0 ? Number(asset.duration_sec) : 8;
    var t = Number(elapsed) || 0;
    if (item.playback === "loop" || item.playback === "repeat") t = t % once;
    if (isFinite(media.duration) && media.duration > 0 && t > media.duration - 0.05) {
      t = Math.max(0, media.duration - 0.05);
    }
    if (Math.abs((media.currentTime || 0) - t) > 0.55) {
      try { media.currentTime = Math.max(0, t); } catch (e) {}
    }
    media.loop = item.playback === "loop";
    media.muted = !state.audioUnlocked || wantMute(item);
    try { media.play().catch(function () {}); } catch (e) {}
  }

  function sameClipMounted(asset) {
    return !!(asset && ((state.mediaAssetId === asset.id && mediaConnected()) || (state.mountingAssetId === asset.id)));
  }

  async function mountMedia(item, elapsed, pop, opts) {
    opts = opts || {};
    var asset = assetById(item.asset_id);
    if (!asset || !asset.display) {
      debugLog("Wall Manager: Datei fehlt, Slot übersprungen");
      return;
    }
    if (!pop && sameClipMounted(asset)) {
      if (state.media && !opts.hold && !opts.skipSeek) seekMedia(item, asset, elapsed);
      return;
    }
    state.mountingAssetId = asset.id;
    try {
      await putMediaEl(item, asset, !!pop, opts);
      state.mediaAssetId = asset.id;
      if (!opts.hold && !opts.skipSeek && (Number(elapsed) || 0) > 0.4) {
        seekMedia(item, asset, elapsed);
      }
    } finally {
      if (state.mountingAssetId === asset.id) state.mountingAssetId = null;
    }
  }

  function finishIfLeavingWall(nextItem) {
    if (!nextItem || nextItem.kind === "photowall") return;
    var pw = photowall();
    if (pw && pw.pause) pw.pause();
  }

  async function showPhotowallLive(item, fading) {
    setChrome(null);
    ensureWall(item);
    if (!fading) {
      setBlack(0);
      hideLayer();
    }
    state.currentLabel = "Photowall " + item.enter + " " + item.photowall_minutes + " min";
  }

  function armPreloadFrom(ph) {
    var item = state.playlist[ph.index];
    if (!item || (item.kind !== "video" && item.kind !== "image")) return;
    var nxt = nextMediaFrom(ph.index);
    if (!nxt || nxt.item.kind !== "photowall") return;
    var remain = Math.max(0, (Number(ph.duration_sec) || 0) - (Number(ph.elapsed_sec) || 0));
    var pre = Number(nxt.item.photowall_preload_sec);
    if (pre !== 0 && !pre) pre = 15;
    if (remain <= pre) ensureWall(nxt.item);
  }

  async function ensureIncoming(nextItem, opts) {
    opts = opts || {};
    var asset = assetById(nextItem.asset_id);
    if (!asset || !asset.display) return;
    if (state.stage) {
      var inc = state.stage.querySelector(".wmIncoming");
      if (inc && state.mediaAssetId === asset.id) return;
    }
    finishIfLeavingWall(nextItem);
    setChrome(nextItem);
    state.mountingAssetId = asset.id;
    try {
      await putMediaEl(nextItem, asset, false, {
        hold: true,
        skipSeek: true,
        overlap: true,
        wipe: !!opts.wipe,
        direction: opts.direction || "ltr"
      });
      state.mediaAssetId = asset.id;
    } finally {
      if (state.mountingAssetId === asset.id) state.mountingAssetId = null;
    }
  }

  async function applyEffect(item, ph, entered) {
    var nxt = nextMediaFrom(ph.index);
    var nextItem = nxt && nxt.item;
    showLayer();
    if (item.effect === "cut") {
      setBlack(0);
      endOverlap();
      if (nextItem && nextItem.kind === "photowall") await showPhotowallLive(nextItem, false);
      else if (nextItem) {
        finishIfLeavingWall(nextItem);
        setChrome(nextItem);
        state.poppedSlot = null;
        await mountMedia(nextItem, 0, false);
      }
      return;
    }
    if (item.effect === "pop") {
      setBlack(0);
      if (!$("wmFrame")) endOverlap();
      if (nextItem && nextItem.kind === "photowall") await showPhotowallLive(nextItem, false);
      else if (nextItem) {
        finishIfLeavingWall(nextItem);
        setChrome(nextItem);
        var pop = entered && nextItem.kind !== "photowall";
        if (pop) state.poppedSlot = nextItem.id;
        await mountMedia(nextItem, 0, pop);
      }
      return;
    }
    if (item.effect === "dissolve" || item.effect === "wipe") {
      var dur = Math.max(0.2, Number(item.duration_sec) || 5);
      var e = Number(ph.elapsed_sec) || 0;
      var mode = item.effect;
      var dir = item.direction || "ltr";
      if (dir !== "rtl" && dir !== "ttb" && dir !== "btt") dir = "ltr";
      setBlack(0);
      var needStart = state.fxMode !== mode;
      if (!needStart && mode === "wipe" && nextItem && nextItem.kind !== "photowall") {
        var inc = state.stage && state.stage.querySelector(".wmIncoming");
        if (!inc) needStart = true;
      }
      if (needStart) {
        state.fxMode = mode;
        if (nextItem && nextItem.kind === "photowall") {
          markOutgoing();
          await showPhotowallLive(nextItem, true);
        } else if (nextItem) {
          await ensureIncoming(nextItem, { wipe: mode === "wipe", direction: dir });
        }
        var remain = Math.max(80, (dur - e) * 1000);
        var fromP = Math.max(0, Math.min(1, e / dur));
        if (mode === "wipe") startWipeAnim(fromP, remain, dir);
        else startDissolveAnim(fromP, remain);
      }
      return;
    }
    var half = Math.max(0.2, Number(item.duration_sec) || 5);
    var e = Number(ph.elapsed_sec) || 0;
    if (e <= half) {
      if (state.fadeHalf !== "out") {
        state.fadeHalf = "out";
        showLayer();
        animateBlackTo(1, Math.max(80, (half - e) * 1000), e / half);
      }
      return;
    }
    if (state.fadeHalf !== "in") {
      state.fadeHalf = "in";
      snapBlack(1);
      if (nextItem && nextItem.kind === "photowall") {
        clearStage();
        state.mediaAssetId = null;
        await showPhotowallLive(nextItem, true);
      } else if (nextItem) {
        finishIfLeavingWall(nextItem);
        setChrome(nextItem);
        await mountMedia(nextItem, 0, false, { hold: true, skipSeek: true });
      }
      animateBlackTo(0, Math.max(80, (half * 2 - e) * 1000), 1);
    }
  }

  async function playPhotowall(item, fx, nextItem, gen) {
    setChrome(null);
    ensureWall(item);
    await crossTo("photowall", null, fx, gen);
    state.currentLabel = "Photowall " + item.enter + " " + item.photowall_minutes + " min";
    debugLog("Wall Manager: " + state.currentLabel);
    var ok = await waitMs(clipMs(item), gen);
    if (!ok) return;
    finishWall(item);
  }

  async function playClip(item, fx, nextItem, gen) {
    var asset = assetById(item.asset_id);
    if (!asset || !asset.display) {
      debugLog("Wall Manager: Datei fehlt, Slot übersprungen");
      return;
    }
    setChrome(item);
    state.currentLabel = (asset.type === "video" ? "Video" : "Bild") + " " + (asset.title || asset.display);
    debugLog("Wall Manager: " + state.currentLabel);
    await crossTo(item.kind, function (pop, opts) { return putMediaEl(item, asset, pop, opts); }, fx, gen);
    if (gen !== state.gen) return;
    armPreload(nextItem, clipMs(item, asset), gen);
    prefetchAround(state.idx);
    await waitClipPlayback(item, asset, gen);
  }

  async function runLoop() {
    var gen = state.gen;
    state.wallArmed = false;
    if (!state.enabled || !state.playlist.length || firstMediaIdx() < 0) {
      releaseToPhotowall();
      return;
    }
    var first = state.playlist[firstMediaIdx()];
    if (first.kind !== "photowall") {
      var p = photowall();
      if (p && p.pause) p.pause();
    }
    var i = firstMediaIdx();
    var incoming = [];
    for (var k = 0; k < i; k++) {
      if (isEffect(state.playlist[k])) incoming.push(state.playlist[k]);
    }
    while (gen === state.gen && !state.following) {
      var item = state.playlist[i];
      var nxt = nextMediaIdx(i);
      var outgoing = effectsAfter(i);
      prefetchAround(i);
      state.idx = i;
      if (item.kind === "photowall") await playPhotowall(item, incoming, state.playlist[nxt], gen);
      else await playClip(item, incoming, state.playlist[nxt], gen);
      if (gen !== state.gen || state.following) return;
      incoming = outgoing;
      i = nxt;
    }
  }

  function releaseToPhotowall() {
    hideLayer();
    setChrome(null);
    setBlack(0);
    cancelWipeTick();
    state.following = false;
    state.appliedIndex = -1;
    state.fxMode = "";
    state.fadeHalf = "";
    state.mediaAssetId = null;
    state.mountingAssetId = null;
    state.poppedSlot = null;
    var pw = photowall();
    if (pw && pw.startTimers) pw.startTimers();
  }

  async function applyPlayhead(ph) {
    if (state.applyBusy) {
      state.applyQueued = ph;
      return;
    }
    state.applyBusy = true;
    try {
      await applyPlayheadNow(ph);
    } finally {
      state.applyBusy = false;
      if (state.applyQueued) {
        var next = state.applyQueued;
        state.applyQueued = null;
        await applyPlayhead(next);
      }
    }
  }

  async function applyPlayheadNow(ph) {
    if (!ph || !state.enabled || ph.index < 0 || !state.playlist.length) {
      if (state.enabled && firstMediaIdx() >= 0) return;
      releaseToPhotowall();
      state.currentLabel = "aus";
      return;
    }
    var item = state.playlist[ph.index];
    if (!item) return;
    state.following = true;
    state.idx = ph.index;
    var prevIdx = state.appliedIndex;
    var entered = prevIdx !== ph.index || state.slotStarted !== ph.started;
    if (entered) {
      var prevItem = prevIdx >= 0 ? state.playlist[prevIdx] : null;
      if (prevItem && prevItem.kind === "photowall" && item.kind !== "photowall") {
        finishWall(prevItem);
      }
      state.appliedIndex = ph.index;
      state.slotStarted = ph.started;
      state.fadeHalf = "";
      state.fxMode = "";
      state.slotId = item.id;
      debugLog("Wall Manager: Slot " + (ph.index + 1) + " " + (item.kind || ""));
    }
    armPreloadFrom(ph);
    prefetchAround(ph.index);
    if (item.kind === "effect") {
      await applyEffect(item, ph, entered);
      state.currentLabel = "Effekt " + (item.effect || "");
      return;
    }
    var skipped = skippedBetween(prevIdx, ph.index);
    var shortSkip = onlyShortFx(skipped);
    var gate = precedingEffects(ph.index);
    var e = Number(ph.elapsed_sec) || 0;
    var arrivePop = item.kind !== "photowall" && (
      (shortSkip && fxListHas(skipped, "pop")) ||
      (prevIdx < 0 && fxListHas(gate, "pop") && e < 0.5)
    );
    if (entered) {
      var popLive = !!$("wmFrame") || (state.poppedSlot && state.poppedSlot === item.id);
      if (!popLive) endOverlap();
    }
    snapBlack(0);
    if (item.kind === "photowall") {
      await showPhotowallLive(item, false);
      return;
    }
    showLayer();
    finishIfLeavingWall(item);
    setChrome(item);
    var asset = assetById(item.asset_id);
    state.currentLabel = asset ? ((asset.type === "video" ? "Video" : "Bild") + " " + (asset.title || asset.display)) : "Clip";
    if (arrivePop && state.poppedSlot !== item.id && e < 0.55) {
      state.poppedSlot = item.id;
      await mountMedia(item, 0, true);
      return;
    }
    await mountMedia(item, e, false);
  }

  async function pullPlayhead(force) {
    if (!force && state.clock === "local") return;
    var ph = null;
    try {
      var res = await fetch(pf("/api/wall-manager/playhead"), { cache: "no-store" });
      if (res.ok) {
        ph = await res.json();
        state.clock = "playhead";
      }
    } catch (e) {}
    if (!ph || ph.index < 0) {
      try {
        var full = await fetch(pf("/api/wall-manager"), { cache: "no-store" });
        if (full.ok) {
          var data = await full.json();
          state.enabled = !!data.enabled;
          state.prefetch = data.prefetch === "all" ? "all" : state.prefetch;
          state.muteAll = !!data.mute_all;
          state.assets = data.assets || state.assets;
          state.playlist = coercePlaylist(data.playlist || state.playlist);
          ph = data.playhead || null;
          state.clock = (ph && ph.index >= 0) ? "full" : "local";
        } else {
          state.clock = "local";
        }
      } catch (e) {
        state.clock = "local";
      }
    }
    if (!ph || ph.index < 0) return;
    if (!state.following) state.gen += 1;
    await applyPlayhead(ph);
  }

  function startFollow() {
    if (state.followTimer) clearInterval(state.followTimer);
    state.followTimer = setInterval(function () { pullPlayhead(false); }, 300);
  }

  function coercePlaylist(list) {
    return (list || []).map(function (it) {
      if (!it || it.kind === "effect") return it;
      var trans = it.transition || it.effect;
      var minutes = Number(it.photowall_minutes == null ? 12 : it.photowall_minutes);
      if (it.kind === "photowall" && (trans === "fade" || trans === "pop") && Math.abs(minutes - 12) < 0.001 && (it.enter || "start") === "start" && (it.exit || "pause") === "pause") {
        return { id: it.id, kind: "effect", effect: trans === "pop" ? "pop" : "fade", duration_sec: Number(it.duration_sec) || 5 };
      }
      return it;
    });
  }

  async function load() {
    var res = await fetch(pf("/api/wall-manager"), { cache: "no-store" });
    if (!res.ok) {
      state.enabled = false;
      state.playlist = [];
      return null;
    }
    var data = await res.json();
    state.enabled = !!data.enabled;
    state.prefetch = data.prefetch === "all" ? "all" : "next";
    state.muteAll = !!data.mute_all;
    state.assets = data.assets || [];
    state.playlist = coercePlaylist(data.playlist || []);
    return data.playhead || null;
  }

  async function startProgram(ph) {
    state.gen += 1;
    state.appliedIndex = -1;
    state.following = false;
    state.fxMode = "";
    state.fadeHalf = "";
    state.mediaAssetId = null;
    state.mountingAssetId = null;
    state.poppedSlot = null;
    state.applyBusy = false;
    state.applyQueued = null;
    state.prefetchBusy = {};
    state.prefetchChain += 1;
    cancelWipeTick();
    state.clock = "";
    startFollow();
    if (state.enabled && ph && typeof ph.index === "number" && ph.index >= 0) {
      await applyPlayhead(ph);
      return;
    }
    if (state.enabled && firstMediaIdx() >= 0) {
      state.currentLabel = "aktiv";
      runLoop();
      return;
    }
    releaseToPhotowall();
    state.currentLabel = "aus";
  }

  async function boot() {
    ensureLayer();
    var ph = await load();
    refreshCacheStats();
    await startProgram(ph);
  }

  async function reload() {
    var ph = await load();
    refreshCacheStats();
    await startProgram(ph);
  }

  function fmtBytes(n) {
    n = Number(n) || 0;
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
    return (n / 1073741824).toFixed(2) + " GB";
  }

  function debugLine() {
    if (!state.enabled) return "Wall Manager: aus";
    var q = state.quotaBytes ? ", Quota " + fmtBytes(state.quotaUsage) + "/" + fmtBytes(state.quotaBytes) : "";
    return "Wall Manager: an · " + (state.currentLabel || "aktiv") + "<br>Programm-Cache: " + state.cacheFiles + " Dateien, " + fmtBytes(state.cacheBytes) + " (max " + PROGRAM_MAX_FILES + ")" + q;
  }

  global.pfWallManager = {
    boot: boot,
    reload: reload,
    sync: function () { return pullPlayhead(true); },
    debugLine: debugLine
  };
})(window);
