(function () {
  "use strict";

  var PREVIEW_SCALE = 0.25;

  var editor = {
    wrap: null,
    viewport: null,
    stage: null,
    bar: null,
    content: null,
    meta: null,
    textarea: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function mdToHtml(md) {
    return (window.simpleMd && simpleMd.mdToHtml) ? simpleMd.mdToHtml(md) : "";
  }

  function htmlToMd(root) {
    return (window.simpleMd && simpleMd.htmlToMd) ? simpleMd.htmlToMd(root) : "";
  }

  function num(id, fallback) {
    var el = $(id);
    var n = el ? parseFloat(el.value) : NaN;
    return isNaN(n) ? fallback : n;
  }

  function applyChrome() {
    if (!editor.bar) return;
    var enabled = $("banner_enabled") && $("banner_enabled").checked;
    var pos = ($("banner_position") && $("banner_position").value) || "bottom";
    var height = Math.max(40, num("banner_height", 120));
    var bg = ($("banner_color") && $("banner_color").value) || "#000000";
    var fg = ($("banner_text_color") && $("banner_text_color").value) || "#ffffff";
    var show = num("banner_show_duration", 10);
    var hide = num("banner_hide_duration", 10);
    editor.stage.classList.toggle("is-bottom", pos !== "top");
    editor.stage.classList.toggle("is-top", pos === "top");
    editor.stage.classList.toggle("is-off", !enabled);
    editor.bar.style.height = height + "px";
    editor.bar.style.setProperty("--banner-h", height + "px");
    editor.bar.style.background = bg;
    editor.bar.style.color = fg;
    editor.content.style.color = fg;
    var align = "center";
    if (window.COMMENT_FONTS && COMMENT_FONTS.align) {
      align = COMMENT_FONTS.align(($("banner_align") && $("banner_align").value) || "center");
    } else {
      align = (($("banner_align") && $("banner_align").value) || "center");
      if (align !== "left" && align !== "right") align = "center";
    }
    var font = ($("banner_font") && $("banner_font").value) || "Arial";
    editor.bar.style.justifyContent = align === "left" ? "flex-start" : align === "right" ? "flex-end" : "center";
    editor.content.classList.remove("is-left", "is-center", "is-right");
    editor.content.classList.add("is-" + align);
    var family = (window.COMMENT_FONTS && COMMENT_FONTS.stack) ? COMMENT_FONTS.stack(font) : font;
    editor.bar.style.fontFamily = family;
    editor.content.style.fontFamily = family;
    var place = pos === "top" ? "oben" : "unten";
    editor.meta.textContent = enabled
      ? "Vorschau 1/4 der Wall-Größe (" + place + ", " + height + " px auf der Wand). Einblenden " + show + " s, Pause " + hide + " s."
      : "Banner ist ausgeschaltet — so sähe er aus, wenn er aktiv ist (Vorschau 1/4).";
    scheduleFit();
  }

  function syncViewport() {
    if (!editor.viewport || !editor.stage) return;
    var innerH = editor.stage.offsetHeight || 0;
    editor.viewport.style.height = Math.max(12, Math.round(innerH * PREVIEW_SCALE)) + "px";
  }

  var fitRaf = 0;
  function scheduleFit() {
    if (fitRaf) cancelAnimationFrame(fitRaf);
    fitRaf = requestAnimationFrame(function () {
      fitRaf = 0;
      if (window.fitBannerText && editor.bar && editor.content) {
        fitBannerText(editor.bar, editor.content);
      }
      syncViewport();
    });
  }

  function commit() {
    if (!editor.textarea || !editor.content) return;
    editor.textarea.value = htmlToMd(editor.content);
  }

  function refreshFromTextarea() {
    if (!editor.content || !editor.textarea) return;
    editor.content.innerHTML = mdToHtml(editor.textarea.value);
    applyChrome();
  }

  function exec(cmd, value) {
    editor.content.focus();
    try {
      document.execCommand(cmd, false, value || null);
    } catch (e) {}
    commit();
    updateToolbar();
    scheduleFit();
  }

  function updateToolbar() {
    if (!editor.wrap) return;
    editor.wrap.querySelectorAll("[data-cmd]").forEach(function (btn) {
      var on = false;
      try { on = document.queryCommandState(btn.getAttribute("data-cmd")); } catch (e) {}
      btn.classList.toggle("is-on", !!on);
    });
  }

  function build() {
    var ta = $("banner_text");
    if (!ta || editor.wrap) return;
    var wrap = document.createElement("div");
    wrap.className = "bannerEditor";
    wrap.innerHTML =
      '<div class="bannerEditor-toolbar" role="toolbar" aria-label="Banner-Format">' +
        '<button type="button" data-cmd="bold" title="Fett">Fett</button>' +
        '<button type="button" data-cmd="italic" title="Kursiv">Kursiv</button>' +
        '<button type="button" data-cmd="underline" title="Unterstrichen">Unterstrichen</button>' +
        '<button type="button" data-block="h1">Überschrift</button>' +
        '<button type="button" data-block="h2">Untertitel</button>' +
        '<button type="button" data-block="p">Text</button>' +
      "</div>" +
      '<div class="bannerEditor-viewport">' +
        '<div class="bannerEditor-stage is-bottom">' +
          '<div class="bannerEditor-bar">' +
            '<div class="bannerEditor-content" contenteditable="true" spellcheck="true"></div>' +
          "</div>" +
          '<div class="bannerEditor-fill" aria-hidden="true"></div>' +
        "</div>" +
      "</div>" +
      '<div class="bannerEditor-meta"></div>';
    ta.classList.add("bannerEditor-source");
    ta.setAttribute("tabindex", "-1");
    ta.parentNode.insertBefore(wrap, ta);
    editor.wrap = wrap;
    editor.viewport = wrap.querySelector(".bannerEditor-viewport");
    editor.stage = wrap.querySelector(".bannerEditor-stage");
    editor.bar = wrap.querySelector(".bannerEditor-bar");
    editor.content = wrap.querySelector(".bannerEditor-content");
    editor.meta = wrap.querySelector(".bannerEditor-meta");
    editor.textarea = ta;
    editor.content.innerHTML = mdToHtml(ta.value);
    try { document.execCommand("defaultParagraphSeparator", false, "p"); } catch (e) {}

    wrap.querySelectorAll("[data-cmd]").forEach(function (btn) {
      btn.addEventListener("mousedown", function (e) { e.preventDefault(); });
      btn.addEventListener("click", function () { exec(btn.getAttribute("data-cmd")); });
    });
    wrap.querySelectorAll("[data-block]").forEach(function (btn) {
      btn.addEventListener("mousedown", function (e) { e.preventDefault(); });
      btn.addEventListener("click", function () {
        var block = btn.getAttribute("data-block");
        editor.content.focus();
        var ok = false;
        try { ok = document.execCommand("formatBlock", false, block); } catch (e) {}
        if (!ok) {
          try { document.execCommand("formatBlock", false, "<" + block + ">"); } catch (e2) {}
        }
        commit();
        scheduleFit();
      });
    });
    editor.content.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" || e.shiftKey) return;
      e.preventDefault();
      try { document.execCommand("insertParagraph", false, null); } catch (err) {}
      commit();
      scheduleFit();
    });
    editor.content.addEventListener("input", function () {
      commit();
      scheduleFit();
    });
    editor.content.addEventListener("keyup", updateToolbar);
    editor.content.addEventListener("mouseup", updateToolbar);
    editor.content.addEventListener("paste", function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData("text/plain") || "";
      document.execCommand("insertText", false, text);
      commit();
      scheduleFit();
    });

    ["banner_enabled", "banner_position", "banner_height", "banner_color",
      "banner_text_color", "banner_show_duration", "banner_hide_duration",
      "banner_align", "banner_font"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("input", applyChrome);
      el.addEventListener("change", applyChrome);
    });
    applyChrome();
    window.addEventListener("resize", scheduleFit);
  }

  window.bannerEditor = {
    init: build,
    refresh: refreshFromTextarea,
    commit: commit,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
