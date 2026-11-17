// Prueba de humo en navegador real (opcional). Requiere: npm i puppeteer  y la app corriendo (python run.py).
// Uso: SPHINX_URL=http://127.0.0.1:5000 node tests/e2e/game_smoke.js   (CHROME_PATH opcional)
const puppeteer = require("puppeteer");
const BASE = process.env.SPHINX_URL || "http://127.0.0.1:5000";
const log = (...a) => console.log(...a);
(async () => {
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || undefined, headless: "new", args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 420, height: 860, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("console", m => { if (m.type() === "error") errors.push("console: " + m.text()); });
  page.on("dialog", d => { errors.push("dialog: " + d.message()); d.dismiss(); });

  await page.goto(BASE + "/", { waitUntil: "networkidle0" });
  await page.screenshot({ path: "./home.png" });
  await page.goto(BASE + "/cursos/fracciones-desde-cero/lecciones/1", { waitUntil: "networkidle0" });
  await page.screenshot({ path: "./lesson.png", fullPage: false });
  await Promise.all([page.waitForNavigation(), page.click("form[action*='/evaluaciones/'] button")]);
  await page.waitForSelector(".game.playing");
  log("juego cargado:", page.url());

  let n = 0, shots = 0;
  for (let guard = 0; guard < 12; guard++) {
    const info = await page.evaluate(() => { const s = [...document.querySelectorAll("section.question")].find(x => !x.hidden); return s ? { kind: s.dataset.kind, qid: s.dataset.qid } : null; });
    if (!info) break;
    log("pregunta", ++n, info.kind);
    const sel = `section.question[data-qid='${info.qid}']`;
    if (info.kind === "mcq" || info.kind === "tf") {
      await page.click(`${sel} label:nth-of-type(2) input`);
    } else if (info.kind === "match") {
      // tocar ficha y luego espacio (como en un celular)
      const k = await page.$$eval(`${sel} .dnd-slot`, s => s.length);
      for (let i = 0; i < k; i++) {
        const chips = await page.$$(`${sel} .dnd-bank .chip`);
        await chips[0].click();
        const slots = await page.$$(`${sel} .dnd-slot`);
        await slots[i].click();
      }
    } else if (info.kind === "order") {
      const k = await page.$$eval(`${sel} .order-bank .chip`, s => s.length);
      for (let i = 0; i < k; i++) { const chips = await page.$$(`${sel} .order-bank .chip`); await chips[0].click(); }
    } else {
      await page.type(`${sel} input[type=text]`, "1");
    }
    if (shots < 4 && ["match", "order", "mcq"].includes(info.kind)) { await page.screenshot({ path: `/tmp/e2e/q_${info.kind}_${shots++}.png` }); }
    const enabled = await page.$eval(".game-check", b => !b.disabled);
    if (!enabled) { errors.push("botón Comprobar deshabilitado tras responder " + info.kind); break; }
    await page.click(".game-check");
    await page.waitForSelector("[data-feedback]:not([hidden])");
    const fb = await page.evaluate(() => ({ cls: document.querySelector("[data-feedback]").className, title: document.querySelector(".fb-title").textContent, body: document.querySelector(".fb-body").textContent.slice(0, 80) }));
    log("   feedback:", fb.cls, "|", fb.title, "|", fb.body);
    await new Promise(r => setTimeout(r, 450));
    if (n === 1) await page.screenshot({ path: "./feedback.png" });
    const last = await page.$eval(".fb-next", b => b.textContent);
    if (last.trim() === "Terminar") { await Promise.all([page.waitForNavigation(), page.click(".fb-next")]); break; }
    await page.click(".fb-next");
  }
  await page.waitForSelector(".score");
  log("resultados:", page.url(), "| puntaje:", await page.$eval(".score", e => e.textContent), "|", await page.$eval(".result-head strong", e => e.textContent));
  await page.screenshot({ path: "./results.png" });
  log("errores JS/consola:", JSON.stringify(errors));
  await browser.close();
})().catch(e => { console.error("FALLÓ:", e.message); process.exit(1); });
