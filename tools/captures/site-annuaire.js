const { chromium } = require('playwright');
const BASE = process.env.OCD_URL || 'http://127.0.0.1:8069';
const OUT = process.env.OUT || './';
const TOKEN = process.argv[2];
const sizes = { phone: { width: 390, height: 844 }, desktop: { width: 1280, height: 860 } };
(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const [label, viewport] of Object.entries(sizes)) {
    const context = await browser.newContext({ viewport, locale: 'fr-FR' });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(`${label} pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('fonts.g')) errors.push(`${label} console: ${m.text()}`); });
    const go = async (path, name, full = false) => {
      const r = await page.goto(BASE + path, { waitUntil: 'load' }); await page.waitForTimeout(350);
      await page.screenshot({ path: `${OUT}${label}-d-${name}.png`, fullPage: full });
      console.log(label, path, r.status());
    };
    await go('/lives', '1-lives');
    await go('/lives/cm', '2-country');
    await go('/lives/pass', '3-pass-anon', true);
    await go('/ocd/connexion', '4-login');
    await go(`/ocd/espace/${TOKEN}`, '5-space', true);
    await go('/lives/pass', '6-pass-active');
    await go('/lives/envoyer', '7-send', true);
    await page.fill('#g-url', 'tiktok.com/@awa/live'); await page.waitForTimeout(200);
    await page.screenshot({ path: `${OUT}${label}-d-7b-send-ok.png` });
    await page.click('.o_ocd_actions button[type=submit]'); await page.waitForLoadState('load'); await page.waitForTimeout(300);
    console.log(label, 'status page', page.url());
    await page.screenshot({ path: `${OUT}${label}-d-8-status.png` });
    // end the live so the next size can send again
    const end = await page.$('form[action$="/fin"] button');
    if (end) { await end.click(); await page.waitForLoadState('load'); }
    await context.close();
  }
  console.log(errors.length ? errors.join('\n') : 'no JS errors');
  await browser.close();
})();
