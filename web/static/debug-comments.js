(function (global) {
  "use strict";

  var WORDS = [
    "Zappelbirne", "Mondsocke", "Kicherlampe", "Wolkenkuchen", "Flitzkeks",
    "Nebeltoast", "Glitzerstein", "Quatschmond", "Hoppeltee", "Funkelsuppe",
    "Knisterboot", "Schlummerstern", "Wackelpanda", "Bummelfloh", "Zitronenklang",
    "Pfannenzauber", "Kirmeswolke", "Tautropfen", "Rumpelkiste", "Sonnensalat"
  ];
  var FACES = ["😀", "😂", "🥳", "😎", "🤩", "😍", "🤪", "😜", "🤗", "😇"];
  var ICONS = [
    "🎉", "❤️", "⭐", "🌈", "🚀", "🍀", "🔥", "🎈", "🌸", "✨", "🍕", "🐱",
    "🎵", "☀️", "💫", "🦄", "👍", "💖", "★", "♥", "♪", "✿", "☀", "☁", "⚡", "✓"
  ];

  function pick(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  function clipComment(text, maxLen) {
    var chars = Array.from(String(text || ""));
    var out = chars.slice(0, maxLen).join("");
    while (out.length > maxLen && chars.length) {
      chars.pop();
      out = chars.join("");
    }
    return out;
  }

  function generateRandomComment(maxLen) {
    var n = parseInt(maxLen, 10);
    if (!isFinite(n) || n < 1) n = 80;
    n = Math.min(500, n);
    var tokens = [];
    var i;
    var words = 1 + Math.floor(Math.random() * 6);
    for (i = 0; i < words; i++) tokens.push(pick(WORDS));
    var faces = 1 + Math.floor(Math.random() * 3);
    for (i = 0; i < faces; i++) tokens.push(pick(FACES));
    var icons = 1 + Math.floor(Math.random() * 3);
    for (i = 0; i < icons; i++) tokens.push(pick(ICONS));
    for (i = tokens.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = tokens[i];
      tokens[i] = tokens[j];
      tokens[j] = tmp;
    }
    var text = "";
    for (i = 0; i < tokens.length; i++) {
      var candidate = text ? (text + " " + tokens[i]) : tokens[i];
      var clipped = clipComment(candidate, n);
      if (clipped === candidate || (!text && clipped)) {
        text = clipped;
        if (clipped !== candidate) break;
      } else {
        break;
      }
    }
    if (!text) text = clipComment("★😀", n);
    return clipComment(text, n);
  }

  global.generateRandomComment = generateRandomComment;
  global.clipComment = clipComment;
})(window);
