(function () {
  "use strict";

  var selectedId = "current";

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(text, kind) {
    var el = $("pw_tpl_status");
    if (!el) return;
    el.textContent = text || "";
    el.classList.remove("is-err", "is-ok");
    if (kind) el.classList.add(kind);
  }

  function render(data) {
    var list = $("pw_tpl_list");
    if (!list) return;
    var current = data.current || {};
    var templates = data.templates || [];
    var html = "";
    html += cardHtml("current", "Aktuell", current.name || "Projekt", current.summary || "Gespeicherte Wand dieses Projekts", selectedId === "current");
    if (!templates.length) {
      html += '<p class="pw-faint" id="pw_tpl_empty">Keine serverweiten Vorlagen. Hier die aktuelle Wand speichern oder unter Einrichtung (/setup) eine Vorlage anlegen.</p>';
    } else {
      templates.forEach(function (t) {
        html += cardHtml(t.id, "Vorlage", t.name || t.id, t.summary || t.description || "", selectedId === t.id);
      });
    }
    list.innerHTML = html;
    list.querySelectorAll("[data-tpl]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectedId = btn.getAttribute("data-tpl") || "current";
        list.querySelectorAll(".pw-cfg").forEach(function (el) {
          el.classList.toggle("is-on", el.getAttribute("data-tpl") === selectedId);
        });
        var applyBtn = $("pw_tpl_apply");
        if (applyBtn) applyBtn.disabled = selectedId === "current";
      });
    });
    var applyBtn = $("pw_tpl_apply");
    if (applyBtn) applyBtn.disabled = selectedId === "current";
  }

  function cardHtml(id, kind, name, note, on) {
    return (
      '<button type="button" class="pw-cfg' + (on ? " is-on" : "") + '" data-tpl="' + escapeAttr(id) + '">' +
      '<span class="pw-cfg-k">' + escapeHtml(kind) + "</span>" +
      "<b>" + escapeHtml(name) + "</b>" +
      '<span class="pw-note">' + escapeHtml(note) + "</span>" +
      "</button>"
    );
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
  }

  async function loadTemplates() {
    var list = $("pw_tpl_list");
    if (!list) return;
    try {
      var res = await fetch("/api/admin/templates");
      if (res.status === 401) {
        location.href = typeof pfUrl === "function" ? pfUrl("/admin") : "/admin";
        return;
      }
      if (!res.ok) {
        list.innerHTML = "";
        setStatus("Vorlagen konnten nicht geladen werden.", "is-err");
        return;
      }
      var data = await res.json();
      render(data);
      if (!data.templates || !data.templates.length) {
        setStatus("");
      }
    } catch (e) {
      list.innerHTML = "";
      setStatus("Vorlagen konnten nicht geladen werden.", "is-err");
    }
  }

  async function applySelected() {
    if (!selectedId || selectedId === "current") {
      setStatus("Bitte eine Vorlage wählen.", "is-err");
      return;
    }
    if (!confirm("Vorlage anwenden? Nur Wand-Einstellungen ändern sich. Upload, Netzwerk, PIN und Medien bleiben.")) {
      return;
    }
    setStatus("Wende Vorlage an …");
    try {
      var res = await fetch("/api/admin/templates/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: selectedId }),
      });
      var data = {};
      try { data = await res.json(); } catch (e) {}
      if (res.status === 401) {
        location.href = typeof pfUrl === "function" ? pfUrl("/admin") : "/admin";
        return;
      }
      if (!res.ok) {
        setStatus(data.detail || "Vorlage anwenden fehlgeschlagen.", "is-err");
        return;
      }
      if (typeof load === "function") await load();
      await loadTemplates();
      if (data.view_changed) {
        alert("Vorlage angewendet. Ansicht geändert – Admin und Wall werden neu geladen.");
        location.reload();
        return;
      }
      setStatus("Vorlage angewendet. Upload und System unverändert.", "is-ok");
    } catch (e) {
      setStatus("Vorlage anwenden fehlgeschlagen.", "is-err");
    }
  }

  async function saveCurrent() {
    var nameEl = $("pw_tpl_name");
    var descEl = $("pw_tpl_desc");
    var name = nameEl ? nameEl.value.trim() : "";
    var description = descEl ? descEl.value.trim() : "";
    if (!name) {
      setStatus("Bitte einen Namen für die Vorlage eingeben.", "is-err");
      if (nameEl) nameEl.focus();
      return;
    }
    setStatus("Speichere Vorlage …");
    try {
      var res = await fetch("/api/admin/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, description: description }),
      });
      var data = {};
      try { data = await res.json(); } catch (e) {}
      if (res.status === 401) {
        location.href = typeof pfUrl === "function" ? pfUrl("/admin") : "/admin";
        return;
      }
      if (!res.ok) {
        var msg = data.detail || "Vorlage speichern fehlgeschlagen.";
        if (Array.isArray(msg)) msg = msg.map(function (p) { return p.msg || p; }).join(" ");
        setStatus(msg, "is-err");
        return;
      }
      if (nameEl) nameEl.value = "";
      if (descEl) descEl.value = "";
      if (data.template && data.template.id) selectedId = data.template.id;
      await loadTemplates();
      setStatus("Vorlage gespeichert (serverweit, wie unter /setup).", "is-ok");
    } catch (e) {
      setStatus("Vorlage speichern fehlgeschlagen.", "is-err");
    }
  }

  function init() {
    var applyBtn = $("pw_tpl_apply");
    var saveBtn = $("pw_tpl_save");
    if (applyBtn) applyBtn.addEventListener("click", applySelected);
    if (saveBtn) saveBtn.addEventListener("click", saveCurrent);
    loadTemplates();
  }

  window.pwReloadTemplates = loadTemplates;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
