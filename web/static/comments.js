(function (global) {
  "use strict";

  function commentUrl(file) {
    var base = String(file || "").split("?")[0];
    var stem = base.replace(/\.[^/.]+$/, "");
    return (global.pfUrl ? global.pfUrl("/media/" + encodeURIComponent(stem) + ".txt") : ("/media/" + encodeURIComponent(stem) + ".txt"));
  }

  function attachPhotoComment(host, file, config) {
    if (!host || !config || !config.comments_enabled) return;
    fetch(commentUrl(file))
      .then(function (r) { return r.ok ? r.text() : ""; })
      .then(function (comment) {
        if (!comment) return;
        var text = document.createElement("div");
        text.className = "photoComment";
        var max = parseInt(config.comment_max_length, 10) || 80;
        text.textContent = comment.substring(0, max);
        text.style.fontFamily = config.comment_font || "Pacifico";
        text.style.color = config.comment_color || "#e51515";
        text.style.fontSize = (config.comment_size || 22) + "px";
        if (config.comment_bold) text.style.fontWeight = "bold";
        if (config.comment_underline) text.style.textDecoration = "underline";
        host.appendChild(text);
      })
      .catch(function () {});
  }

  global.attachPhotoComment = attachPhotoComment;
  global.photoCommentUrl = commentUrl;
})(window);
