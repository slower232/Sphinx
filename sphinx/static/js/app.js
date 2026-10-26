/* Sphinx – mejoras progresivas. Todo funciona sin JavaScript salvo el tutor y el lector en voz alta. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

  // Menú móvil
  var toggle = document.querySelector("[data-nav-toggle]"), nav = document.getElementById("nav");
  if (toggle && nav) toggle.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // Confirmación de acciones destructivas
  document.addEventListener("submit", function (e) {
    var msg = e.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // Evitar envíos duplicados (el servidor también es idempotente)
  document.querySelectorAll("form[data-once]").forEach(function (f) {
    f.addEventListener("submit", function () {
      f.querySelectorAll('button[type="submit"]').forEach(function (b) { b.disabled = true; });
    });
  });

  // Tarjetas de memoria
  document.querySelectorAll("[data-flashcards] .flashcard").forEach(function (card) {
    var back = card.querySelector(".back");
    back.hidden = true;
    card.setAttribute("aria-pressed", "false");
    card.addEventListener("click", function () {
      var show = back.hidden;
      back.hidden = !show;
      card.setAttribute("aria-pressed", show ? "true" : "false");
    });
  });

  // Mostrar solo los campos del tipo de bloque / pregunta elegido (administración)
  document.querySelectorAll("[data-type-select]").forEach(function (sel) {
    var scope = sel.closest("form");
    function apply() {
      scope.querySelectorAll("[data-types]").forEach(function (el) {
        var on = el.getAttribute("data-types").split(" ").indexOf(sel.value) !== -1;
        el.hidden = !on;
        el.querySelectorAll("input,textarea,select").forEach(function (i) { i.disabled = !on; });
      });
    }
    sel.addEventListener("change", apply);
    apply();
  });

  // Lectura en voz alta (API del navegador; depende de las voces instaladas)
  var speakBtn = document.querySelector("[data-speak]");
  if (speakBtn && "speechSynthesis" in window) {
    speakBtn.hidden = false;
    var speaking = false;
    speakBtn.addEventListener("click", function () {
      if (speaking) { window.speechSynthesis.cancel(); speaking = false; speakBtn.setAttribute("aria-pressed", "false"); return; }
      var target = document.querySelector(speakBtn.getAttribute("data-speak"));
      var u = new SpeechSynthesisUtterance(target.innerText);
      u.lang = document.documentElement.lang || "es";
      u.onend = function () { speaking = false; speakBtn.setAttribute("aria-pressed", "false"); };
      speaking = true; speakBtn.setAttribute("aria-pressed", "true");
      window.speechSynthesis.speak(u);
    });
  }

  // Tutor de IA (solo si el servidor lo habilitó)
  var form = document.getElementById("tutor-form");
  if (form) {
    var log = document.getElementById("tutor-log"), input = document.getElementById("tutor-msg"), history = [];
    function add(cls, text) {
      var d = document.createElement("div");
      d.className = "msg " + cls; d.textContent = text;   // textContent: nunca se interpreta HTML
      log.appendChild(d); log.scrollTop = log.scrollHeight;
    }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = input.value.trim();
      if (!text) return;
      var btn = form.querySelector("button"); btn.disabled = true; input.value = "";
      add("user", text);
      fetch(form.getAttribute("data-endpoint"), {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ message: text, lesson_id: parseInt(form.getAttribute("data-lesson-id"), 10), history: history })
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (data.ok) { add("bot", data.text); history.push({ role: "user", content: text }, { role: "assistant", content: data.text }); history = history.slice(-6); }
        else add("err", data.error || "Error");
      }).catch(function () { add("err", form.getAttribute("data-net-error")); })
        .then(function () { btn.disabled = false; input.focus(); });
    });
  }
})();
