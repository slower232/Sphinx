/* Sphinx – modo juego: una pregunta por pantalla con retroalimentación inmediata.
   La CALIFICACIÓN es del servidor (POST /api/intentos/<id>/responder); aquí solo se muestra el resultado.
   Sin JavaScript, el formulario completo sigue funcionando. */
(function () {
  "use strict";
  var game = document.querySelector("[data-game]");
  if (!game) return;
  var d = game.dataset;
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  var form = document.getElementById("game-form");
  var sections = [].slice.call(form.querySelectorAll("section.question"));
  var progress = game.querySelector(".game-progress");
  var bar = game.querySelector("[data-bar]"), checkBtn = bar.querySelector(".game-check");
  var fb = game.querySelector("[data-feedback]"), fbImg = fb.querySelector("img"), fbTitle = fb.querySelector(".fb-title"),
      fbBody = fb.querySelector(".fb-body"), fbNext = fb.querySelector(".fb-next");
  var idx = 0, combo = 0;
  game.classList.add("playing");

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  function fire(node) { node.dispatchEvent(new Event("change", { bubbles: true })); }
  function locked(sec) { return sec.classList.contains("locked"); }

  /* ---------- Relacionar: arrastrar y soltar (o tocar ficha y luego el espacio) ---------- */
  function enhanceMatch(sec) {
    var rows = [].slice.call(sec.querySelectorAll(".match-row"));
    var selects = rows.map(function (r) { return r.querySelector("select"); });
    var values = [].slice.call(selects[0].options).filter(function (o) { return o.value !== ""; }).map(function (o) { return o.value; });
    var wrap = el("div", "dnd"), slots = el("div", "dnd-slots"), bank = el("div", "dnd-bank");
    bank.setAttribute("aria-label", d.tBank);
    var selected = null, dragging = null;
    function sync() { slots.querySelectorAll(".dnd-slot").forEach(function (s, i) { var c = s.querySelector(".chip"); selects[i].value = c ? c.dataset.value : ""; }); fire(selects[0]); }
    function release(chip) { chip.setAttribute("aria-pressed", "false"); bank.appendChild(chip); sync(); }
    function place(chip, slot) {
      var old = slot.querySelector(".chip"); if (old && old !== chip) bank.appendChild(old);
      chip.setAttribute("aria-pressed", "false"); slot.appendChild(chip); selected = null; sync();
    }
    rows.forEach(function (row, i) {
      var left = row.querySelector("span").textContent, r = el("div", "dnd-row"), slot = el("div", "dnd-slot");
      slot.tabIndex = 0; slot.setAttribute("role", "button"); slot.setAttribute("aria-label", left + ": " + d.tEmpty);
      slot.addEventListener("click", function (e) { if (locked(sec) || e.target.classList.contains("chip")) return; if (selected) place(selected, slot); });
      slot.addEventListener("keydown", function (e) { if ((e.key === "Enter" || e.key === " ") && e.target === slot && selected) { e.preventDefault(); place(selected, slot); } });
      slot.addEventListener("dragover", function (e) { e.preventDefault(); });
      slot.addEventListener("drop", function (e) { e.preventDefault(); if (dragging && !locked(sec)) place(dragging, slot); });
      r.appendChild(el("span", "dnd-left", left)); r.appendChild(slot); slots.appendChild(r);
    });
    values.forEach(function (v) {
      var chip = el("button", "chip", v); chip.type = "button"; chip.draggable = true; chip.dataset.value = v; chip.setAttribute("aria-pressed", "false");
      chip.addEventListener("click", function () {
        if (locked(sec)) return;
        if (chip.parentNode !== bank) { release(chip); return; }
        if (selected && selected !== chip) selected.setAttribute("aria-pressed", "false");
        selected = selected === chip ? null : chip; chip.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      chip.addEventListener("dragstart", function (e) { dragging = chip; e.dataTransfer.setData("text/plain", v); });
      bank.appendChild(chip);
    });
    bank.addEventListener("dragover", function (e) { e.preventDefault(); });
    bank.addEventListener("drop", function (e) { e.preventDefault(); if (dragging && !locked(sec)) release(dragging); });
    rows.forEach(function (r) { r.hidden = true; });
    wrap.appendChild(slots); wrap.appendChild(bank);
    rows[0].parentNode.insertBefore(wrap, rows[0]);
  }

  /* ---------- Ordenar: banco de fichas -> línea de respuesta ---------- */
  function enhanceOrder(sec) {
    var rows = [].slice.call(sec.querySelectorAll(".match-row"));
    var selects = rows.map(function (r) { return r.querySelector("select"); });
    var values = [].slice.call(selects[0].options).filter(function (o) { return o.value !== ""; }).map(function (o) { return o.value; });
    var wrap = el("div", "order-wrap"), answer = el("div", "order-answer"), bank = el("div", "order-bank"), dragging = null;
    answer.dataset.empty = d.tOrderEmpty; answer.setAttribute("role", "list");
    function sync() { var chips = answer.querySelectorAll(".chip"); selects.forEach(function (s, i) { s.value = chips[i] ? chips[i].dataset.value : ""; }); fire(selects[0]); }
    values.forEach(function (v) {
      var chip = el("button", "chip", v); chip.type = "button"; chip.draggable = true; chip.dataset.value = v;
      chip.addEventListener("click", function () {
        if (locked(sec)) return;
        if (chip.parentNode === bank) answer.appendChild(chip); else bank.appendChild(chip);
        sync();
      });
      chip.addEventListener("dragstart", function (e) { dragging = chip; e.dataTransfer.setData("text/plain", v); });
      chip.addEventListener("dragover", function (e) { e.preventDefault(); });
      chip.addEventListener("drop", function (e) {
        e.preventDefault(); e.stopPropagation();
        if (!dragging || dragging === chip || locked(sec)) return;
        if (chip.parentNode === answer) answer.insertBefore(dragging, chip); else bank.appendChild(dragging);
        sync();
      });
      bank.appendChild(chip);
    });
    answer.addEventListener("dragover", function (e) { e.preventDefault(); });
    answer.addEventListener("drop", function (e) { e.preventDefault(); if (dragging && !locked(sec)) { answer.appendChild(dragging); sync(); } });
    bank.addEventListener("dragover", function (e) { e.preventDefault(); });
    bank.addEventListener("drop", function (e) { e.preventDefault(); if (dragging && !locked(sec)) { bank.appendChild(dragging); sync(); } });
    rows.forEach(function (r) { r.hidden = true; });
    wrap.appendChild(answer); wrap.appendChild(bank);
    rows[0].parentNode.insertBefore(wrap, rows[0]);
  }

  /* ---------- Lectura de la respuesta de cada tipo ---------- */
  function getResponse(sec) {
    var kind = sec.dataset.kind;
    if (kind === "mcq" || kind === "tf") { var c = sec.querySelector("input[type=radio]:checked"); return c ? c.value : null; }
    if (kind === "numeric" || kind === "short") { var v = sec.querySelector("input[type=text]").value.trim(); return v ? v : null; }
    var vals = [].slice.call(sec.querySelectorAll("select")).map(function (s) { return s.value; });
    return vals.every(function (x) { return x !== ""; }) ? vals : null;
  }

  function answeredCount() { return sections.filter(function (s) { return s.dataset.answered; }).length; }
  function show(i) {
    idx = i;
    sections.forEach(function (s, j) { s.hidden = j !== i; });
    progress.value = answeredCount();
    fb.hidden = true; bar.hidden = false; checkBtn.disabled = getResponse(sections[i]) === null;
    var first = sections[i].querySelector("input,button.chip,select:not([hidden])");
    window.scrollTo(0, 0);
    if (first && first.type !== "radio") try { first.focus({ preventScroll: true }); } catch (e) { /* sin foco */ }
  }
  function lockSection(sec) { sec.classList.add("locked"); sec.querySelectorAll("input,select").forEach(function (n) { n.disabled = true; }); }

  function markOptions(sec, res) {
    var chosen = sec.querySelector("input[type=radio]:checked");
    sec.querySelectorAll("label.choice, label.img-option").forEach(function (lab) {
      var txt = lab.querySelector("span:last-child").textContent.trim();
      if (!res.correct && txt === res.correct_text) lab.classList.add("res-ok");
      if (chosen && lab === chosen.closest("label")) lab.classList.add(res.correct ? "res-ok" : "res-bad");
    });
  }
  function showFeedback(sec, res) {
    sec.dataset.answered = "1"; lockSection(sec); markOptions(sec, res);
    var praise = d.tPraise.split("|");
    combo = res.correct ? combo + 1 : 0;
    fb.className = "feedback " + (res.correct ? "ok" : "bad");
    fbImg.src = res.correct ? (combo >= 3 ? d.imgCheer : d.imgHappy) : d.imgOops;
    fbTitle.textContent = res.correct ? praise[Math.floor(Math.random() * praise.length)] + (combo >= 3 ? " 🔥 " + d.tCombo.replace("{n}", combo) : "") : d.tWrong;
    fbBody.textContent = res.correct ? (res.explanation || "") : d.tAnswer + ": " + res.correct_text + (res.explanation ? ". " + res.explanation : "");
    fbNext.textContent = idx + 1 >= sections.length ? d.tFinish : d.tNext;
    progress.value = answeredCount();
    bar.hidden = true; fb.hidden = false; fbNext.focus();
  }

  checkBtn.addEventListener("click", function () {
    var sec = sections[idx], r = getResponse(sec);
    if (r === null) return;
    checkBtn.disabled = true;
    fetch(d.checkUrl, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ question_id: parseInt(sec.dataset.qid, 10), response: r }) })
      .then(function (res) { return res.json().then(function (j) { return { ok: res.ok, j: j }; }); })
      .then(function (x) { if (!x.ok || !x.j.ok) throw new Error("check"); showFeedback(sec, x.j); })
      .catch(function () { window.alert(d.tNet); checkBtn.disabled = false; });
  });
  fbNext.addEventListener("click", function () {
    if (idx + 1 >= sections.length) { fbNext.disabled = true; form.submit(); } else show(idx + 1);
  });
  form.addEventListener("input", function () { if (!bar.hidden) checkBtn.disabled = getResponse(sections[idx]) === null; });
  form.addEventListener("change", function () { if (!bar.hidden) checkBtn.disabled = getResponse(sections[idx]) === null; });

  sections.forEach(function (s) {
    if (s.dataset.kind === "match") enhanceMatch(s);
    if (s.dataset.kind === "order") enhanceOrder(s);
    if (s.dataset.answered) lockSection(s);
  });
  var start = sections.findIndex(function (s) { return !s.dataset.answered; });
  if (start === -1) { form.submit(); } else show(start);   // si ya respondió todo (recarga), termina el intento
})();
