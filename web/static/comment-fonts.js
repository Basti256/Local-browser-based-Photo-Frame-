(function (global) {
  "use strict";

  var FONTS = [
    {name: "Pacifico", fallback: "cursive"},
    {name: "Caveat", fallback: "cursive"},
    {name: "Dancing Script", fallback: "cursive"},
    {name: "Great Vibes", fallback: "cursive"},
    {name: "Satisfy", fallback: "cursive"},
    {name: "Sacramento", fallback: "cursive"},
    {name: "Parisienne", fallback: "cursive"},
    {name: "Allura", fallback: "cursive"},
    {name: "Amatic SC", fallback: "cursive"},
    {name: "Indie Flower", fallback: "cursive"},
    {name: "Permanent Marker", fallback: "cursive"},
    {name: "Shadows Into Light", fallback: "cursive"},
    {name: "Lobster", fallback: "cursive"},
    {name: "Playfair Display", fallback: "serif"},
    {name: "Cinzel", fallback: "serif"},
    {name: "Merriweather", fallback: "serif"},
    {name: "Roboto", fallback: "sans-serif"},
    {name: "Open Sans", fallback: "sans-serif"},
    {name: "Lato", fallback: "sans-serif"},
    {name: "Montserrat", fallback: "sans-serif"},
    {name: "Oswald", fallback: "sans-serif"},
    {name: "Raleway", fallback: "sans-serif"},
    {name: "Nunito", fallback: "sans-serif"},
    {name: "Quicksand", fallback: "sans-serif"},
    {name: "Josefin Sans", fallback: "sans-serif"},
    {name: "Comfortaa", fallback: "cursive"},
    {name: "Arial", fallback: "sans-serif", local: true},
    {name: "Georgia", fallback: "serif", local: true},
    {name: "Times New Roman", fallback: "serif", local: true},
    {name: "Comic Sans MS", fallback: "cursive", local: true},
  ];

  function googleHref() {
    var q = FONTS.filter(function (f) { return !f.local; }).map(function (f) {
      return "family=" + encodeURIComponent(f.name).replace(/%20/g, "+");
    }).join("&");
    return "https://fonts.googleapis.com/css2?" + q + "&display=swap";
  }

  function ensureLink() {
    if (document.getElementById("commentFontsLink")) return;
    var link = document.createElement("link");
    link.id = "commentFontsLink";
    link.rel = "stylesheet";
    link.href = googleHref();
    document.head.appendChild(link);
  }

  function stack(name) {
    var found = FONTS.filter(function (f) { return f.name === name; })[0];
    return (name || "Arial") + ", " + (found ? found.fallback : "cursive");
  }

  function isLocal(name) {
    var found = FONTS.filter(function (f) { return f.name === name; })[0];
    return !!(found && found.local);
  }

  function loadOne(name, linkId) {
    linkId = linkId || "displayFontLink";
    var el = document.getElementById(linkId);
    if (!name || isLocal(name)) {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement("link");
      el.id = linkId;
      el.rel = "stylesheet";
      document.head.appendChild(el);
    }
    el.href = "https://fonts.googleapis.com/css2?family=" +
      encodeURIComponent(name).replace(/%20/g, "+") + "&display=swap";
  }

  function normalizeAlign(value) {
    var v = String(value || "center").toLowerCase();
    return v === "left" || v === "right" ? v : "center";
  }

  function idsFrom(options) {
    options = options || {};
    return {
      font: options.font || "comment_font",
      sample: options.sample || "comment_font_sample",
      color: options.color || "comment_color",
      size: options.size || "comment_size",
      bold: options.bold || "comment_bold",
      underline: options.underline || "comment_underline",
    };
  }

  function paintSample(ids) {
    ids = idsFrom(ids);
    var sample = document.getElementById(ids.sample);
    var sel = document.getElementById(ids.font);
    if (!sel) return;
    var font = sel.value || "Pacifico";
    sel.style.fontFamily = stack(font);
    if (!sample) return;
    var colorEl = document.getElementById(ids.color);
    var sizeEl = document.getElementById(ids.size);
    var bold = document.getElementById(ids.bold);
    var under = document.getElementById(ids.underline);
    sample.style.fontFamily = stack(font);
    sample.style.color = colorEl && colorEl.value ? colorEl.value : "#333333";
    sample.style.fontSize = ((sizeEl && sizeEl.value) || 22) + "px";
    sample.style.fontWeight = bold && bold.checked ? "bold" : "normal";
    sample.style.textDecoration = under && under.checked ? "underline" : "none";
    sample.textContent = font;
  }

  function fillSelect(current, ids) {
    ensureLink();
    ids = idsFrom(ids);
    var sel = document.getElementById(ids.font);
    if (!sel) return;
    var names = FONTS.map(function (f) { return f.name; });
    if (current && names.indexOf(current) < 0) {
      FONTS.push({name: current, fallback: "cursive"});
    }
    sel.innerHTML = "";
    FONTS.forEach(function (f) {
      var opt = document.createElement("option");
      opt.value = f.name;
      opt.textContent = f.name;
      opt.style.fontFamily = f.name + ", " + f.fallback;
      sel.appendChild(opt);
    });
    sel.value = current && (names.indexOf(current) >= 0 || current) ? current : "Pacifico";
    if (!sel.value) sel.selectedIndex = 0;
    paintSample(ids);
  }

  function mount(current, options) {
    var ids = idsFrom(options);
    fillSelect(current, ids);
    [ids.font, ids.color, ids.size, ids.bold, ids.underline].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el || el._commentFontBound) return;
      el._commentFontBound = true;
      el.addEventListener("input", function () { paintSample(ids); });
      el.addEventListener("change", function () { paintSample(ids); });
    });
  }

  global.COMMENT_FONTS = {
    mount: mount,
    paintSample: paintSample,
    stack: stack,
    loadOne: loadOne,
    ensureLink: ensureLink,
    align: normalizeAlign,
  };
})(window);
