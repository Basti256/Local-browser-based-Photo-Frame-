(function () {
  "use strict";

  var assets = [];
  var playlist = [];
  var ffmpeg = true;
  var selected = -1;
  var liveIndex = -1;
  var liveStarted = 0;
  var liveDuration = 0;
  var wallClients = 0;
  var dragFrom = -1;
  var playTimer = 0;
  var clockTimer = 0;
  var lastClientPoll = 0;

  function $(id) {
    return document.getElementById(id);
  }

  function pf(path) {
    return typeof window.pfUrl === "function" ? window.pfUrl(path) : path;
  }

  function esc(s) {
    return String(s || "").replace(/[&<>"]/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c];
    });
  }

  function newId() {
    return "p" + Math.random().toString(16).slice(2) + Date.now().toString(16);
  }

  function assetById(id) {
    for (var i = 0; i < assets.length; i++) {
      if (assets[i].id === id) return assets[i];
    }
    return null;
  }

  function assetTitle(id) {
    var a = assetById(id);
    return a ? (a.title || a.display || id) : "";
  }

  function assetsOf(type) {
    return assets.filter(function (a) { return a.type === type; });
  }

  function defaultItem(kind, effect) {
    if (kind === "effect") {
      var row = {
        id: newId(),
        kind: "effect",
        effect: effect || "fade",
        duration_sec: 5
      };
      if (row.effect === "wipe") row.direction = "ltr";
      return row;
    }
    var item = {
      id: newId(),
      kind: kind,
      asset_id: null,
      playback: "once",
      loop_minutes: 5,
      repeat_count: 2,
      show_banner: true,
      show_qr: true,
      mute: false
    };
    if (kind === "image") item.image_seconds = 8;
    if (kind === "photowall") {
      item.photowall_minutes = 12;
      item.photowall_preload_sec = 15;
      item.enter = "start";
      item.exit = "pause";
    }
    return item;
  }

  function isConvertedEffect(it) {
    if (!it) return false;
    if (it.kind === "effect" || it.kind === "fade" || it.kind === "pop" || it.kind === "cut" || it.kind === "dissolve" || it.kind === "wipe") return true;
    if (it.kind !== "photowall") return false;
    var trans = it.transition || it.effect;
    if (trans !== "fade" && trans !== "pop") return false;
    if (Math.abs(Number(it.photowall_minutes == null ? 12 : it.photowall_minutes) - 12) > 0.001) return false;
    if ((it.enter || "start") !== "start") return false;
    if ((it.exit || "pause") !== "pause") return false;
    return true;
  }

  function asEffect(it) {
    var trans = it.effect || it.transition || "fade";
    if (["fade", "pop", "cut", "dissolve", "wipe"].indexOf(trans) < 0) trans = "fade";
    var row = {
      id: it.id,
      kind: "effect",
      effect: trans,
      duration_sec: Number(it.duration_sec) || 5
    };
    if (trans === "wipe") {
      var d = it.direction || "ltr";
      if (["ltr", "rtl", "ttb", "btt"].indexOf(d) < 0) d = "ltr";
      row.direction = d;
    }
    return row;
  }

  function coercePlaylist(list) {
    return (list || []).map(function (it) {
      return isConvertedEffect(it) && it.kind !== "effect" ? asEffect(it) : it;
    });
  }

  function serializePlaylist() {
    return playlist.map(function (it) {
      if (it.kind === "effect" || isConvertedEffect(it)) {
        var row = asEffect(it);
        return row;
      }
      if (it.kind === "photowall") {
        return {
          id: it.id,
          kind: "photowall",
          photowall_minutes: Number(it.photowall_minutes) || 12,
          photowall_preload_sec: it.photowall_preload_sec == null ? 15 : Number(it.photowall_preload_sec),
          enter: it.enter || "start",
          exit: it.exit || "pause"
        };
      }
      var row = {
        id: it.id,
        kind: it.kind,
        asset_id: it.asset_id || null,
        playback: it.playback || "once",
        loop_minutes: Number(it.loop_minutes) || 5,
        repeat_count: Number(it.repeat_count) || 2,
        show_banner: it.show_banner !== false,
        show_qr: it.show_qr !== false,
        mute: !!it.mute
      };
      if (it.kind === "image") row.image_seconds = Number(it.image_seconds) || 8;
      return row;
    });
  }

  function pad2(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function fmtClock(sec) {
    sec = Math.max(0, Math.floor(Number(sec) || 0));
    var h = Math.floor(sec / 3600);
    var m = Math.floor((sec % 3600) / 60);
    var s = sec % 60;
    if (h > 0) return h + ":" + pad2(m) + ":" + pad2(s);
    return m + ":" + pad2(s);
  }

  function itemPlaySec(it) {
    if (!it) return 0;
    if (it.kind === "effect" || isConvertedEffect(it)) {
      var fx = asEffect(it);
      if (fx.effect === "fade") return Math.max(0.4, (Number(fx.duration_sec) || 5) * 2);
      if (fx.effect === "pop") return 0.85;
      if (fx.effect === "dissolve" || fx.effect === "wipe") return Math.max(0.2, Number(fx.duration_sec) || 5);
      return 0.05;
    }
    if (it.kind === "photowall") return Math.max(1, (Number(it.photowall_minutes) || 12) * 60);
    var playback = it.playback || "once";
    if (it.kind === "image") {
      var imgOnce = Number(it.image_seconds) || 8;
      if (playback === "loop") return Math.max(1, (Number(it.loop_minutes) || 5) * 60);
      if (playback === "repeat") return Math.max(0.5, (Number(it.repeat_count) || 1) * imgOnce);
      return Math.max(0.5, imgOnce);
    }
    var a = assetById(it.asset_id);
    var once = a && Number(a.duration_sec) > 0 ? Number(a.duration_sec) : 8;
    if (playback === "loop") return Math.max(1, (Number(it.loop_minutes) || 5) * 60);
    if (playback === "repeat") return Math.max(0.5, (Number(it.repeat_count) || 1) * once);
    return Math.max(0.5, once);
  }

  function rowElapsed(i) {
    var total = itemPlaySec(playlist[i]);
    if (i === liveIndex && liveDuration > 0) total = liveDuration;
    var elapsed = 0;
    if (i === liveIndex && liveIndex >= 0 && liveStarted > 0) {
      elapsed = Math.max(0, Date.now() / 1000 - liveStarted);
      if (total > 0) elapsed = Math.min(elapsed, total);
    }
    return { elapsed: elapsed, total: total };
  }

  function rowClock(i) {
    var t = rowElapsed(i);
    return fmtClock(t.elapsed) + "/" + fmtClock(t.total);
  }

  function paintClients() {
    var el = $("wmWallClients");
    if (el) el.textContent = wallClients + " Verb. aktiv";
  }

  function paintClocks() {
    var box = $("wmPlaylist");
    if (!box) return;
    box.querySelectorAll(".wmItemTime").forEach(function (el) {
      var i = parseInt(el.getAttribute("data-i"), 10);
      el.textContent = rowClock(i);
    });
  }

  function applyPlayheadMeta(data) {
    if (!data) return false;
    var prev = liveIndex;
    if (typeof data.wall_clients === "number") {
      wallClients = data.wall_clients;
      paintClients();
    }
    if (typeof data.index === "number") liveIndex = data.index;
    else if (data.playhead && typeof data.playhead.index === "number") liveIndex = data.playhead.index;
    var ph = data.playhead && typeof data.playhead.index === "number" ? data.playhead : data;
    if (typeof ph.duration_sec === "number") liveDuration = ph.duration_sec;
    else liveDuration = liveIndex >= 0 ? itemPlaySec(playlist[liveIndex]) : 0;
    if (typeof ph.elapsed_sec === "number") liveStarted = Date.now() / 1000 - ph.elapsed_sec;
    else if (typeof ph.started === "number" && ph.started > 0) liveStarted = ph.started;
    else if (liveIndex < 0) liveStarted = 0;
    return prev !== liveIndex;
  }

  function rowLabel(it) {
    if (it.kind === "effect" || isConvertedEffect(it)) {
      var fx = asEffect(it);
      if (fx.effect === "pop") return "Effekt · Aufpoppen";
      if (fx.effect === "cut") return "Effekt · Harter Schnitt";
      if (fx.effect === "dissolve") return "Effekt · Weiche Blende (" + (fx.duration_sec || 5) + " s)";
      if (fx.effect === "wipe") return "Effekt · Wischblende (" + (fx.duration_sec || 5) + " s)";
      return "Effekt · Aus/Einblenden (" + (fx.duration_sec || 5) + " s)";
    }
    if (it.kind === "photowall") return "Photowall · " + (it.photowall_minutes || 12) + " min";
    var t = it.kind === "video" ? "Video" : "Bild";
    var name = assetTitle(it.asset_id);
    return name ? t + " · " + name : t + " · Datei wählen";
  }

  function closeAddMenu() {
    var m = $("wmAddMenu");
    if (m) m.hidden = true;
  }

  function renderList() {
    var box = $("wmPlaylist");
    if (!box) return;
    if (!playlist.length) {
      box.innerHTML = "<p class=\"wmMuted\">Leere Liste: die Photowall läuft wie bisher. Plus (+) fügt Medium oder Effekt hinzu.</p>";
      renderSide();
      return;
    }
    box.innerHTML = playlist.map(function (it, i) {
      var on = i === selected ? " is-on" : "";
      var live = i === liveIndex ? " is-live" : "";
      var kind = it.kind === "effect" ? "effect" : it.kind;
      return '<div class="wmItem' + on + live + '" draggable="true" data-i="' + i + '" data-kind="' + kind + '" title="Doppelklick: Wiedergabe hierher springen">' +
        '<span class="wmGrip" aria-hidden="true">⋮⋮</span>' +
        '<span class="wmItemLabel">' + esc(rowLabel(it)) + "</span>" +
        '<span class="wmItemTime" data-i="' + i + '" title="Laufzeit vergangen/gesamt">' + esc(rowClock(i)) + "</span>" +
        '<button type="button" class="wmItemRm" data-rm="' + i + '" title="Entfernen">×</button></div>';
    }).join("");
    box.querySelectorAll(".wmItem").forEach(function (row) {
      row.addEventListener("click", function (e) {
        if (e.target.closest("[data-rm]")) return;
        selected = parseInt(row.getAttribute("data-i"), 10);
        renderList();
      });
      row.addEventListener("dblclick", function (e) {
        e.preventDefault();
        e.stopPropagation();
        jumpTo(parseInt(row.getAttribute("data-i"), 10));
      });
      row.addEventListener("dragstart", function (e) {
        dragFrom = parseInt(row.getAttribute("data-i"), 10);
        row.classList.add("is-drag");
        try { e.dataTransfer.setData("text/plain", String(dragFrom)); } catch (err) {}
        e.dataTransfer.effectAllowed = "move";
      });
      row.addEventListener("dragend", function () {
        row.classList.remove("is-drag");
        dragFrom = -1;
      });
      row.addEventListener("dragover", function (e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        row.classList.add("is-over");
      });
      row.addEventListener("dragleave", function () { row.classList.remove("is-over"); });
      row.addEventListener("drop", function (e) {
        e.preventDefault();
        row.classList.remove("is-over");
        var to = parseInt(row.getAttribute("data-i"), 10);
        if (dragFrom < 0 || to === dragFrom) return;
        var item = playlist.splice(dragFrom, 1)[0];
        playlist.splice(to, 0, item);
        selected = to;
        renderList();
      });
    });
    box.querySelectorAll("[data-rm]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.stopPropagation();
        var i = parseInt(b.getAttribute("data-rm"), 10);
        playlist.splice(i, 1);
        if (selected === i) selected = -1;
        else if (selected > i) selected -= 1;
        renderList();
      });
    });
    renderSide();
  }

  function field(label, html) {
    return "<label>" + label + "</label>" + html;
  }

  function num(key, value, step) {
    return '<input type="number" step="' + (step || "1") + '" data-k="' + key + '" value="' + value + '">';
  }

  function sel(key, value, choices) {
    var h = '<select data-k="' + key + '">';
    choices.forEach(function (c) {
      h += '<option value="' + c[0] + '"' + (String(value) === String(c[0]) ? " selected" : "") + ">" + c[1] + "</option>";
    });
    return h + "</select>";
  }

  function chk(key, value, label) {
    return '<label class="wmChk"><input type="checkbox" data-k="' + key + '"' + (value ? " checked" : "") + "> " + label + "</label>";
  }

  function renderSide() {
    var side = $("wmSide");
    if (!side) return;
    var it = playlist[selected];
    if (!it) {
      side.innerHTML = "<p class=\"wmMuted\">Eintrag in der Liste anklicken, um Einstellungen zu sehen. Doppelklick springt die Wall auf diesen Punkt.</p>";
      return;
    }
    var h = "<h3>" + esc(rowLabel(it)) + "</h3>";
    if (it.kind === "effect" || isConvertedEffect(it)) {
      if (it.kind !== "effect") {
        var fx = asEffect(it);
        it.kind = fx.kind;
        it.effect = fx.effect;
        it.duration_sec = fx.duration_sec;
        delete it.photowall_minutes;
        delete it.transition;
      }
      h += field("Effekt", sel("effect", it.effect, [
        ["fade", "Aus/Einblenden"],
        ["dissolve", "Weiche Blende"],
        ["wipe", "Wischblende"],
        ["pop", "Aufpoppen"],
        ["cut", "Harter Schnitt"]
      ]));
      var durLabel = it.effect === "fade" ? "Dauer Aus- bzw. Einblenden (Sekunden)" : "Dauer (Sekunden)";
      var durHint = "Standard 5.";
      if (it.effect === "fade") durHint = "Gilt für das Abdunkeln und das Aufhellen jeweils einzeln. Standard 5.";
      else if (it.effect === "dissolve") durHint = "Vorheriges und nächstes Medium überlappen, ohne Schwarz. Standard 5.";
      else if (it.effect === "wipe") durHint = "Wischblende überdeckt das vorherige Medium. Standard 5.";
      h += '<div data-fx-duration>' + field(durLabel, num("duration_sec", it.duration_sec || 5, "0.1")) +
        "<p class=\"wmMuted\">" + durHint + "</p></div>";
      h += '<div data-wipe-dir>' + field("Richtung", sel("direction", it.direction || "ltr", [
        ["ltr", "Links nach rechts"],
        ["rtl", "Rechts nach links"],
        ["ttb", "Oben nach unten"],
        ["btt", "Unten nach oben"]
      ])) + "</div>";
    } else if (it.kind === "photowall") {
      h += field("Dauer (Minuten)", num("photowall_minutes", it.photowall_minutes, "0.1"));
      h += field("Vorher laden (Sekunden)", num("photowall_preload_sec", it.photowall_preload_sec == null ? 15 : it.photowall_preload_sec, "1"));
      h += "<p class=\"wmMuted\">Die Photowall startet so viele Sekunden vor dem Einblenden, unter dem vorherigen Clip.</p>";
      h += field("Am Anfang", sel("enter", it.enter, [["start", "starten"], ["resume", "fortsetzen"]]));
      h += field("Am Ende", sel("exit", it.exit, [["pause", "pausieren"], ["stop", "aus"]]));
    } else {
      h += "<label>Vorhandene Datei</label>" + filePick(it.kind, it.asset_id);
      h += "<label>Oder vom PC hochladen</label><input type=\"file\" id=\"wmSideFile\" accept=\"" +
        (it.kind === "video" ? "video/*" : "image/*") + "\">";
      h += "<p id=\"wmSideUpload\" class=\"wmMuted\"></p>";
      h += field("Wiedergabe", sel("playback", it.playback, [["once", "Einmal"], ["loop", "Loop"], ["repeat", "Mehrfach"]]));
      if (it.kind === "image") h += field("Anzeigedauer (Sekunden)", num("image_seconds", it.image_seconds, "0.5"));
      h += '<div class="wmCond" data-show="loop">' + field("Loopdauer (Minuten)", num("loop_minutes", it.loop_minutes, "0.1")) + "</div>";
      h += '<div class="wmCond" data-show="repeat">' + field("Wiederholungen", num("repeat_count", it.repeat_count, "1")) + "</div>";
      h += chk("show_banner", it.show_banner, "Banner") + chk("show_qr", it.show_qr, "QR-Code");
      if (it.kind === "video") h += chk("mute", it.mute, "Stumm");
    }
    side.innerHTML = h;
    side.querySelectorAll("[data-k]").forEach(function (el) {
      el.addEventListener("change", function () {
        var k = el.getAttribute("data-k");
        if (el.type === "checkbox") it[k] = el.checked;
        else if (el.type === "number") it[k] = parseFloat(el.value);
        else it[k] = el.value || null;
        if (k === "effect" && it.effect === "wipe" && !it.direction) it.direction = "ltr";
        renderList();
      });
    });
    side.querySelectorAll(".wmCond").forEach(function (c) {
      c.style.display = c.getAttribute("data-show") === it.playback ? "block" : "none";
    });
    var durBox = side.querySelector("[data-fx-duration]");
    if (durBox) durBox.style.display = (it.effect === "fade" || it.effect === "dissolve" || it.effect === "wipe") ? "block" : "none";
    var wipeDir = side.querySelector("[data-wipe-dir]");
    if (wipeDir) wipeDir.style.display = it.effect === "wipe" ? "block" : "none";
    var file = $("wmSideFile");
    if (file) file.addEventListener("change", function () { uploadToItem(it, file); });
    bindFilePick(it);
  }

  function fileSel(kind, value) {
    var list = assetsOf(kind);
    var h = '<select data-k="asset_id">';
    h += '<option value="">Datei wählen</option>';
    list.forEach(function (a) {
      h += '<option value="' + esc(a.id) + '"' + (value === a.id ? " selected" : "") + ">" + esc(a.title || a.display) + "</option>";
    });
    return h + "</select>";
  }

  function selectedPreview(a) {
    var h = '<div class="wmFileCard">';
    if (a) {
      h += '<button type="button" class="wmFileZoom" data-zoom="' + esc(a.id) + '" title="Größere Vorschau">';
      h += '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M14.5 14.5L20 20" stroke="currentColor" stroke-width="2" fill="none"/><path d="M10 7v6M7 10h6" stroke="currentColor" stroke-width="2"/></svg></button>';
      var mediaUrl = a.display ? pf("/wm/" + a.display) : "";
      if (a.type === "video" && mediaUrl) {
        h += '<video class="wmFileThumb" muted playsinline loop autoplay preload="auto" src="' + esc(mediaUrl) + '"></video>';
      } else if (mediaUrl) {
        h += '<img class="wmFileThumb" alt="" src="' + esc(mediaUrl) + '">';
      } else {
        h += '<div class="wmFileThumb wmFileThumbEmpty">' + (a.type === "video" ? "Video" : "Bild") + "</div>";
      }
    } else {
      h += '<div class="wmFileThumb wmFileThumbEmpty">Kein Medium</div>';
    }
    return h + "</div>";
  }

  function filePick(kind, value) {
    var list = assetsOf(kind);
    var chosen = assetById(value);
    var h = '<div class="wmFileRow">';
    h += selectedPreview(chosen);
    h += '<div class="wmFileSelectCol">';
    h += fileSel(kind, value);
    if (chosen) {
      h += '<button type="button" class="wmFileDel" data-del-asset="' + esc(chosen.id) + '" title="Datei löschen">🗑 Löschen</button>';
    } else if (!list.length) {
      h += "<p class=\"wmMuted\">Noch keine Datei. Unten hochladen.</p>";
    }
    h += "</div></div>";
    return h;
  }

  function bindFilePick(it) {
    var side = $("wmSide");
    if (!side) return;
    side.querySelectorAll("video.wmFileThumb").forEach(function (v) {
      v.muted = true;
      v.playsInline = true;
      var play = function () { v.play().catch(function () {}); };
      v.addEventListener("canplay", play, { once: true });
      play();
    });
    side.querySelectorAll("[data-zoom]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        openPreviewAsset(assetById(b.getAttribute("data-zoom")));
      });
    });
    side.querySelectorAll("[data-del-asset]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        deleteAsset(b.getAttribute("data-del-asset"), it);
      });
    });
  }

  async function deleteAsset(id, it) {
    var a = assetById(id);
    var name = a ? (a.title || a.display) : "Datei";
    if (!window.confirm("„" + name + "“ wirklich löschen?")) return;
    try {
      var res = await fetch(pf("/api/admin/wall-manager/asset/" + encodeURIComponent(id)), { method: "DELETE" });
      if (!res.ok) return;
      assets = assets.filter(function (x) { return x.id !== id; });
      playlist.forEach(function (row) {
        if (row.asset_id === id) row.asset_id = null;
      });
      if (it && it.asset_id === id) it.asset_id = null;
      renderList();
    } catch (err) {}
  }

  async function uploadToItem(it, input) {
    var status = $("wmSideUpload");
    if (!input.files || !input.files[0]) return;
    if (status) status.textContent = "Hochladen und ggf. umwandeln…";
    var fd = new FormData();
    fd.append("file", input.files[0]);
    try {
      var res = await fetch(pf("/api/admin/wall-manager/upload"), { method: "POST", body: fd });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        if (status) status.textContent = data.detail || "Upload fehlgeschlagen.";
        return;
      }
      assets.push(data);
      it.asset_id = data.id;
      if (status) status.textContent = data.transcode_status === "ready" ? "Gespeichert." : (data.transcode_error || "Gespeichert.");
      input.value = "";
      renderList();
    } catch (e) {
      if (status) status.textContent = "Upload fehlgeschlagen.";
    }
  }

  function openPreviewAsset(a) {
    var modal = $("wmPreview");
    var frame = $("wmPreviewFrame");
    if (!modal || !frame) return;
    frame.innerHTML = "";
    if (!a || !a.display) {
      frame.textContent = "Kein Medium gewählt.";
      modal.hidden = false;
      return;
    }
    var url = pf("/wm/" + a.display);
    var el;
    if (a.type === "video") {
      el = document.createElement("video");
      el.controls = true;
      el.autoplay = true;
      el.muted = true;
      el.playsInline = true;
      el.src = url;
    } else {
      el = document.createElement("img");
      el.alt = a.title || "";
      el.src = url;
    }
    frame.appendChild(el);
    modal.hidden = false;
  }

  function addItem(kind, effect) {
    playlist.push(defaultItem(kind, effect));
    selected = playlist.length - 1;
    closeAddMenu();
    renderList();
  }

  async function jumpTo(index) {
    if (index < 0 || index >= playlist.length) return;
    selected = index;
    var status = $("wmSaveStatus");
    var payload = {
      enabled: $("wm_enabled") ? $("wm_enabled").checked : false,
      prefetch: $("wm_prefetch") ? $("wm_prefetch").value : "next",
      mute_all: $("wm_mute_all") ? $("wm_mute_all").checked : false,
      playlist: serializePlaylist(),
      jump: index
    };
    try {
      var res = await fetch(pf("/api/admin/wall-manager/jump"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index: index, id: playlist[index] && playlist[index].id })
      });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        res = await fetch(pf("/api/admin/wall-manager"), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        data = await res.json().catch(function () { return {}; });
      }
      if (!res.ok) {
        if (status) status.textContent = typeof data.detail === "string" ? data.detail : "Sprung fehlgeschlagen. Prozess neu starten, dann erneut Doppelklick.";
        renderList();
        return;
      }
      var hasPh = (data.playhead && typeof data.playhead.index === "number") || typeof data.index === "number";
      if (!hasPh) {
        if (status) status.textContent = "Sprung braucht einen neu gestarteten Photo-Frame-Prozess, dann Admin und Wall neu laden.";
        renderList();
        return;
      }
      if (data.playlist) playlist = coercePlaylist(data.playlist);
      applyPlayheadMeta(data.playhead || data);
      if (status) status.textContent = "Wiedergabe springt auf: " + rowLabel(playlist[index] || {});
    } catch (e) {
      if (status) status.textContent = "Sprung fehlgeschlagen.";
    }
    renderList();
  }

  async function pollPlayhead() {
    try {
      var res = await fetch(pf("/api/admin/wall-manager/playhead"), { cache: "no-store" });
      if (!res.ok) {
        await pollClientsFallback();
        paintClocks();
        return;
      }
      var data = await res.json();
      var jumped = applyPlayheadMeta(data);
      if (typeof data.wall_clients !== "number") await pollClientsFallback();
      if (jumped) renderList();
      else paintClocks();
    } catch (e) {
      paintClocks();
    }
  }

  async function pollClientsFallback() {
    var now = Date.now();
    if (now - lastClientPoll < 2000) return;
    lastClientPoll = now;
    try {
      var res = await fetch(pf("/api/admin/stats"), { cache: "no-store" });
      if (!res.ok) return;
      var s = await res.json();
      if (typeof s.wall_clients === "number") {
        wallClients = s.wall_clients;
        paintClients();
      }
    } catch (e) {}
  }

  async function load() {
    var res = await fetch(pf("/api/admin/wall-manager"), { cache: "no-store" });
    if (!res.ok) return;
    var data = await res.json();
    assets = data.assets || [];
    playlist = coercePlaylist(data.playlist || []);
    ffmpeg = !!data.ffmpeg;
    selected = playlist.length ? 0 : -1;
    applyPlayheadMeta(data);
    if (typeof data.wall_clients !== "number") pollClientsFallback();
    var en = $("wm_enabled");
    if (en) en.checked = !!data.enabled;
    var pre = $("wm_prefetch");
    if (pre) pre.value = data.prefetch === "all" ? "all" : "next";
    var mu = $("wm_mute_all");
    if (mu) mu.checked = !!data.mute_all;
    var ff = $("wmFfmpegHint");
    if (ff) ff.textContent = ffmpeg
      ? "ffmpeg gefunden. Videos als H.264/AAC MP4 bis 720p, ohne Hochskalieren."
      : "ffmpeg fehlt. Videos bleiben Original.";
    renderList();
  }

  async function save() {
    var status = $("wmSaveStatus");
    try {
      var res = await fetch(pf("/api/admin/wall-manager"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: $("wm_enabled") ? $("wm_enabled").checked : false,
          prefetch: $("wm_prefetch") ? $("wm_prefetch").value : "next",
          mute_all: $("wm_mute_all") ? $("wm_mute_all").checked : false,
          playlist: serializePlaylist()
        })
      });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        if (status) status.textContent = typeof data.detail === "string" ? data.detail : "Speichern fehlgeschlagen.";
        return;
      }
      playlist = coercePlaylist(data.playlist || playlist);
      if (data.assets) assets = data.assets;
      applyPlayheadMeta(data);
      if (status) status.textContent = "Gespeichert. Offene Walls übernehmen den Ablauf.";
      renderList();
    } catch (e) {
      if (status) status.textContent = "Speichern fehlgeschlagen.";
    }
  }

  function bind() {
    if (!$("wmAdmin")) return;
    var add = $("wmAddBtn");
    var menu = $("wmAddMenu");
    if (add && menu) {
      add.addEventListener("click", function (e) {
        e.stopPropagation();
        menu.hidden = !menu.hidden;
      });
      menu.addEventListener("click", function (e) { e.stopPropagation(); });
      menu.querySelectorAll("[data-add]").forEach(function (b) {
        b.addEventListener("click", function () {
          var k = b.getAttribute("data-add");
          var fx = b.getAttribute("data-effect");
          if (k === "effect") addItem("effect", fx);
          else addItem(k);
        });
      });
    }
    document.addEventListener("click", function () { closeAddMenu(); });
    var sv = $("wmSaveBtn");
    if (sv) sv.addEventListener("click", save);
    var closePrev = $("wmPreviewClose");
    if (closePrev) closePrev.addEventListener("click", function () {
      var m = $("wmPreview");
      var f = $("wmPreviewFrame");
      if (f) f.innerHTML = "";
      if (m) m.hidden = true;
    });
    load();
    if (playTimer) clearInterval(playTimer);
    playTimer = setInterval(pollPlayhead, 400);
    if (clockTimer) clearInterval(clockTimer);
    clockTimer = setInterval(paintClocks, 250);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
