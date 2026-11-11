const { chromium } = require('playwright');
const BASE = process.env.OCD_URL || 'http://127.0.0.1:8069';
const OUT = process.env.OUT || './';
const pages = (process.argv[2] || 'dashboard').split(',');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, locale: 'fr-FR' });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('fonts.g')) errors.push(`console: ${m.text()}`); });
  await page.goto(BASE + '/web/login', { waitUntil: 'load' });
  await page.fill('input[name="login"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await page.press('input[name="password"]', 'Enter');
  await page.waitForSelector('.o_main_navbar', { timeout: 60000 });
  const targets = {
    dashboard: '/odoo/action-ocd_live.ocd_live_dashboard_action',
    planning: '/odoo/action-ocd_live.ocd_live_planning_action',
    regie: '/odoo/action-ocd_live_shop.ocd_live_regie_action',
    verify: '/odoo/action-ocd_live.ocd_live_verification_action',
    bookings: '/odoo/action-ocd_live.ocd_live_booking_action',
    links: '/odoo/action-ocd_live.ocd_directory_listing_action',
    vendors: '/odoo/action-ocd_live.res_partner_action_ocd_vendor',
    vendor: '/odoo/action-ocd_live.res_partner_action_ocd_vendor/' + (process.env.VENDOR_ID || 1),
    dispatch: '/odoo/action-ocd_live_shop.ocd_live_dispatch_action',
    parcels: '/odoo/action-ocd_live_shop.stock_picking_action_ocd_dispatch',
    parcel: '/odoo/action-ocd_live_shop.stock_picking_action_ocd_dispatch/' + (process.env.PARCEL_ID || 1),
    orders: '/odoo/action-ocd_live_shop.ocd_live_orders_action',
    couriers: '/odoo/action-ocd_live_shop.ocd_live_couriers_action',
    payouts: '/odoo/action-ocd_live_shop.ocd_payout_action',
    rates: '/odoo/action-ocd_live_shop.ocd_delivery_rate_action',
    settings: '/odoo/action-ocd_live.ocd_live_settings_action',
    odoo_settings: '/odoo/action-ocd_live.res_config_settings_action_ocd_live',
    recruit: '/odoo/action-ocd_live_recruitment.hr_applicant_action_ocd_host',
    tools: '/odoo/action-ocd_live.ocd_live_tools_action',
    autos: '/odoo/action-ocd_live.ocd_live_automations_action',
    crons: '/odoo/action-ocd_live.ocd_live_cron_action',
    whatsapp: '/odoo/action-ocd_live_whatsapp.ocd_whatsapp_inbox_action',
  };
  for (const name of pages) {
    await page.goto(BASE + targets[name], { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.o_action_manager .o_action, .o_action_manager > div', { timeout: 30000 });
    await page.waitForTimeout(1800);
    await page.screenshot({ path: `${OUT}bo-${name}.png` });
    console.log(name, 'ok');
  }
  console.log(errors.length ? errors.join('\n') : 'no JS errors');
  await browser.close();
})();
