(function (global) {
  "use strict";

  function clamp(n, lo, hi, fallback) {
    n = Number(n);
    if (!isFinite(n)) n = fallback;
    return Math.max(lo, Math.min(hi, n));
  }

  function normRot(v) {
    var n = parseInt(v, 10);
    if (!isFinite(n)) n = 0;
    n = ((n % 360) + 360) % 360;
    return [0, 90, 180, 270].indexOf(n) >= 0 ? n : 0;
  }

  function posValue(v) {
    return v === "top" || v === "bottom" ? v : "center";
  }

  function readSettings(root) {
    if (!root) root = document;
    function val(id, fallback) {
      var el = root.getElementById ? root.getElementById(id) : document.getElementById(id);
      if (!el) return fallback;
      if (el.type === "checkbox") return el.checked;
      return el.value;
    }
    var modeEl = document.getElementById("background_mode");
    var colorEl = document.getElementById("background_color");
    var imageEl = document.getElementById("background_image");
    var mode = modeEl ? modeEl.value : "color";
    return {
      background_mode: mode,
      background_color: colorEl ? colorEl.value : "#000000",
      background_image: mode === "image" && imageEl ? imageEl.value : "",
      background_rotation: normRot(val("background_rotation", 0)),
      background_brightness: clamp(val("background_brightness", 100), 20, 180, 100),
      background_contrast: clamp(val("background_contrast", 100), 20, 180, 100),
      background_position: posValue(val("background_position", "center")),
      background_scale: clamp(val("background_scale", 100), 20, 300, 100),
      background_opacity: clamp(val("background_opacity", 100), 0, 100, 100),
    };
  }

  function layout(root, cfg, img) {
    var box = root.getBoundingClientRect();
    var W = box.width;
    var H = box.height;
    var nw = img.naturalWidth;
    var nh = img.naturalHeight;
    if (!nw || !nh || W < 2 || H < 2) return;
    var rot = normRot(cfg.background_rotation);
    var swapped = rot === 90 || rot === 270;
    var visW = swapped ? nh : nw;
    var visH = swapped ? nw : nh;
    var cover = Math.max(W / visW, H / visH);
    var s = cover * (clamp(cfg.background_scale, 20, 300, 100) / 100);
    var dw = visW * s;
    var dh = visH * s;
    img.style.width = nw * s + "px";
    img.style.height = nh * s + "px";
    var left = (W - dw) / 2;
    var top;
    var pos = posValue(cfg.background_position);
    if (pos === "top") top = 0;
    else if (pos === "bottom") top = H - dh;
    else top = (H - dh) / 2;
    img.style.left = left + dw / 2 + "px";
    img.style.top = top + dh / 2 + "px";
    img.style.transform = "translate(-50%,-50%) rotate(" + rot + "deg)";
    img.style.opacity = String(clamp(cfg.background_opacity, 0, 100, 100) / 100);
    img.style.filter =
      "brightness(" + clamp(cfg.background_brightness, 20, 180, 100) / 100 +
      ") contrast(" + clamp(cfg.background_contrast, 20, 180, 100) / 100 + ")";
  }

  function applyWallBackground(root, cfg) {
    if (!root) return;
    cfg = cfg || {};
    var color = cfg.background_color || "#000000";
    root.style.backgroundColor = color;
    var img = root.querySelector("img");
    if (!img) {
      img = document.createElement("img");
      img.alt = "";
      root.appendChild(img);
    }
    var useImage = (cfg.background_mode || "color") === "image" && cfg.background_image;
    if (!useImage) {
      img.style.display = "none";
      img.removeAttribute("src");
      return;
    }
    img.style.display = "block";
    var src = "/background/" + encodeURIComponent(cfg.background_image);
    function run() {
      layout(root, cfg, img);
    }
    img.onload = run;
    if (img.getAttribute("src") === src && img.complete && img.naturalWidth) run();
    else img.src = src;
    if (!root._bgRo && typeof ResizeObserver !== "undefined") {
      root._bgRo = new ResizeObserver(function () {
        if (img.naturalWidth) layout(root, root._bgCfg || cfg, img);
      });
      root._bgRo.observe(root);
    }
    root._bgCfg = cfg;
  }

  function setValText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function refreshPreview() {
    var prev = document.getElementById("background_image_preview");
    if (!prev || !global.applyWallBackground) return;
    applyWallBackground(prev, readSettings());
    var b = document.getElementById("background_brightness");
    var c = document.getElementById("background_contrast");
    var s = document.getElementById("background_scale");
    var o = document.getElementById("background_opacity");
    if (b) setValText("background_brightness_val", String(b.value));
    if (c) setValText("background_contrast_val", String(c.value));
    if (s) setValText("background_scale_val", String(s.value));
    if (o) setValText("background_opacity_val", String(o.value));
  }

  function fillForm(cfg) {
    cfg = cfg || {};
    function set(id, v) {
      var el = document.getElementById(id);
      if (el) el.value = v;
    }
    set("background_rotation", String(normRot(cfg.background_rotation)));
    set("background_brightness", String(clamp(cfg.background_brightness, 20, 180, 100)));
    set("background_contrast", String(clamp(cfg.background_contrast, 20, 180, 100)));
    set("background_position", posValue(cfg.background_position));
    set("background_scale", String(clamp(cfg.background_scale, 20, 300, 100)));
    set("background_opacity", String(clamp(cfg.background_opacity, 0, 100, 100)));
    refreshPreview();
  }

  function rotateBy(delta) {
    var el = document.getElementById("background_rotation");
    if (!el) return;
    el.value = String(normRot((parseInt(el.value, 10) || 0) + delta));
    refreshPreview();
  }

  function initAdmin() {
    var ids = [
      "background_mode", "background_color", "background_color_hex", "background_image",
      "background_brightness", "background_contrast", "background_position",
      "background_scale", "background_opacity",
    ];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("input", refreshPreview);
      el.addEventListener("change", refreshPreview);
    });
    var left = document.getElementById("background_rotate_left");
    var right = document.getElementById("background_rotate_right");
    if (left) left.addEventListener("click", function () { rotateBy(-90); });
    if (right) right.addEventListener("click", function () { rotateBy(90); });
  }

  global.applyWallBackground = applyWallBackground;
  global.backgroundSettingsFromForm = readSettings;
  global.fillBackgroundForm = fillForm;
  global.initBackgroundAdmin = initAdmin;
  global.refreshBackgroundPreview = refreshPreview;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdmin);
  } else {
    initAdmin();
  }
})(window);
