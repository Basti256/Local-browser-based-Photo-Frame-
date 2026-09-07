(function (global) {
  "use strict";

  var ANGLES = [0, 90, 180, 270];
  var CLASSES = ["wall-rot-0", "wall-rot-90", "wall-rot-180", "wall-rot-270"];
  var rotation = 0;
  var applied = false;

  function clampRot(value) {
    var n = parseInt(value, 10);
    return ANGLES.indexOf(n) >= 0 ? n : 0;
  }

  function wallStageEl() {
    return document.getElementById("wallStage");
  }

  function stripLegacyControl() {
    var bar = document.getElementById("wallRotateBar");
    if (bar && bar.parentNode) bar.parentNode.removeChild(bar);
    try { global.localStorage.removeItem("pfWallRotate"); } catch (e) {}
  }

  function applyClass() {
    stripLegacyControl();
    var root = document.documentElement;
    CLASSES.forEach(function (c) { root.classList.remove(c); });
    root.classList.add("wall-rot-" + rotation);
  }

  function wallInnerWidth() {
    var el = wallStageEl();
    if (el && el.clientWidth) return el.clientWidth;
    return rotation === 90 || rotation === 270 ? global.innerHeight : global.innerWidth;
  }

  function wallInnerHeight() {
    var el = wallStageEl();
    if (el && el.clientHeight) return el.clientHeight;
    return rotation === 90 || rotation === 270 ? global.innerWidth : global.innerHeight;
  }

  function wallMount(node) {
    var stage = wallStageEl();
    (stage || document.body).appendChild(node);
  }

  function wallClientRect(el) {
    if (!el) return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    var stage = wallStageEl();
    var er = el.getBoundingClientRect();
    var lw = wallInnerWidth();
    var lh = wallInnerHeight();
    if (!stage || !rotation) {
      var sr = stage ? stage.getBoundingClientRect() : { left: 0, top: 0 };
      return {
        left: er.left - sr.left,
        top: er.top - sr.top,
        right: er.right - sr.left,
        bottom: er.bottom - sr.top,
        width: er.width,
        height: er.height
      };
    }
    var cx = global.innerWidth / 2;
    var cy = global.innerHeight / 2;
    var corners = [
      [er.left, er.top],
      [er.right, er.top],
      [er.right, er.bottom],
      [er.left, er.bottom]
    ];
    var xs = [];
    var ys = [];
    var i;
    for (i = 0; i < 4; i++) {
      var dx = corners[i][0] - cx;
      var dy = corners[i][1] - cy;
      var lx;
      var ly;
      if (rotation === 90) {
        lx = dy;
        ly = -dx;
      } else if (rotation === 180) {
        lx = -dx;
        ly = -dy;
      } else {
        lx = -dy;
        ly = dx;
      }
      xs.push(lx + lw / 2);
      ys.push(ly + lh / 2);
    }
    var left = Math.min.apply(null, xs);
    var right = Math.max.apply(null, xs);
    var top = Math.min.apply(null, ys);
    var bottom = Math.max.apply(null, ys);
    return {
      left: left,
      top: top,
      right: right,
      bottom: bottom,
      width: right - left,
      height: bottom - top
    };
  }

  var OVERRIDE_KEY = "pfDebugWallRotate";
  var lastRotateCfg = {};

  function readOverride() {
    try {
      var v = global.sessionStorage.getItem(OVERRIDE_KEY);
      if (v == null || v === "") return null;
      return clampRot(v);
    } catch (e) {
      return null;
    }
  }

  function writeOverride(value) {
    try {
      global.sessionStorage.setItem(OVERRIDE_KEY, String(clampRot(value)));
    } catch (e) {}
  }

  function clearOverride() {
    try { global.sessionStorage.removeItem(OVERRIDE_KEY); } catch (e) {}
  }

  function syncDebugWallRotate(cfg) {
    if (cfg) lastRotateCfg = cfg;
    var debugOn = !!(lastRotateCfg && lastRotateCfg.debug_overlay);
    var configRot = clampRot(lastRotateCfg && lastRotateCfg.wall_display_rotation);
    var bar = document.getElementById("debugWallRotate");
    if (!debugOn) {
      if (bar) bar.style.display = "none";
      return;
    }
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "debugWallRotate";
      var lab = document.createElement("label");
      lab.setAttribute("for", "debugWallRotateSel");
      lab.textContent = "Debug drehen";
      var sel = document.createElement("select");
      sel.id = "debugWallRotateSel";
      sel.setAttribute("aria-label", "Debug-Drehung, unabhängig von der Config");
      [
        [0, "Horizontal (0°)"],
        [90, "Porträt (90°)"],
        [180, "Horizontal gedreht (180°)"],
        [270, "Porträt gedreht (270°)"]
      ].forEach(function (opt) {
        var o = document.createElement("option");
        o.value = String(opt[0]);
        o.textContent = opt[1];
        sel.appendChild(o);
      });
      sel.addEventListener("change", function () {
        writeOverride(sel.value);
        applyWallDisplayRotation(lastRotateCfg);
      });
      var hint = document.createElement("span");
      hint.className = "debugWallRotateHint";
      bar.appendChild(lab);
      bar.appendChild(sel);
      bar.appendChild(hint);
      document.body.appendChild(bar);
    }
    var selEl = document.getElementById("debugWallRotateSel");
    var hintEl = bar.querySelector(".debugWallRotateHint");
    if (hintEl) hintEl.textContent = "Config " + configRot + "°";
    if (selEl && document.activeElement !== selEl) selEl.value = String(rotation);
    bar.style.display = "flex";
  }

  function applyWallDisplayRotation(cfg) {
    if (cfg) lastRotateCfg = cfg;
    var debugOn = !!(cfg && cfg.debug_overlay);
    var configRot = clampRot(cfg && cfg.wall_display_rotation);
    var next = configRot;
    if (debugOn) {
      var ov = readOverride();
      if (ov !== null) next = ov;
    } else {
      clearOverride();
    }
    if (applied && next !== rotation) {
      rotation = next;
      applyClass();
      global.location.reload();
      return;
    }
    rotation = next;
    applyClass();
    applied = true;
    syncDebugWallRotate(cfg);
  }

  rotation = 0;
  applyClass();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", stripLegacyControl);
  } else {
    stripLegacyControl();
  }

  global.wallInnerWidth = wallInnerWidth;
  global.wallInnerHeight = wallInnerHeight;
  global.wallClientRect = wallClientRect;
  global.wallMount = wallMount;
  global.wallDisplayRotation = function () { return rotation; };
  global.applyWallDisplayRotation = applyWallDisplayRotation;
  global.syncDebugWallRotate = syncDebugWallRotate;
})(window);
