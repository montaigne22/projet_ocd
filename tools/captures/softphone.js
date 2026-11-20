// The phone of the agents (whatsapp_cloud_call) with a simulated call: JsSIP is replaced by a fake
// that registers and receives the calls the script gives it. Fails when a step breaks.
//   OCD_URL=http://127.0.0.1:8069 OCD_CALL_ID=<id of a call> [OUT=docs/captures/] node tools/captures/softphone.js
// admin/admin must be an agent of a WhatsApp account with calls, with the address of the call server
// entered (Settings > WhatsApp > Calls); the call (WhatsApp > Calls) gives the name shown.
const { chromium } = require("playwright");

const BASE = process.env.OCD_URL || "http://127.0.0.1:8069";
const CALL_ID = parseInt(process.env.OCD_CALL_ID || "0", 10);
const OUT = process.env.OUT || "";

const FAKE_JSSIP = `
window.__sessions = [];
class Emitter { constructor() { this.h = {}; } on(e, f) { (this.h[e] = this.h[e] || []).push(f); } emit(e, a) { (this.h[e] || []).forEach((f) => f(a)); } }
class Session extends Emitter {
  constructor(name, user) { super(); this.remote_identity = { display_name: name, uri: { user } }; this.connection = null; this.answered = false; this.terminated = null; this.muted = false; }
  answer(opts) { this.answered = true; this.answerOpts = opts; }
  terminate(opts) { this.terminated = opts || {}; setTimeout(() => this.emit("ended", {}), 10); }
  mute() { this.muted = true; }
  unmute() { this.muted = false; }
}
class UA extends Emitter {
  constructor(cfg) { super(); this.cfg = cfg; window.__fakeUA = this; }
  start() { setTimeout(() => this.emit("registered", {}), 100); }
  stop() { this.stopped = true; }
  incoming(name, user, callId) {
    const s = new Session(name, user);
    window.__sessions.push(s);
    this.emit("newRTCSession", { originator: "remote", session: s, request: { getHeader: (h) => (h === "X-OCD-Call" ? String(callId) : "") } });
    return window.__sessions.length - 1;
  }
}
window.JsSIP = { UA, WebSocketInterface: class { constructor(url) { this.url = url; } }, C: { causes: {} }, version: "fake" };
`;

function check(name, condition) {
  console.log((condition ? "ok   " : "FAIL ") + name);
  if (!condition) {
    process.exitCode = 1;
  }
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !m.text().includes("WebSocket")) errors.push(m.text()); });
  await page.route("**/whatsapp_cloud_call/static/lib/jssip/jssip.min.js", (route) =>
    route.fulfill({ status: 200, contentType: "application/javascript", body: FAKE_JSSIP }));
  await page.goto(BASE + "/web/login");
  await page.fill("input[name=login]", "admin");
  await page.fill("input[name=password]", "admin");
  await page.press("input[name=password]", "Enter");
  await page.waitForSelector(".o_main_navbar", { timeout: 60000 });

  const systray = page.locator(".o_whatsapp_softphone_systray button");
  await systray.waitFor({ timeout: 20000 });
  check("phone in the top bar", await systray.isVisible());
  await systray.click();
  await page.locator("#o_whatsapp_softphone_available").check();
  await page.waitForFunction(() => window.__fakeUA, null, { timeout: 10000 });
  const cfg = await page.evaluate(() => ({ uri: window.__fakeUA.cfg.uri, wss: window.__fakeUA.cfg.sockets[0].url }));
  check(`connected to ${cfg.wss} as ${cfg.uri}`, cfg.wss.startsWith("wss://") && cfg.uri.startsWith("sip:agent"));
  await page.locator(".o_whatsapp_softphone_menu .text-muted").first().waitFor();
  if (OUT) {
    await page.screenshot({ path: OUT + "softphone_menu.png", clip: { x: 866, y: 0, width: 500, height: 260 } });
  }
  await page.keyboard.press("Escape");

  const panel = page.locator(".o_whatsapp_softphone_panel");
  await page.evaluate((id) => window.__fakeUA.incoming("Customer", "237670000000", id), CALL_ID);
  await panel.locator("button:has-text('Answer'), button:has-text('Décrocher')").first().waitFor({ timeout: 10000 });
  await page.waitForTimeout(800);
  const name = (await panel.locator(".fw-bold.fs-5").textContent()).trim();
  check(`incoming call shown: ${name}`, Boolean(name));
  if (OUT) {
    await page.screenshot({ path: OUT + "softphone_incoming.png" });
  }
  await panel.locator("button.btn-success").click();
  await panel.locator("button.btn-danger").waitFor();
  check("answered", await page.evaluate(() => window.__sessions[0].answered));
  await panel.locator("button.btn-secondary").click();
  check("microphone off", await page.evaluate(() => window.__sessions[0].muted));
  const second = await page.evaluate(() => window.__fakeUA.incoming("Other", "237690000000", 0));
  await page.waitForTimeout(200);
  const busy = await page.evaluate((i) => window.__sessions[i].terminated, second);
  check("second call refused while busy (486)", busy && busy.status_code === 486);
  if (OUT) {
    await page.screenshot({ path: OUT + "softphone_call.png" });
  }
  await panel.locator("button.btn-danger").click();
  await page.waitForTimeout(300);
  check("panel closed after hanging up", (await panel.count()) === 0);
  const third = await page.evaluate((id) => window.__fakeUA.incoming("Customer", "237670000000", id), CALL_ID);
  await panel.locator("button.btn-danger").click();
  await page.waitForTimeout(500);
  const declined = await page.evaluate((i) => window.__sessions[i].terminated, third);
  check("declined (603)", declined && declined.status_code === 603);

  // the real bundle of JsSIP loads
  const page2 = await context.newPage();
  await page2.goto(BASE + "/odoo");
  await page2.waitForFunction(() => window.JsSIP, null, { timeout: 30000 });
  const version = await page2.evaluate(() => window.JsSIP.version + " " + typeof window.JsSIP.UA);
  check(`real JsSIP: ${version}`, version.endsWith("function"));
  check(`no error in the page ${JSON.stringify(errors)}`, errors.length === 0);
  await browser.close();
})().catch((e) => {
  console.error("FAIL", e);
  process.exit(1);
});
