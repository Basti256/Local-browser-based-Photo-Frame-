(function (global) {
  "use strict";

  var FRAME_SIZE_REF = 150;

  function commentUrl(file) {
    var base = String(file || "").split("?")[0];
    var stem = base.replace(/\.[^/.]+$/, "");
    return (global.pfUrl ? global.pfUrl("/media/" + encodeURIComponent(stem) + ".txt") : ("/media/" + encodeURIComponent(stem) + ".txt"));
  }

  function padVal(value, fallback) {
    var n = parseInt(value, 10);
    return isFinite(n) ? n : fallback;
  }

  function photoFrameScale(sizePx) {
    var n = parseFloat(sizePx);
    if (!isFinite(n) || n <= FRAME_SIZE_REF) return 1;
    return Math.min(2.5, 1 + 0.5 * (n - FRAME_SIZE_REF) / FRAME_SIZE_REF);
  }

  function applyPhotoFramePadding(el, sizePx, config) {
    if (!el || !config) return 1;
    var s = photoFrameScale(sizePx);
    el.dataset.frameScale = String(s);
    var t = padVal(config.frame_padding_top, 12) * s;
    var side = padVal(config.frame_padding_side, 12) * s;
    var b = padVal(config.frame_padding_bottom, 50) * s;
    var font = padVal(config.comment_size, 22) * s;
    if (config.comments_enabled !== false && b > 0) {
      var minBottom = font * 1.2 * 2 + 16;
      if (b < minBottom) b = minBottom;
    }
    el.style.padding = Math.round(t) + "px " + Math.round(side) + "px " + Math.round(b) + "px " + Math.round(side) + "px";
    return s;
  }

  function stylePhotoComment(text, host, config) {
    if (!text || !config) return;
    var scale = parseFloat(host && host.dataset.frameScale);
    if (!isFinite(scale) || scale < 1) scale = 1;
    text.style.fontFamily = config.comment_font || "Pacifico";
    text.style.color = config.comment_color || "#e51515";
    text.style.fontSize = ((padVal(config.comment_size, 22)) * scale) + "px";
    var inset = Math.round(8 * scale);
    text.style.bottom = inset + "px";
    text.style.left = inset + "px";
    text.style.right = inset + "px";
    text.style.fontWeight = config.comment_bold ? "bold" : "";
    text.style.textDecoration = config.comment_underline ? "underline" : "";
  }

  var commentCache = {};
  var commentPending = {};

  function commentCacheKey(file) {
    return String(file || "").split("?")[0];
  }

  function fetchPhotoComment(file) {
    var key = commentCacheKey(file);
    if (!key) return Promise.resolve("");
    if (Object.prototype.hasOwnProperty.call(commentCache, key)) {
      return Promise.resolve(commentCache[key]);
    }
    if (commentPending[key]) return commentPending[key];
    commentPending[key] = fetch(commentUrl(key))
      .then(function (r) { return r.ok ? r.text() : ""; })
      .then(function (comment) {
        commentCache[key] = comment || "";
        delete commentPending[key];
        return commentCache[key];
      })
      .catch(function () {
        delete commentPending[key];
        return "";
      });
    return commentPending[key];
  }

  function applyPhotoCommentText(host, comment, config) {
    if (!host || !comment || host.querySelector(".photoComment")) return;
    var text = document.createElement("div");
    text.className = "photoComment";
    var max = parseInt(config && config.comment_max_length, 10) || 80;
    text.textContent = comment.substring(0, max);
    stylePhotoComment(text, host, config);
    host.appendChild(text);
  }

  function attachPhotoComment(host, file, config) {
    if (!host || !config || !config.comments_enabled) return;
    var key = commentCacheKey(file);
    if (Object.prototype.hasOwnProperty.call(commentCache, key)) {
      applyPhotoCommentText(host, commentCache[key], config);
      return;
    }
    fetchPhotoComment(file).then(function (comment) {
      applyPhotoCommentText(host, comment, config);
    });
  }

  function prefetchPhotoComments(files) {
    (files || []).forEach(function (f) {
      var ext = String(f || "").split(".").pop().toLowerCase();
      if (ext === "txt") return;
      fetchPhotoComment(f);
    });
  }

  global.attachPhotoComment = attachPhotoComment;
  global.prefetchPhotoComments = prefetchPhotoComments;
  global.fetchPhotoComment = fetchPhotoComment;
  global.photoCommentUrl = commentUrl;
  global.photoFrameScale = photoFrameScale;
  global.applyPhotoFramePadding = applyPhotoFramePadding;
  global.stylePhotoComment = stylePhotoComment;
})(window);
