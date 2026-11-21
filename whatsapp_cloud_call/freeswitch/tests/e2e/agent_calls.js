// End-to-end test of the WhatsApp calls with the real call server: the fake Meta calls the call
// server (TLS, digest, SDES), FreeSWITCH asks Odoo who rings, the agents answer in Odoo (Chromium,
// JsSIP, WebRTC), the call is checked in Odoo. Steps and setup: README.md of this folder.
//
//   OCD_URL=http://127.0.0.1:8079 node agent_calls.js
//
// Environment: OCD_URL, AGENT1=login:password (default admin:admin), AGENT2=login:password,
// META_CONTAINER (default fake-meta), META_RECORDINGS (folder of the recordings of the fake Meta).
const { chromium } = require("playwright");
const { execSync } = require("child_process");
const fs = require("fs");

const BASE = process.env.OCD_URL || "http://127.0.0.1:8079";
const [LOGIN1, PASSWORD1] = (process.env.AGENT1 || "admin:admin").split(":");
const [LOGIN2, PASSWORD2] = (process.env.AGENT2 || "kossi:kossi-e2e").split(":");
const META = process.env.META_CONTAINER || "fake-meta";
const RECORDINGS = process.env.META_RECORDINGS || "";
const SERVER = process.env.SERVER_CONTAINER || "ocd-fs";
const DOMAIN = process.env.OCD_SIP_DOMAIN || "calls.ocd.test";
const BYPASS = ["127.0.0.1", "localhost", DOMAIN, process.env.NO_PROXY || ""].filter(Boolean).join(",");

let failures = 0;
function check(name, condition, detail = "") {
  console.log(`${condition ? "ok  " : "FAIL"} ${name}${detail ? ` (${detail})` : ""}`);
  if (!condition) failures++;
}

function metaCall(wacid, seconds) {
  execSync(
    `docker exec ${META} fs_cli -x "bgapi originate {meta_name=${wacid},meta_seconds=${seconds},` +
      `sip_h_x-wa-meta-wacid=${wacid},sip_h_x-wa-meta-phone-number-id=1110001,` +
      `origination_caller_id_number=+237670000000,rtp_secure_media=mandatory:AES_CM_128_HMAC_SHA1_80,` +
      `absolute_codec_string=OPUS}sofia/gateway/ocd/+22890000001 &lua(/opt/fake_meta/meta_call.lua)"`
  );
}

function registered() {
  return execSync(`docker exec ${SERVER} fs_cli -x "sofia status profile ocd_agents reg"`).toString();
}

// loudness of a WAV file of 16 bits, between two seconds
function rms(path, from = 0, to = 1e9) {
  const data = fs.readFileSync(path);
  const rate = data.readUInt32LE(24);
  const channels = data.readUInt16LE(22);
  let offset = 12;
  while (offset < data.length - 8 && data.toString("ascii", offset, offset + 4) !== "data") {
    offset += 8 + data.readUInt32LE(offset + 4);
  }
  const start = offset + 8 + Math.floor(from * rate) * 2 * channels;
  const end = Math.min(data.length - 1, offset + 8 + Math.floor(to * rate) * 2 * channels);
  let sum = 0;
  let count = 0;
  for (let i = start; i < end; i += 2) {
    const value = data.readInt16LE(i);
    sum += value * value;
    count++;
  }
  return { rms: count ? Math.round(Math.sqrt(sum / count)) : 0, seconds: (data.length - offset - 8) / rate / 2 / channels };
}

async function agentPage(browser, login, password) {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  page.on("pageerror", (error) => console.log(`  [${login}] page error: ${error}`));
  // keep the peer connections to read their statistics
  await page.addInitScript(() => {
    const Original = window.RTCPeerConnection;
    window.__pcs = [];
    window.RTCPeerConnection = function (...args) {
      const pc = new Original(...args);
      window.__pcs.push(pc);
      return pc;
    };
    window.RTCPeerConnection.prototype = Original.prototype;
  });
  await page.goto(BASE + "/web/login");
  await page.fill("input[name=login]", login);
  await page.fill("input[name=password]", password);
  await page.press("input[name=password]", "Enter");
  await page.waitForSelector(".o_main_navbar", { timeout: 60000 });
  await page.locator(".o_whatsapp_softphone_systray button").waitFor({ timeout: 30000 });
  return page;
}

async function takeCalls(page, login) {
  await page.locator(".o_whatsapp_softphone_systray button").click();
  const toggle = page.locator("#o_whatsapp_softphone_available");
  if (!(await toggle.isChecked())) await toggle.check();
  await page.waitForSelector(".o_whatsapp_softphone_dot.bg-success", { timeout: 30000 });
  await page.keyboard.press("Escape");
  for (let i = 0; i < 20 && !registered().includes(login); i++) await page.waitForTimeout(500);
}

async function audioStats(page) {
  return page.evaluate(async () => {
    const pc = window.__pcs[window.__pcs.length - 1];
    if (!pc) return null;
    const result = { state: pc.iceConnectionState, received: 0, sent: 0, level: 0 };
    (await pc.getStats()).forEach((report) => {
      if (report.type === "inbound-rtp" && report.kind === "audio") {
        result.received = report.packetsReceived;
        result.level = report.audioLevel || 0;
      }
      if (report.type === "outbound-rtp" && report.kind === "audio") result.sent = report.packetsSent;
    });
    return result;
  });
}

