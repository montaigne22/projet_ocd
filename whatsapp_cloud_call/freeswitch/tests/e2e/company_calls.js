// End-to-end test of the calls of the company (phase 2.2): the agent calls a customer from the
// phone of the top bar (Chromium, JsSIP), the call server checks the call with Odoo and calls the
// fake Meta through its gateway (TLS), the customer answers; voice both ways; the agent hangs up;
// the call is checked in Odoo. Setup: README.md of this folder (OCD_META_SIP in the .env).
//
//   OCD_URL=http://127.0.0.1:8079 ODOO_DB=e2e META_RECORDINGS=/tmp/meta node company_calls.js
//
// The call prepared by Odoo (whatsapp_action_call, after the checks of Meta, tested in the tests
// of Odoo) is written here with psql: the Graph API of Meta is not reached in this test.
const { chromium } = require("playwright");
const { execSync } = require("child_process");
const fs = require("fs");

const BASE = process.env.OCD_URL || "http://127.0.0.1:8079";
const DB = process.env.ODOO_DB || "e2e";
const [LOGIN, PASSWORD] = (process.env.AGENT1 || "admin:admin").split(":");
const RECORDINGS = process.env.META_RECORDINGS || "";
const DOMAIN = process.env.OCD_SIP_DOMAIN || "calls.ocd.test";
const BYPASS = ["127.0.0.1", "localhost", DOMAIN, process.env.NO_PROXY || ""].filter(Boolean).join(",");

let failures = 0;
function check(name, condition, detail = "") {
  console.log(`${condition ? "ok  " : "FAIL"} ${name}${detail ? ` (${detail})` : ""}`);
  if (!condition) failures++;
}

function sql(query) {
  return execSync(`psql -d ${DB} -tAc "${query}"`).toString().trim();
}

(async () => {
  const browser = await chromium.launch({
    args: ["--ignore-certificate-errors", "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
           "--autoplay-policy=no-user-gesture-required"],
    env: { ...process.env, NO_PROXY: BYPASS, no_proxy: BYPASS },
  });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  page.on("pageerror", (error) => console.log(`  page error: ${error}`));
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
  await page.fill("input[name=login]", LOGIN);
  await page.fill("input[name=password]", PASSWORD);
  await page.press("input[name=password]", "Enter");
  await page.waitForSelector(".o_main_navbar", { timeout: 60000 });
  await page.locator(".o_whatsapp_softphone_systray button").click();
  const toggle = page.locator("#o_whatsapp_softphone_available");
  if (!(await toggle.isChecked())) await toggle.check();
  await page.waitForSelector(".o_whatsapp_softphone_dot.bg-success", { timeout: 30000 });
  await page.keyboard.press("Escape");

  console.log("3. the agent calls a customer through WhatsApp");
  const uid = sql(`select id from res_users where login = '${LOGIN}'`);
  const channel = sql("select id from discuss_channel where channel_type = 'whatsapp' and whatsapp_number = '237670000000' limit 1");
  const account = sql("select whatsapp_account_id from discuss_channel where id = " + channel);
  const partner = sql("select whatsapp_partner_id from discuss_channel where id = " + channel);
  const callId = sql(
    "insert into whatsapp_call (account_id, company_id, direction, channel_id, partner_id, number, user_id, state, " +
    "start_date, create_date, write_date, create_uid, write_uid) select " +
    `${account}, company_id, 'outbound', ${channel}, ${partner}, '237670000000', ${uid}, 'ringing', ` +
    `now() at time zone 'utc', now() at time zone 'utc', now() at time zone 'utc', ${uid}, ${uid} ` +
    `from whatsapp_account where id = ${account} returning id`
  ).split("\n")[0];
  await page.evaluate((id) => odoo.__WOWL_DEBUG__.root.env.services.whatsapp_softphone.dial(
    { call_id: Number(id), name: "Awa Ngono", number: "+237670000000" }), callId);
  const panel = page.locator(".o_whatsapp_softphone_panel");
  await panel.locator("text=In call").waitFor({ timeout: 30000 }).catch(() => {});
  const shown = (await panel.count()) ? (await panel.innerText()).split("\n").join(" | ") : "(no panel)";
  check("the agent is in call with the customer", shown.includes("In call") && shown.includes("Awa Ngono"), shown);
  // the call server tells Odoo right after the answer (in its own thread): a few seconds at most
  let answered = "";
  for (let i = 0; i < 10 && answered !== "answered"; i++) {
    answered = sql(`select state from whatsapp_call where id = ${callId}`);
    if (answered !== "answered") await page.waitForTimeout(500);
  }
  check("Odoo: answered", answered === "answered", answered);
  await page.waitForTimeout(8000);
  const stats = await page.evaluate(async () => {
    const pc = window.__pcs[window.__pcs.length - 1];
    if (!pc) return null;
    const result = { state: pc.iceConnectionState, received: 0, sent: 0 };
    (await pc.getStats()).forEach((report) => {
      if (report.type === "inbound-rtp" && report.kind === "audio") result.received = report.packetsReceived;
      if (report.type === "outbound-rtp" && report.kind === "audio") result.sent = report.packetsSent;
    });
    return result;
  });
  check("voice of the customer reaches the agent", stats && stats.received > 200, JSON.stringify(stats));
  check("voice of the agent leaves the browser", stats && stats.sent > 200, JSON.stringify(stats));
  await panel.locator("button.btn-danger").click();
  await page.waitForTimeout(3000);
  const row = sql(`select state, direction, duration, ended_by, server_seen from whatsapp_call where id = ${callId}`);
  const [state, direction, duration, endedBy, serverSeen] = row.split("|");
  check("Odoo: call of the company completed, ended by the agent", state === "completed" && direction === "outbound"
        && endedBy === "agent" && serverSeen === "t", row);
  check("Odoo: duration of the conversation", Number(duration) >= 6 && Number(duration) <= 15, duration);
  const notice = sql(`select body from mail_message where id = (select notice_message_id from whatsapp_call where id = ${callId})`);
  check("Odoo: line in the conversation", notice.includes("Call to the customer of"), notice);
  const trace = sql(`select phone_trace from whatsapp_call where id = ${callId}`);
  check("Odoo: diagnostic of the phone", trace.includes("call sent") && trace.includes("established"), trace.slice(0, 200));
  if (RECORDINGS) {
    const path = `${RECORDINGS}/out_237670000000.wav`;
    check("the customer heard the agent (recording of the fake Meta)", fs.existsSync(path) && fs.statSync(path).size > 50000,
          fs.existsSync(path) ? String(fs.statSync(path).size) : "no recording");
  }

  console.log("4. a call that Odoo did not prepare is refused by the call server");
  const before = Number(sql("select count(*) from whatsapp_call"));
  await page.evaluate(() => odoo.__WOWL_DEBUG__.root.env.services.whatsapp_softphone.dial(
    { call_id: 999999, name: "Nobody", number: "+237600000000" }));
  await page.waitForTimeout(4000);
  const message = await page.locator(".o_whatsapp_softphone_panel").innerText().catch(() => "");
  check("refused, the agent told why", message.includes("The call did not leave"), message.split("\n").join(" | "));
  check("no call created", Number(sql("select count(*) from whatsapp_call")) === before);

  await browser.close();
  console.log(failures ? `${failures} failure(s)` : "all checks passed");
  process.exit(failures ? 1 : 0);
})();
