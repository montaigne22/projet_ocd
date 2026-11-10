const { chromium } = require('playwright');
const BASE = process.env.OCD_URL || 'http://127.0.0.1:8069';
const OUT = process.env.OUT || './';
const sizes = { phone: { width: 390, height: 844 } };
(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const [label, viewport] of Object.entries(sizes)) {
    const context = await browser.newContext({ viewport, locale: 'fr-FR' });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(`${label} pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('fonts.g')) errors.push(`${label} console: ${m.text()}`); });
    const shot = async (name, full = false) => page.screenshot({ path: `${OUT}${label}-${name}.png`, fullPage: full });
    await page.goto(BASE + '/ocd', { waitUntil: 'load' }); await page.waitForTimeout(400);
    await shot('1-home');
    await page.click('a.o_ocd_choice >> nth=0'); await page.waitForLoadState('load'); await page.waitForTimeout(300);
    await shot('2-day');
    await page.click('a.o_ocd_day >> nth=' + (label === 'phone' ? 5 : label === 'tablet' ? 6 : 7)); await page.waitForLoadState('load'); await page.waitForTimeout(300);
    await shot('3-hour');
    await page.click('a.o_ocd_slot >> nth=1'); await page.waitForLoadState('load'); await page.waitForTimeout(300);
    await shot('4-package', true);
    await page.click('a.o_ocd_pack >> nth=0'); await page.waitForLoadState('load'); await page.waitForTimeout(300);
    await page.fill('#f-name', `Awa Mensah ${label}`);
    await page.fill('#f-city', 'Lomé');
    await page.fill('#f-phone', '9' + String(Date.now()).slice(-7));
    await page.waitForTimeout(200);
    await shot('5-infos', true);
    await page.click('.o_ocd_actions button[type=submit]'); await page.waitForLoadState('load'); await page.waitForTimeout(800);
    console.log(label, 'pay url', page.url());
    await shot('6-pay', true);
    // voice caption
    await page.click('.o_ocd_live_voice_play'); await page.waitForTimeout(500);
    await shot('7-voice');
    await context.close();
  }
  console.log(errors.length ? errors.join('\n') : 'no JS errors');
  await browser.close();
})();
