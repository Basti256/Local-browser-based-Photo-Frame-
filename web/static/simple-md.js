(function (global) {
  "use strict";

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function inlineMd(s) {
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, label, href) {
      href = href.trim();
      if (!/^(https?:|mailto:|#)/i.test(href)) return label;
      return '<a href="' + href.replace(/"/g, "") + '">' + label + "</a>";
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    s = s.replace(/\+\+(.+?)\+\+/g, "<u>$1</u>");
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    s = s.replace(/(^|[\s(])_([^_]+)_/g, "$1<em>$2</em>");
    s = s.replace(/\n/g, "<br>");
    return s;
  }

  function headingHtml(level, first, rest) {
    var tag = "h" + level;
    var html = "<" + tag + ">" + inlineMd(first) + "</" + tag + ">";
    if (rest) html += "<p>" + inlineMd(rest) + "</p>";
    return html;
  }

  function mdToHtml(md) {
    var s = escapeHtml(md || "").replace(/\r\n/g, "\n").trim();
    if (!s) return "";
    s = s.replace(/\+\+(#{1,3}\s+)/g, "$1++");
    return s.split(/\n{2,}/).map(function (block) {
      var lines = block.split("\n");
      var first = lines[0];
      var rest = lines.slice(1).join("\n");
      var hm;
      if ((hm = first.match(/^###\s+(.*)$/))) return headingHtml(3, hm[1], rest);
      if ((hm = first.match(/^##\s+(.*)$/))) return headingHtml(2, hm[1], rest);
      if ((hm = first.match(/^#\s+(.*)$/))) return headingHtml(1, hm[1], rest);
      if (lines.every(function (l) { return /^[-*]\s+/.test(l); })) {
        return "<ul>" + lines.map(function (l) {
          return "<li>" + inlineMd(l.replace(/^[-*]\s+/, "")) + "</li>";
        }).join("") + "</ul>";
      }
      return "<p>" + inlineMd(block) + "</p>";
    }).join("");
  }

  function safeHref(h) {
    h = (h || "").trim();
    return /^(https?:|mailto:|#)/i.test(h) ? h : "";
  }

  function headingMd(mark, inner) {
    var lines = String(inner || "").replace(/\r\n/g, "\n").split("\n");
    var title = "";
    var rest = [];
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].replace(/^\s+|\s+$/g, "");
      if (!line) continue;
      if (!title) title = line;
      else rest.push(line);
    }
    var out = title ? mark + " " + title + "\n\n" : "";
    if (rest.length) out += rest.join("\n\n") + "\n\n";
    return out;
  }

  function underlineMd(inner) {
    return String(inner || "").split(/(\n{2,})/).map(function (part) {
      if (/^\n+$/.test(part)) return part;
      return part.split("\n").map(function (line) {
        var trimmed = line.replace(/^\s+|\s+$/g, "");
        if (!trimmed) return line;
        var hm = trimmed.match(/^(#{1,3}\s+)(.*)$/);
        if (hm) return hm[1] + "++" + hm[2] + "++";
        if (trimmed.indexOf("++") === 0 && trimmed.slice(-2) === "++") return line;
        return line.replace(trimmed, "++" + trimmed + "++");
      }).join("\n");
    }).join("");
  }

  function htmlToMd(root) {
    function walk(node) {
      if (!node) return "";
      if (node.nodeType === 3) return node.nodeValue || "";
      if (node.nodeType !== 1) return "";
      var tag = node.tagName.toLowerCase();
      var inner = Array.prototype.map.call(node.childNodes, walk).join("");
      if (tag === "strong" || tag === "b") return "**" + inner + "**";
      if (tag === "em" || tag === "i") return "*" + inner + "*";
      if (tag === "u" || tag === "ins") return underlineMd(inner);
      if (tag === "span") {
        var style = (node.getAttribute("style") || "") + " " + ((node.style && node.style.textDecoration) || "");
        if (/underline/i.test(style)) return underlineMd(inner);
      }
      if (tag === "h1") return headingMd("#", inner);
      if (tag === "h2") return headingMd("##", inner);
      if (tag === "h3") return headingMd("###", inner);
      if (tag === "br") return "\n";
      if (tag === "li") return "- " + inner.trim() + "\n";
      if (tag === "ul" || tag === "ol") return "\n" + inner + "\n";
      if (tag === "a") {
        var href = safeHref(node.getAttribute("href"));
        return href ? "[" + inner + "](" + href + ")" : inner;
      }
      if (tag === "p" || tag === "div") {
        var t = inner.replace(/\n+$/, "");
        return t ? t + "\n\n" : "";
      }
      return inner;
    }
    return walk(root).replace(/\n{3,}/g, "\n\n").trim();
  }

  global.simpleMd = {
    mdToHtml: mdToHtml,
    htmlToMd: htmlToMd,
  };
})(window);
