(function () {
  "use strict";

  var SW = 1.25;
  var ICONS = {
    lage:
      '<rect x="1.5" y="1.5" width="6" height="6" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="8.5" y="1.5" width="6" height="6" fill="var(--wash)" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="1.5" y="8.5" width="6" height="6" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="8.5" y="8.5" width="6" height="6" stroke="currentColor" stroke-width="' + SW + '"/>',
    ablauf:
      '<path d="M1.5 4.2 L1.5 11.8 L7 8 Z" fill="currentColor"/>' +
      '<rect x="8.2" y="2.5" width="6.3" height="2.2" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="8.2" y="6.9" width="6.3" height="2.2" fill="currentColor"/>' +
      '<rect x="8.2" y="11.3" width="6.3" height="2.2" stroke="currentColor" stroke-width="' + SW + '"/>',
    photowall:
      '<rect x="1.5" y="3.2" width="7" height="5.4" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="5" y="7" width="8" height="6.2" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="8.2" y="1.8" width="6.2" height="5" fill="var(--wash)" stroke="currentColor" stroke-width="' + SW + '"/>',
    upload:
      '<path d="M8 11.2 V3.2 M5 6 L8 3.2 L11 6" stroke="currentColor" stroke-width="' + SW + '" stroke-linecap="square"/>' +
      '<path d="M2.2 10.2 V13.2 H13.8 V10.2" stroke="currentColor" stroke-width="' + SW + '" stroke-linecap="square"/>',
    betrieb:
      '<circle cx="8" cy="8" r="3.1" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="7.15" y="1.2" width="1.7" height="2.6" fill="currentColor"/>' +
      '<rect x="7.15" y="12.2" width="1.7" height="2.6" fill="currentColor"/>' +
      '<rect x="1.2" y="7.15" width="2.6" height="1.7" fill="currentColor"/>' +
      '<rect x="12.2" y="7.15" width="2.6" height="1.7" fill="currentColor"/>',
    debug:
      '<path d="M8 1.6 L14.4 8 L8 14.4 L1.6 8 Z" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<circle cx="8" cy="8" r="1.4" fill="currentColor"/>',
    start: '<path d="M4.2 3.1 L4.2 12.9 L13.2 8 Z" fill="currentColor"/>',
    pause:
      '<rect x="3.6" y="3.1" width="2.8" height="9.8" fill="currentColor"/>' +
      '<rect x="9.6" y="3.1" width="2.8" height="9.8" fill="currentColor"/>',
    fade:
      '<rect x="1.8" y="3.2" width="8" height="8" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="6.2" y="4.8" width="8" height="8" fill="var(--wash)" stroke="currentColor" stroke-width="' + SW + '"/>',
    qr:
      '<rect x="1.4" y="1.4" width="5.2" height="5.2" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="2.8" y="2.8" width="2.4" height="2.4" fill="currentColor"/>' +
      '<rect x="9.4" y="1.4" width="5.2" height="5.2" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="10.8" y="2.8" width="2.4" height="2.4" fill="currentColor"/>' +
      '<rect x="1.4" y="9.4" width="5.2" height="5.2" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="2.8" y="10.8" width="2.4" height="2.4" fill="currentColor"/>' +
      '<rect x="10" y="10" width="2" height="2" fill="currentColor"/>' +
      '<rect x="13" y="13" width="1.6" height="1.6" fill="currentColor"/>',
    banner:
      '<rect x="1.4" y="4" width="13.2" height="8" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<path d="M3.2 7 H12.8 M3.2 10 H9.6" stroke="currentColor" stroke-width="' + SW + '"/>',
    bildtext:
      '<rect x="3" y="1.8" width="10" height="8" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<path d="M3 13.2 H13" stroke="currentColor" stroke-width="' + SW + '"/>',
    medien:
      '<rect x="1.6" y="1.6" width="5.4" height="5.4" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="9" y="1.6" width="5.4" height="5.4" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="1.6" y="9" width="5.4" height="5.4" stroke="currentColor" stroke-width="' + SW + '"/>' +
      '<rect x="9" y="9" width="5.4" height="5.4" fill="var(--wash)" stroke="currentColor" stroke-width="' + SW + '"/>',
  };

  var PLAYLIST = [
    { file: "—", duration: "5 s", tone: "—" },
    { file: "Begrüßung.mp4", duration: "1:20", tone: "an" },
    { file: "Photowall", duration: "12 min", tone: "—" },
    { file: "Danke.jpg", duration: "8 s", tone: "—" },
  ];

  var WALL_CFGS = {
    current: {
      view: "Fly",
      rot: "0°",
      bgMode: "Bild",
      bgColor: "#000000",
      bgFile: "shared:sommer.jpg",
      bgPos: "mittig",
      bgScale: "100 %",
      bgBright: "100 %",
      bgContrast: "100 %",
      bgOpacity: "100 %",
      bgRot: "0°",
      gridCols: "4",
      gridDur: "8 s",
      gridGapC: "20 px",
      gridGapR: "0 px",
      gridFrames: "an",
      spawn: "Bahnen",
      lanes: "6",
      laneOrder: "niemals nebeneinander",
      burst: "1 s",
      imgInterval: "6 s",
      vidInterval: "10 s",
      imgMaxN: "10",
      vidMaxN: "2",
      imgMin: "100 px",
      vidMin: "100 px",
      imgMax: "150 px",
      vidMax: "150 px",
      vidMode: "einmal",
      imgFlight: "Random Drift",
      vidFlight: "Random Drift",
      imgDrift: "0,2",
      vidDrift: "0,2",
      imgRot: "90°",
      vidRot: "90°",
      imgRotDir: "beide",
      vidRotDir: "beide",
      imgDur: "30 s",
      vidDur: "30 s",
      imgVar: "an",
      vidVar: "an",
      imgVarN: "0,4",
      vidVarN: "0,4",
      imgHl: "an",
      vidHl: "an",
      imgHlDur: "10 s",
      vidHlDur: "10 s",
      imgHlCol: "#ffff00",
      vidHlCol: "#ffff00",
      imgHlMax: "3",
      vidHlMax: "3",
      centerOn: "aus",
      centerMode: "Fly Through",
      centerPct: "30 %",
      centerDur: "5 s",
      centerMax: "1",
      centerVar: "30 px",
      centerSpeed: "1 s / 1 s",
      padTop: "12 px",
      padSide: "12 px",
      padBot: "50 px",
      cacheOn: "aus",
      cacheTtl: "30 min",
      cacheMax: "100 / 20",
      cacheMb: "500 MB",
      qrOn: "an",
      qrText: "Schick uns dein Bild!",
      qrPos: "unten mittig",
      qrSize: "220 px",
      qrTextSize: "24",
      qrColor: "#db0a0a",
      qrDyn: "an",
      qrTime: "5 s / 5 s",
      bannerOn: "aus",
      bannerText: "—",
      bannerPos: "unten",
      bannerH: "120",
      bannerLook: "#000 / #fff",
      bannerAlign: "mitte",
      bannerFont: "Arial",
      bannerTime: "10 s / 10 s",
      commentOn: "an",
      commentCol: "#e51515",
      commentFont: "Pacifico",
      commentSize: "22 px",
      commentBold: "aus",
      commentUl: "aus",
    },
    hochzeit: {
      view: "Fly",
      rot: "0°",
      bgMode: "Farbe",
      bgColor: "#1a1210",
      bgFile: "—",
      spawn: "Bahnen",
      lanes: "5",
      laneOrder: "zufällig",
      imgHlCol: "#ffff00",
      vidHlCol: "#ffff00",
      qrOn: "an",
      qrText: "Fotos teilen",
      bannerOn: "an",
      bannerText: "Wir heiraten",
      bannerPos: "oben",
      bannerFont: "Pacifico",
      commentOn: "an",
      commentFont: "Pacifico",
    },
    grid: {
      view: "Grid",
      rot: "90°",
      bgMode: "Farbe",
      bgColor: "#111111",
      bgFile: "—",
      gridCols: "4",
      gridDur: "6 s",
      gridGapC: "12 px",
      gridGapR: "8 px",
      spawn: "Zufall",
      imgMax: "120 px",
      vidMax: "120 px",
      qrOn: "an",
      qrPos: "unten rechts",
      bannerOn: "aus",
      commentOn: "aus",
    },
    sommer: {
      view: "Fly",
      rot: "0°",
      bgMode: "Bild",
      bgFile: "shared:wiese.jpg",
      bgBright: "110 %",
      bgContrast: "90 %",
      spawn: "Burst",
      burst: "1,4 s",
      imgInterval: "5 s",
      vidInterval: "8 s",
      qrOn: "an",
      bannerOn: "an",
      bannerText: "Sommerfest",
      bannerPos: "unten",
    },
  };

  var VIEWS = ["lage", "ablauf", "photowall", "upload", "betrieb", "debug"];
  var toastTimer = 0;

  function paintIcons(root) {
    (root || document).querySelectorAll("[data-icon]").forEach(function (el) {
      if (el.querySelector("svg")) return;
      var name = el.getAttribute("data-icon");
      var size = Number(el.getAttribute("data-size") || 16);
      var markup = ICONS[name];
      if (!markup) return;
      el.innerHTML =
        '<svg class="pic" width="' +
        size +
        '" height="' +
        size +
        '" viewBox="0 0 16 16" fill="none" aria-hidden="true">' +
        markup +
        "</svg>";
    });
  }

  function showToast(msg) {
    var el = document.getElementById("toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      el.classList.remove("is-on");
    }, 2200);
  }

  function showView(id) {
    if (VIEWS.indexOf(id) < 0) id = "lage";
    document.querySelectorAll("[data-panel]").forEach(function (panel) {
      panel.classList.toggle("is-on", panel.getAttribute("data-panel") === id);
    });
    document.querySelectorAll("[data-nav]").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-nav") === id);
    });
    if (location.hash !== "#" + id) {
      history.replaceState(null, "", "#" + id);
    }
  }

  function setChipGroup(group, value) {
    document.querySelectorAll('[data-chip-group="' + group + '"]').forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-chip") === value);
    });
  }

  function applyWallFields(values) {
    Object.keys(values).forEach(function (key) {
      document.querySelectorAll('[data-wf="' + key + '"]').forEach(function (el) {
        el.textContent = values[key];
      });
    });
    if (values.view) setChipGroup("view", values.view);
    if (values.rot) setChipGroup("rot", values.rot);
    if (values.spawn) setChipGroup("spawn", values.spawn);
  }

  function applyWallCfg(id) {
    var base = WALL_CFGS.current || {};
    var extra = WALL_CFGS[id] || {};
    var merged = {};
    Object.keys(base).forEach(function (key) {
      merged[key] = base[key];
    });
    Object.keys(extra).forEach(function (key) {
      merged[key] = extra[key];
    });
    applyWallFields(merged);
    document.querySelectorAll("[data-cfg]").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-cfg") === id);
    });
  }

  function setPlaylist(index) {
    document.querySelectorAll("[data-pl]").forEach(function (row) {
      var on = Number(row.getAttribute("data-pl")) === index;
      row.classList.toggle("is-sel", on);
    });
    var item = PLAYLIST[index];
    var box = document.getElementById("plDetail");
    if (!item || !box) return;
    var fields = box.querySelectorAll(".field b");
    if (fields[0]) fields[0].textContent = item.file;
    if (fields[1]) fields[1].textContent = item.duration;
    if (fields[2]) fields[2].textContent = item.tone;
  }

  paintIcons(document);

  document.addEventListener("click", function (ev) {
    var go = ev.target.closest("[data-go]");
    if (go) {
      showView(go.getAttribute("data-go"));
      return;
    }
    var nav = ev.target.closest("[data-nav]");
    if (nav) {
      showView(nav.getAttribute("data-nav"));
      return;
    }
    var dummy = ev.target.closest("[data-dummy]");
    if (dummy) {
      ev.preventDefault();
      showToast(dummy.getAttribute("data-dummy") || "Attrappe — speichert nicht");
      return;
    }
    var pl = ev.target.closest("[data-pl]");
    if (pl) {
      setPlaylist(Number(pl.getAttribute("data-pl")));
      return;
    }
    var cfg = ev.target.closest("[data-cfg]");
    if (cfg) {
      applyWallCfg(cfg.getAttribute("data-cfg"));
      return;
    }
    var chip = ev.target.closest("[data-chip]");
    if (chip) {
      var group = chip.getAttribute("data-chip-group");
      var value = chip.getAttribute("data-chip") || chip.textContent.trim();
      setChipGroup(group, value);
      var field = chip.getAttribute("data-wf-set");
      if (field) {
        var patch = {};
        patch[field] = value;
        applyWallFields(patch);
      }
    }
  });

  document.querySelectorAll(".dummy-in").forEach(function (input) {
    input.addEventListener("input", function () {
      showToast("Feld nur zur Ansicht — speichert nicht");
    });
  });

  var fromHash = (location.hash || "").replace(/^#/, "");
  showView(fromHash || "lage");
})();
