/*
 * Widget de chat embebible — un solo <script src="widget.js"></script> y
 * ya funciona en cualquier sitio: inyecta su propio CSS, no depende de
 * ningún build step ni de otro archivo. Habla con la misma API (/chat)
 * que usa el bot de Telegram del proyecto.
 *
 * Config opcional antes de incluir este script:
 *   window.RAG_WIDGET_CONFIG = { apiBaseUrl: "https://tu-api.example.com" };
 */
(function () {
  "use strict";

  var config = window.RAG_WIDGET_CONFIG || {};
  var API_BASE_URL = config.apiBaseUrl || "http://localhost:8000";

  function getSessionId() {
    var key = "rag_widget_session_id";
    try {
      var existing = window.localStorage.getItem(key);
      if (existing) return existing;
      var fresh = "web-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
      window.localStorage.setItem(key, fresh);
      return fresh;
    } catch (err) {
      // localStorage puede fallar (modo privado, storage bloqueado): usamos
      // un id que al menos dura mientras la pestaña esté abierta.
      return "web-" + Date.now().toString(36);
    }
  }

  var sessionId = getSessionId();

  var STYLES =
    ".rag-widget-bubble{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#2563eb;color:#fff;border:none;font-size:24px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.25);z-index:999999;}" +
    ".rag-widget-panel{position:fixed;bottom:88px;right:20px;width:320px;max-width:90vw;height:420px;max-height:70vh;background:#fff;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.25);display:flex;flex-direction:column;overflow:hidden;font-family:system-ui,-apple-system,Segoe UI,sans-serif;z-index:999999;}" +
    ".rag-widget-panel.rag-hidden{display:none;}" +
    ".rag-widget-header{background:#2563eb;color:#fff;padding:12px 16px;font-weight:600;font-size:14px;}" +
    ".rag-widget-messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;background:#f8fafc;}" +
    ".rag-widget-msg{max-width:85%;padding:8px 12px;border-radius:10px;font-size:14px;line-height:1.35;white-space:pre-wrap;}" +
    ".rag-widget-msg.user{align-self:flex-end;background:#2563eb;color:#fff;}" +
    ".rag-widget-msg.bot{align-self:flex-start;background:#e2e8f0;color:#0f172a;}" +
    ".rag-widget-msg.error{align-self:flex-start;background:#fee2e2;color:#991b1b;}" +
    ".rag-widget-sources{display:block;margin-top:4px;font-size:11px;opacity:.7;}" +
    ".rag-widget-inputrow{display:flex;border-top:1px solid #e2e8f0;}" +
    ".rag-widget-input{flex:1;border:none;padding:10px 12px;font-size:14px;outline:none;}" +
    ".rag-widget-send{border:none;background:#2563eb;color:#fff;padding:0 16px;cursor:pointer;font-size:14px;}" +
    ".rag-widget-send:disabled{opacity:.5;cursor:default;}";

  function injectStyles() {
    var style = document.createElement("style");
    style.textContent = STYLES;
    document.head.appendChild(style);
  }

  function createEl(tag, className, text) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function buildWidget() {
    var bubble = createEl("button", "rag-widget-bubble", "💬");
    bubble.setAttribute("aria-label", "Abrir chat de soporte");

    var panel = createEl("div", "rag-widget-panel rag-hidden");
    var header = createEl("div", "rag-widget-header", "Soporte NovaShop");
    var messages = createEl("div", "rag-widget-messages");
    var inputRow = createEl("div", "rag-widget-inputrow");
    var input = createEl("input", "rag-widget-input");
    input.type = "text";
    input.placeholder = "Escribe tu pregunta...";
    var sendBtn = createEl("button", "rag-widget-send", "Enviar");

    inputRow.appendChild(input);
    inputRow.appendChild(sendBtn);
    panel.appendChild(header);
    panel.appendChild(messages);
    panel.appendChild(inputRow);

    document.body.appendChild(bubble);
    document.body.appendChild(panel);

    function appendMessage(role, text, sources) {
      var msg = createEl("div", "rag-widget-msg " + role, text);
      if (sources && sources.length) {
        var sourcesEl = createEl("span", "rag-widget-sources", "📎 Fuente: " + sources.join(", "));
        msg.appendChild(sourcesEl);
      }
      messages.appendChild(msg);
      messages.scrollTop = messages.scrollHeight;
      return msg;
    }

    function setBusy(busy) {
      input.disabled = busy;
      sendBtn.disabled = busy;
    }

    function send() {
      var text = input.value.trim();
      if (!text) return;

      appendMessage("user", text);
      input.value = "";
      setBusy(true);
      var pending = appendMessage("bot", "Escribiendo...");

      fetch(API_BASE_URL + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
        .then(function (response) {
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          pending.remove();
          appendMessage("bot", data.answer, data.sources);
        })
        .catch(function () {
          pending.remove();
          appendMessage("error", "No pude conectarme con el asistente. Intenta de nuevo en un momento.");
        })
        .finally(function () {
          setBusy(false);
          input.focus();
        });
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") send();
    });

    bubble.addEventListener("click", function () {
      panel.classList.toggle("rag-hidden");
      if (!panel.classList.contains("rag-hidden") && !messages.childNodes.length) {
        input.focus();
        appendMessage(
          "bot",
          "¡Hola! Soy el asistente de soporte de NovaShop. Pregúntame sobre envíos, devoluciones, pagos o el estado de tu pedido."
        );
      }
    });
  }

  function init() {
    injectStyles();
    buildWidget();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
