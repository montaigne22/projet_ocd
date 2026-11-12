// Cards of the feed (a short video, the carousel of the products, an image), the page « My card in
// the lives » and the page « Join my live ».
//   node tools/captures/site-cartes.js <personal link of a vendor> <path of « Join my live »> [names...]
// The names are the vendors whose card is taken (by default the three of the demo in Togo).
const { chromium } = require('playwright');
const BASE = process.env.OCD_URL || 'http://127.0.0.1:8069';
const OUT = process.env.OUT || './';
const [TOKEN, JOIN, ...NAMES] = process.argv.slice(2);
const names = NAMES.length ? NAMES : ['Awa', 'Kossi', 'Ama'];
const sizes = { phone: { width: 390, height: 844 }, desktop: { width: 1280, height: 860 } };
(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const [label, viewport] of Object.entries(sizes)) {
    const context = await browser.newContext({ viewport, locale: 'fr-FR', deviceScaleFactor: 2 });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(`${label} pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('fonts.g')) errors.push(`${label} console: ${m.text()}`); });
    await page.goto(`${BASE}/lives?pays=tg`, { waitUntil: 'load' });
    await page.waitForTimeout(800);
    for (const [index, name] of names.entries()) {
      const found = await page.evaluate((who) => {
        const feed = document.querySelector('.o_ocd_feed');
        const card = [...feed.querySelectorAll('.o_ocd_feed_person')].find((el) => (el.getAttribute('aria-label') || '').includes(who));
        if (!card) {
          return false;
        }
        feed.scrollTop = card.offsetTop;
        return true;
      }, name);
      await page.waitForTimeout(2200);
      if (found) {
        await page.screenshot({ path: `${OUT}site-${label}-c-${index + 1}-carte-${name.toLowerCase()}.png` });
      }
      console.log(label, name, found ? 'ok' : 'not in the feed');
    }
    if (label === 'phone' && TOKEN) {
      await page.goto(`${BASE}/ocd/espace/${TOKEN}`, { waitUntil: 'load' });
      await page.goto(`${BASE}/ocd/espace/moi/carte`, { waitUntil: 'load' });
      await page.waitForTimeout(800);
      await page.screenshot({ path: `${OUT}site-phone-c-4-ma-carte.png`, fullPage: true });
      console.log(label, 'my card ok');
    }
    if (label === 'phone' && JOIN) {
      await page.goto(`${BASE}${JOIN}`, { waitUntil: 'load' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${OUT}site-phone-c-5-rejoindre-mon-live.png`, fullPage: true });
      console.log(label, 'join ok');
    }
    await context.close();
  }
  console.log(errors.length ? errors.join('\n') : 'no JS errors');
  await browser.close();
})();