async function odooCall(page, wacid) {
  return page.evaluate(async (wacid) => {
    const response = await fetch("/web/dataset/call_kw/whatsapp.call/search_read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0", method: "call",
        params: {
          model: "whatsapp.call", method: "search_read",
          args: [[["wacid", "=", wacid]], ["state", "user_id", "duration", "wait_duration", "ended_by", "reconnect_count", "channel_id", "notice_message_id", "end_cause"]],
          kwargs: {},
        },
      }),
    });
    return ((await response.json()).result || [])[0] || null;
  }, wacid);
}

async function waitState(page, wacid, states, seconds = 30) {
  let call = null;
  for (let i = 0; i < seconds * 2; i++) {
    call = await odooCall(page, wacid);
    if (call && states.includes(call.state)) return call;
    await page.waitForTimeout(500);
  }
  return call;
}

(async () => {
  const browser = await chromium.launch({
    args: [
      "--ignore-certificate-errors",
      "--use-fake-device-for-media-stream",
      "--use-fake-ui-for-media-stream",
      "--autoplay-policy=no-user-gesture-required",
    ],
    // the call server and Odoo are reached directly, never through a proxy of the environment
    // (Chromium reads both variables)
    env: { ...process.env, NO_PROXY: BYPASS, no_proxy: BYPASS },
  });
  const agent1 = await agentPage(browser, LOGIN1, PASSWORD1);
  const agent2 = await agentPage(browser, LOGIN2, PASSWORD2);

  // === 1. A customer calls, the agent answers, talks, hangs up === //
  console.log("1. call answered and hung up by the agent");
  await takeCalls(agent1, "agent");
  check("agent connected to the call server", /agent\d+@/.test(registered()));
  const wacid1 = `wacid.E2E.${Date.now()}`;
  metaCall(wacid1, 60);
  const panel1 = agent1.locator(".o_whatsapp_softphone_panel");
  await panel1.locator("button.btn-success").waitFor({ timeout: 30000 });
  await agent1.waitForTimeout(1500);
  const name = (await panel1.locator(".fw-bold.fs-5").textContent()).trim();
  check("the phone rings with the name of the customer", name === "Awa Ngono", name);
  await panel1.locator("button.btn-success").click();
  await panel1.locator("button.btn-danger").waitFor({ timeout: 15000 });
  const answered = await waitState(agent1, wacid1, ["answered"], 15);
  check("Odoo: answered by the agent", answered && answered.state === "answered", JSON.stringify(answered && answered.user_id));
  await agent1.waitForTimeout(8000);
  const stats = await audioStats(agent1);
  check("voice of the customer reaches the agent", stats && stats.received > 200, JSON.stringify(stats));
  check("voice of the agent leaves the browser", stats && stats.sent > 200, JSON.stringify(stats));
  await panel1.locator("button.btn-danger").click();
  const ended = await waitState(agent1, wacid1, ["completed"], 20);
  check("Odoo: completed, ended by the agent", ended && ended.state === "completed" && ended.ended_by === "agent", JSON.stringify(ended));
  check("Odoo: duration of the conversation", ended && ended.duration >= 6 && ended.duration <= 15, ended && String(ended.duration));
  check("Odoo: line in the conversation", ended && ended.notice_message_id);
  if (RECORDINGS) {
    await agent1.waitForTimeout(1000);
    const heard = rms(`${RECORDINGS}/${wacid1}.wav`);
    check("the customer heard the agent (fake microphone)", heard.rms > 100, JSON.stringify(heard));
  }

  // === 2. The agent is cut off (page closed): the call goes to the colleague === //
  console.log("2. agent cut off, the colleague gets the call");
  await takeCalls(agent2, LOGIN2 === "kossi" ? "agent" : "agent");
  const wacid2 = `wacid.CUT.${Date.now()}`;
  metaCall(wacid2, 120);
  const ring1 = agent1.locator(".o_whatsapp_softphone_panel button.btn-success");
  await ring1.waitFor({ timeout: 30000 });
  await ring1.click();
  await agent1.locator(".o_whatsapp_softphone_panel button.btn-danger").waitFor({ timeout: 15000 });
  await waitState(agent2, wacid2, ["answered"], 15);
  await agent1.waitForTimeout(3000);
  const cutAt = Date.now();
  await agent1.context().close(); // network lost: no hang-up sent
  const panel2 = agent2.locator(".o_whatsapp_softphone_panel");
  await panel2.locator("button.btn-success").waitFor({ timeout: 60000 });
  check("the colleague rings after the agent is cut off", true, `${Math.round((Date.now() - cutAt) / 1000)} s`);
  await panel2.locator("button.btn-success").click();
  await panel2.locator("button.btn-danger").waitFor({ timeout: 15000 });
  await agent2.waitForTimeout(5000);
  const stats2 = await audioStats(agent2);
  check("voice of the customer reaches the colleague", stats2 && stats2.received > 100, JSON.stringify(stats2));
  await panel2.locator("button.btn-danger").click();
  const ended2 = await waitState(agent2, wacid2, ["completed"], 20);
  check("Odoo: completed by the colleague, agent cut off once",
    ended2 && ended2.state === "completed" && ended2.reconnect_count === 1 && ended2.user_id && ended2.user_id[1] !== "",
    JSON.stringify(ended2));

  await browser.close();
  console.log(failures ? `${failures} failure(s)` : "all checks passed");
  process.exit(failures ? 1 : 0);
})().catch((error) => {
  console.error("FAIL", error);
  process.exit(1);
});
