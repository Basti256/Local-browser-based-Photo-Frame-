(function (global) {
  "use strict";

  var meta = document.querySelector('meta[name="pf-base"]');
  var base = (meta && meta.getAttribute("content")) || "";
  base = String(base).replace(/\/$/, "");
  global.PF_BASE = base;

  var PROJECT_PATH = /^\/(wall|upload|admin|api|media|derived|header|background|ws)(\/|$)/i;

  function pathOnly(url) {
    var p = String(url || "").split("?")[0].split("#")[0];
    return p;
  }

  function isProjectPath(path) {
    if (!path) return false;
    if (path === "/sw.js" || path.indexOf("/sw.js") === 0) return true;
    return PROJECT_PATH.test(path);
  }

  function pfUrl(path) {
    if (path == null || path === "") return base || "/";
    if (typeof path !== "string") return path;
    if (/^(https?:|wss?:|blob:|data:)/i.test(path)) return rewriteAbs(path);
    if (path.charAt(0) !== "/") return path;
    var p = pathOnly(path);
    if (!isProjectPath(p)) return path;
    return base + path;
  }

  function rewriteAbs(url) {
    try {
      var u = new URL(url, location.href);
      if (u.protocol === "blob:" || u.protocol === "data:") return url;
      if (u.host !== location.host) return url;
      if (!isProjectPath(u.pathname)) return url;
      u.pathname = base + u.pathname;
      return u.toString();
    } catch (e) {
      return url;
    }
  }

  global.pfUrl = pfUrl;

  var origFetch = global.fetch;
  if (origFetch) {
    global.fetch = function (input, init) {
      if (typeof input === "string") input = pfUrl(input);
      else if (typeof Request !== "undefined" && input instanceof Request) {
        var nu = pfUrl(input.url);
        if (nu !== input.url) input = new Request(nu, input);
      }
      return origFetch.call(this, input, init);
    };
  }

  var XO = global.XMLHttpRequest;
  if (XO && XO.prototype && XO.prototype.open) {
    var origOpen = XO.prototype.open;
    XO.prototype.open = function (method, url) {
      if (typeof url === "string") arguments[1] = pfUrl(url);
      return origOpen.apply(this, arguments);
    };
  }

  var WS = global.WebSocket;
  if (WS) {
    var Wrapped = function (url, protocols) {
      if (typeof url === "string") url = pfUrl(url);
      if (protocols !== undefined) return new WS(url, protocols);
      return new WS(url);
    };
    Wrapped.prototype = WS.prototype;
    Wrapped.CONNECTING = WS.CONNECTING;
    Wrapped.OPEN = WS.OPEN;
    Wrapped.CLOSING = WS.CLOSING;
    Wrapped.CLOSED = WS.CLOSED;
    global.WebSocket = Wrapped;
  }

  var origOpenWin = global.open;
  if (origOpenWin) {
    global.open = function (url) {
      if (typeof url === "string") arguments[0] = pfUrl(url);
      return origOpenWin.apply(this, arguments);
    };
  }

  if (navigator.serviceWorker && navigator.serviceWorker.register) {
    var origReg = navigator.serviceWorker.register.bind(navigator.serviceWorker);
    navigator.serviceWorker.register = function (scriptURL, options) {
      scriptURL = pfUrl(scriptURL);
      options = options ? Object.assign({}, options) : {};
      if (base) options.scope = base + "/";
      return origReg(scriptURL, options);
    };
  }

  function rewriteTree(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll("a[href], link[href], img[src], video[src], script[src], form[action]").forEach(function (el) {
      var attr = el.hasAttribute("href") ? "href" : (el.hasAttribute("src") ? "src" : "action");
      var v = el.getAttribute(attr);
      if (!v || v.charAt(0) !== "/" || v.charAt(1) === "/") return;
      var next = pfUrl(v);
      if (next !== v) el.setAttribute(attr, next);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { rewriteTree(document); });
  } else {
    rewriteTree(document);
  }
})(window);
