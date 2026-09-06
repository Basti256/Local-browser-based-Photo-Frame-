(function () {
  "use strict";

  var editor = {
    wrap: null,
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
    if (!editor.content) return;
    var align = "center";
    if (window.COMMENT_FONTS && COMMENT_FONTS.align) {
      align = COMMENT_FONTS.align(($("upload_greeting_align") && $("upload_greeting_align").value) || "center");
    } else {
      align = (($("upload_greeting_align") && $("upload_greeting_align").value) || "center");
      if (align !== "left" && align !== "right") align = "center";
    }
    var font = ($("upload_greeting_font") && $("upload_greeting_font").value) || "Arial";
    var family = (window.COMMENT_FONTS && COMMENT_FONTS.stack) ? COMMENT_FONTS.stack(font) : font;
    var color = ($("upload_greeting_color") && $("upload_greeting_color").value) || "#222222";
    var size = Math.max(10, num("upload_greeting_size", 28));
    var bold = $("upload_greeting_bold") ? $("upload_greeting_bold").checked : true;
    var underline = $("upload_greeting_underline") ? $("upload_greeting_underline").checked : false;
    editor.content.style.fontFamily = family;
    editor.content.style.color = color;
    editor.content.style.fontSize = size + "px";
    editor.content.style.fontWeight = bold ? "bold" : "normal";
    editor.content.style.textDecoration = underline ? "underline" : "none";
    editor.content.style.textAlign = align;
    editor.content.classList.remove("is-left", "is-center", "is-right");
    editor.content.classList.add("is-" + align);
    if (editor.meta) {
      editor.meta.textContent = "Vorschau wie auf der Upload-Seite. Mehrere Zeilen und Überschriften möglich.";
    }
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
    var ta = $("upload_greeting");
    if (!ta || editor.wrap) return;
    var wrap = document.createElement("div");
    wrap.className = "greetingEditor";
    wrap.innerHTML =
      '<div class="greetingEditor-toolbar" role="toolbar" aria-label="Begrüßungs-Format">' +
        '<button type="button" data-cmd="bold" title="Fett">Fett</button>' +
        '<button type="button" data-cmd="italic" title="Kursiv">Kursiv</button>' +
        '<button type="button" data-cmd="underline" title="Unterstrichen">Unterstrichen</button>' +
        '<button type="button" data-block="h1">Überschrift</button>' +
        '<button type="button" data-block="h2">Untertitel</button>' +
        '<button type="button" data-block="p">Text</button>' +
      "</div>" +
      '<div class="greetingEditor-stage">' +
        '<div class="greetingEditor-content" contenteditable="true" spellcheck="true"></div>' +
      "</div>" +
      '<div class="greetingEditor-meta"></div>';
    ta.classList.add("greetingEditor-source");
    ta.setAttribute("tabindex", "-1");
    ta.parentNode.insertBefore(wrap, ta);
    editor.wrap = wrap;
    editor.content = wrap.querySelector(".greetingEditor-content");
    editor.meta = wrap.querySelector(".greetingEditor-meta");
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
      });
    });
    editor.content.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" || e.shiftKey) return;
      e.preventDefault();
      try { document.execCommand("insertParagraph", false, null); } catch (err) {}
      commit();
    });
    editor.content.addEventListener("input", commit);
    editor.content.addEventListener("keyup", updateToolbar);
    editor.content.addEventListener("mouseup", updateToolbar);
    editor.content.addEventListener("paste", function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData("text/plain") || "";
      document.execCommand("insertText", false, text);
      commit();
    });

    ["upload_greeting_align", "upload_greeting_font", "upload_greeting_color",
      "upload_greeting_size", "upload_greeting_bold", "upload_greeting_underline"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("input", applyChrome);
      el.addEventListener("change", applyChrome);
    });
    applyChrome();
  }

  window.greetingEditor = {
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
