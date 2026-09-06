(function (global) {
  "use strict";

  var MAX_RATIO = 0.13333;

  function overflows(box, text) {
    return text.scrollHeight > box.clientHeight + 1 || text.scrollWidth > box.clientWidth + 1;
  }

  function fitBannerText(box, text) {
    if (!box || !text) return;
    var h = box.clientHeight || 0;
    if (h < 8) return;
    var minPx = Math.max(10, h * 0.04);
    var max = Math.max(minPx, h * MAX_RATIO);
    text.style.fontSize = max + "px";
    if (!(text.textContent || "").trim()) return;
    if (!overflows(box, text)) return;
    var lo = minPx;
    var hi = max;
    var best = minPx;
    for (var i = 0; i < 14; i++) {
      var mid = (lo + hi) / 2;
      text.style.fontSize = mid + "px";
      if (overflows(box, text)) hi = mid;
      else {
        best = mid;
        lo = mid;
      }
    }
    text.style.fontSize = best + "px";
  }

  global.fitBannerText = fitBannerText;
})(window);
