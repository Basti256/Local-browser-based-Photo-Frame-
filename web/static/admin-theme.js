(function (global) {
  "use strict";

  var KEY = "pf-admin-theme";
  var MODES = ["light", "dark", "system"];
  var SW = 1.25;
  var ICONS = {
    light:
      '<circle cx="8" cy="8" r="2.4" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<path d="M8 1.6 V3.2 M8 12.8 V14.4 M1.6 8 H3.2 M12.8 8 H14.4 M3.3 3.3 L4.4 4.4 M11.6 11.6 L12.7 12.7 M3.3 12.7 L4.4 11.6 M11.6 4.4 L12.7 3.3" stroke="currentColor" stroke-width="' + SW + '" stroke-linecap="square"/>',
    dark:
      '<path d="M10.2 2.2 A5.8 5.8 0 1 0 13.8 10.4 A4.6 4.6 0 0 1 10.2 2.2 Z" fill="none" stroke="currentColor" stroke-width="' + SW + '"/>',
    system:
      '<rect x="2" y="2.4" width="12" height="8.2" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<path d="M6.2 13.4 H9.8 M8 10.6 V13.4" stroke="currentColor" stroke-width="' + SW + '" stroke-linecap="square"/>',
  };
  var LABELS = { light: "Hell", dark: "Dunkel", system: "System" };

  function read() {
    try {
      var v = localStorage.getItem(KEY);
      if (MODES.indexOf(v) >= 0) return v;
    } catch (e) {}
    return "system";
  }

  function apply(mode) {
    if (MODES.indexOf(mode) < 0) mode = "system";
    document.documentElement.setAttribute("data-theme", mode);
    try {
      localStorage.setItem(KEY, mode);
    } catch (e) {}
    sync();
    return mode;
  }

  function svg(name) {
    return (
      '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" aria-hidden="true">' +
      (ICONS[name] || "") +
      "</svg>"
    );
  }

  function sync() {
    var mode = read();
    document.querySelectorAll("[data-pf-theme]").forEach(function (root) {
      if (!root.getAttribute("data-ready")) {
        root.setAttribute("data-ready", "1");
        root.setAttribute("role", "group");
        root.setAttribute("aria-label", "Darstellung");
        root.classList.add("pf-theme");
        root.innerHTML = MODES.map(function (id) {
          return (
            '<button type="button" data-theme-set="' +
            id +
            '" title="' +
            LABELS[id] +
            '" aria-label="' +
            LABELS[id] +
            '">' +
            svg(id) +
            "</button>"
          );
        }).join("");
      }
      root.querySelectorAll("[data-theme-set]").forEach(function (btn) {
        var on = btn.getAttribute("data-theme-set") === mode;
        btn.classList.toggle("is-on", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
  }

  function onClick(ev) {
    var btn = ev.target.closest("[data-theme-set]");
    if (!btn) return;
    ev.preventDefault();
    apply(btn.getAttribute("data-theme-set"));
  }

  apply(read());
  document.addEventListener("click", onClick);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", sync);
  } else {
    sync();
  }

  global.pfTheme = { read: read, apply: apply, key: KEY };
})(window);
