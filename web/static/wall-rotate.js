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

  function applyClass() {
    var root = document.documentElement;
    CLASSES.forEach(function (c) { root.classList.remove(c); });
    root.classList.add("wall-rot-" + rotation);
  }

  function wallInnerWidth() {
    var el = document.getElementById("wallStage");
    if (el && el.clientWidth) return el.clientWidth;
    return rotation === 90 || rotation === 270 ? global.innerHeight : global.innerWidth;
  }

  function wallInnerHeight() {
    var el = document.getElementById("wallStage");
    if (el && el.clientHeight) return el.clientHeight;
    return rotation === 90 || rotation === 270 ? global.innerWidth : global.innerHeight;
  }

  function wallClientRect(el) {
    if (!el) return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    var er = el.getBoundingClientRect();
    var lw = wallInnerWidth();
    var lh = wallInnerHeight();
    if (!rotation) {
      var stage = document.getElementById("wallStage");
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
    var rad = -rotation * Math.PI / 180;
    var cos = Math.cos(rad);
    var sin = Math.sin(rad);
    var corners = [
      [er.left, er.top],
      [er.right, er.top],
      [er.right, er.bottom],
      [er.left, er.bottom]
    ];
    var xs = [];
    var ys = [];
    for (var i = 0; i < 4; i++) {
      var dx = corners[i][0] - cx;
      var dy = corners[i][1] - cy;
      xs.push(dx * cos - dy * sin + lw / 2);
      ys.push(dx * sin + dy * cos + lh / 2);
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

  function applyWallDisplayRotation(cfg) {
    var next = clampRot(cfg && cfg.wall_display_rotation);
    if (applied && next !== rotation) {
      rotation = next;
      applyClass();
      global.location.reload();
      return;
    }
    rotation = next;
    applyClass();
    applied = true;
  }

  rotation = 0;
  applyClass();

  global.wallInnerWidth = wallInnerWidth;
  global.wallInnerHeight = wallInnerHeight;
  global.wallClientRect = wallClientRect;
  global.wallDisplayRotation = function () { return rotation; };
  global.applyWallDisplayRotation = applyWallDisplayRotation;
})(window);
