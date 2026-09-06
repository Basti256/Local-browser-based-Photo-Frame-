(function (global) {
  "use strict";

  function normRot(v) {
    var n = parseInt(v, 10);
    if (!isFinite(n)) n = 0;
    n = ((n % 360) + 360) % 360;
    return [0, 90, 180, 270].indexOf(n) >= 0 ? n : 0;
  }

  function applyToImg(img, rot) {
    if (!img) return;
    rot = normRot(rot);
    img.style.transform = rot ? "rotate(" + rot + "deg)" : "";
    img.style.transformOrigin = "center center";
    var wrap = img.parentElement;
    if (wrap && wrap.classList.contains("headerPreview")) {
      wrap.classList.toggle("is-rot-90", rot === 90 || rot === 270);
    }
  }

  function refreshPreview() {
    var sel = document.getElementById("upload_image");
    var prev = document.getElementById("upload_image_preview");
    var rotEl = document.getElementById("upload_image_rotation");
    if (!prev) return;
    var img = prev.querySelector("img");
    if (!img) {
      img = document.createElement("img");
      img.alt = "";
      prev.appendChild(img);
    }
    var name = sel ? (sel.value || "") : "";
    var rot = rotEl ? normRot(rotEl.value) : 0;
    if (!name) {
      img.removeAttribute("src");
      img.style.display = "none";
      prev.classList.add("is-empty");
      return;
    }
    prev.classList.remove("is-empty");
    img.style.display = "block";
    var src = name.indexOf("/") === 0 || /^https?:/i.test(name)
      ? name
      : "/header/" + encodeURIComponent(name);
    img.onload = function () { applyToImg(img, rot); };
    if (img.getAttribute("src") === src && img.complete) applyToImg(img, rot);
    else img.src = src;
    applyToImg(img, rot);
  }

  function rotateBy(delta) {
    var el = document.getElementById("upload_image_rotation");
    if (!el) return;
    el.value = String(normRot((parseInt(el.value, 10) || 0) + delta));
    refreshPreview();
  }

  async function loadList() {
    var sel = document.getElementById("upload_image");
    if (!sel) return;
    var cur = sel.value;
    sel.innerHTML = '<option value="">– kein Bild –</option>';
    try {
      var res = await fetch("/api/header/list");
      var files = await res.json();
      (files || []).forEach(function (f) {
        var opt = document.createElement("option");
        opt.value = f;
        opt.textContent = f;
        sel.appendChild(opt);
      });
      if (cur) sel.value = cur;
    } catch (e) {}
  }

  function fillForm(cfg) {
    cfg = cfg || {};
    var rot = document.getElementById("upload_image_rotation");
    if (rot) rot.value = String(normRot(cfg.upload_image_rotation));
    var sel = document.getElementById("upload_image");
    if (sel) {
      var name = cfg.upload_image || "";
      if (name && sel.value !== name) {
        var opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        sel.appendChild(opt);
      }
      sel.value = name;
    }
    refreshPreview();
  }

  function rotationFromForm() {
    var el = document.getElementById("upload_image_rotation");
    return el ? normRot(el.value) : 0;
  }

  function initAdmin() {
    var sel = document.getElementById("upload_image");
    var btn = document.getElementById("header_upload_btn");
    var input = document.getElementById("header_upload_input");
    var left = document.getElementById("header_rotate_left");
    var right = document.getElementById("header_rotate_right");
    if (sel) sel.addEventListener("change", refreshPreview);
    if (left) left.addEventListener("click", function () { rotateBy(-90); });
    if (right) right.addEventListener("click", function () { rotateBy(90); });
    if (btn && input) {
      btn.addEventListener("click", async function () {
        if (!input.files || !input.files[0]) {
          alert("Bitte zuerst ein Bild auswählen");
          return;
        }
        var fd = new FormData();
        fd.append("file", input.files[0]);
        try {
          var r = await fetch("/api/header/upload", { method: "POST", body: fd });
          var d = await r.json();
          if (d.ok) {
            await loadList();
            if (sel) sel.value = d.filename;
            refreshPreview();
            input.value = "";
          } else {
            alert(d.error || "Upload fehlgeschlagen");
          }
        } catch (e) {
          alert("Upload fehlgeschlagen");
        }
      });
    }
  }

  global.loadHeaderList = loadList;
  global.fillHeaderForm = fillForm;
  global.refreshHeaderPreview = refreshPreview;
  global.headerRotationFromForm = rotationFromForm;
  global.applyHeaderRotation = applyToImg;
  global.normHeaderRotation = normRot;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdmin);
  } else {
    initAdmin();
  }
})(window);
