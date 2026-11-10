// Pages of the shop on the website (boutique of a vendor, replay), in French, on phone,
// tablet and computer.
// Usage: OCD_URL=http://127.0.0.1:8069 OUT=docs/captures/ node tools/captures/site-shop.js <vendor sold by OCD> <vendor in direct contact>
// With the demo data: Brenda Wax (sold by OCD, with a replay) and Awa Mensah (direct contact).
const { chromium } = require('playwright');
const BASE = process.env.OCD_URL || 'http://127.0.0.1:8069';
const OUT = process.env.OUT || './';
const [OCD_VENDOR, DIRECT_VENDOR] = process.argv.slice(2);
const sizes = {
  phone: { width: 390, height: 844 },
  tablet: { width: 820, height: 1180 },
  desktop: { width: 1280, height: 860 },
};
(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const [label, viewport] of Object.entries(sizes)) {
    const context = await browser.newContext({ viewport, locale: 'fr-FR' });
    await context.addCookies([{ name: 'frontend_lang', value: 'fr_FR', url: BASE }]);
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(`${label} pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('fonts.g')) errors.push(`${label} console: ${m.text()}`); });
    const go = async (path, name, full = true) => {
      const r = await page.goto(BASE + path, { waitUntil: 'networkidle' });
      await page.screenshot({ path: `${OUT}site-${label}-s-${name}.png`, fullPage: full });
      console.log(label, path, r.status());
    };
    await go(`/ocd/boutique/${OCD_VENDOR}`, '1-vitrine');
    await go(`/ocd/boutique/${DIRECT_VENDOR}`, '1b-vitrine-direct');
    await go(`/ocd/boutique/${OCD_VENDOR}/replay`, '2-replay');
    await context.close();
  }
  console.log(errors.length ? errors.join('\n') : 'no JS errors');
  await browser.close();
})();
