(function () {
  "use strict";

  var TAB_KEY = "pf_admin_tab";
  var MEDIA_KEY = "pf_admin_media";

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function showTab(id) {
    $all(".tabPanel").forEach(function (p) {
      p.classList.toggle("is-on", p.getAttribute("data-tab") === id);
    });
    $all(".adminTabs [data-tab]").forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-tab") === id);
    });
    try { sessionStorage.setItem(TAB_KEY, id); } catch (e) {}
  }

  function showMedia(kind) {
    $all(".mediaPane").forEach(function (p) {
      p.classList.toggle("is-on", p.getAttribute("data-media") === kind);
    });
    $all(".mediaToggle [data-media]").forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-media") === kind);
    });
    try { sessionStorage.setItem(MEDIA_KEY, kind); } catch (e) {}
  }

  window.toggleSection = function (header) {
    var panel = header.closest(".tabPanel") || document;
    var content = header.nextElementSibling;
    var open = content.style.display === "block";
    $all(".sectionContent", panel).forEach(function (el) {
      el.style.display = "none";
    });
    $all(".sectionHeader span:last-child", panel).forEach(function (el) {
      if (el.classList.contains("help")) return;
      el.textContent = "▼";
    });
    if (!open) {
      content.style.display = "block";
      var arrow = header.querySelector("span:last-child");
      if (arrow && !arrow.classList.contains("help")) arrow.textContent = "▲";
    }
  };

  function init() {
    var tabs = $all(".adminTabs [data-tab]");
    if (!tabs.length) return;
    tabs.forEach(function (b) {
      b.addEventListener("click", function () { showTab(b.getAttribute("data-tab")); });
    });
    $all(".mediaToggle [data-media]").forEach(function (b) {
      b.addEventListener("click", function () { showMedia(b.getAttribute("data-media")); });
    });
    var tab = "wall";
    var media = "image";
    try {
      tab = sessionStorage.getItem(TAB_KEY) || tab;
      media = sessionStorage.getItem(MEDIA_KEY) || media;
    } catch (e) {}
    if (!$('.tabPanel[data-tab="' + tab + '"]')) tab = "wall";
    if (media !== "video") media = "image";
    showTab(tab);
    showMedia(media);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
