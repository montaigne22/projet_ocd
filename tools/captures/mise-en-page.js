// Layout check of the screens that grow with the data: the feed of the lives, the home page and
// « To check » of the back office. Fails (exit 1) when a rule is broken, at the sizes of a phone,
// a tablet, a laptop (1366 x 657) and large screens:
// - nothing wider than the page;
// - feed: no card cut, the cards wide enough for their product (tablet and up), « I am live »
//   above the cards on a large screen and small in the top bar on a phone, a country picked brings its
//   band under the head;
// - home: only the countries with a live and the one of the visitor, then « All countries »;
// - the page of a country: its cards not cut, never one card stretched over the page;
// - « To check »: no column squeezed under 280 px, no card wider than its column, no empty
//   column on the board;
// - the screens of the team on a phone and a tablet: nothing wider than the screen; on a phone, no
//   chat bubbles of Odoo over it, no card cut (« To check », « Dispatch »);
// - the pages of the site on a phone: nothing wider than the screen, titles at a phone size, the
//   title of the bar on one line, the bar at the bottom low;
// - with OCD_SPACE_LINK (the personal link of a vendor of the demo): « My space » has every entry
//   of the computer on a phone and a tablet, each page of it with the menu at the bottom on a
//   phone, no heading covered, no amount cut in « My figures ».
//
//   OCD_URL=http://127.0.0.1:8069 [OCD_SPACE_LINK=/ocd/espace/<token>] node tools/captures/mise-en-page.js
// (a base with lives and things to check: the demo, ocd_live_demo; the back office as admin)
const { chromium } = require('playwright');
const BASE = process.env.OCD_URL || 'http://127.0.0.1:8069';
const LOGIN = process.env.OCD_LOGIN || 'admin';
const PASSWORD = process.env.OCD_PASSWORD || 'admin';
const SITE_SIZES = [[390, 844], [820, 1180], [1024, 768], [1366, 657], [1440, 900], [1914, 810]];
// 1456 x 680: a screen of 1820 x 850 with the browser zoomed at 125 %
const BACK_SIZES = [[1366, 657], [1456, 680], [1820, 850]];

const failures = [];
function check(ok, what) {
    console.log(`${ok ? 'ok  ' : 'FAIL'} ${what}`);
    if (!ok) {
        failures.push(what);
    }
}

async function feed(browser, [width, height]) {
    const page = await (await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })).newPage();
    await page.goto(`${BASE}/lives`, { waitUntil: 'load' });
    await page.waitForTimeout(1500);
    const size = `lives ${width}x${height}`;
    const info = await page.evaluate(() => {
        const cards = [...document.querySelectorAll('.o_ocd_feed_card')];
        const shown = (el) => el && getComputedStyle(el).display !== 'none';
        const photos = [...document.querySelectorAll('.o_ocd_feed_tile img')]
            .map((img) => img.getBoundingClientRect().width).filter((w) => w > 0);
        return {
            over: document.documentElement.scrollWidth - innerWidth,
            cut: cards.filter((card) => card.scrollHeight > card.clientHeight + 1).map((card) => card.dataset.key),
            narrowest: Math.min(...cards.filter((card) => card.classList.contains('o_ocd_feed_person'))
                .map((card) => card.getBoundingClientRect().width)),
            smallestPhoto: photos.length ? Math.min(...photos) : null,
            ctaTop: shown(document.querySelector('.o_ocd_feed_live_cta')),
            ctaBottom: shown(document.querySelector('.o_ocd_bottom_cta')),
            ctaBar: shown(document.querySelector('.o_ocd_header_live')),
        };
    });
    const large = width >= 768;
    check(info.over <= 0, `${size}: nothing wider than the page (${info.over}px)`);
    check(!info.cut.length, `${size}: no card cut ${info.cut.join(' ')}`);
    if (large) {
        check(info.narrowest >= 320, `${size}: cards 320 px wide at least (${Math.round(info.narrowest)})`);
        check(info.smallestPhoto === null || info.smallestPhoto >= 120,
            `${size}: product photos 120 px wide at least (${Math.round(info.smallestPhoto)})`);
        check(info.ctaTop && !info.ctaBottom && !info.ctaBar, `${size}: « I am live » above the cards, not over them`);
        // A country picked: its band right under the head
        const band = await page.$('.o_ocd_feed_divider[data-country-start]');
        if (band) {
            const code = await band.getAttribute('data-country-start');
            await page.click(`.o_ocd_feed_chip[data-country="${code}"]`);
            await page.waitForTimeout(2000);
            const gap = await page.evaluate((code) => {
                const el = document.querySelector(`[data-country-start="${code}"]`);
                return el.getBoundingClientRect().top - document.querySelector('.o_ocd_feed_head').getBoundingClientRect().bottom;
            }, code);
            check(gap >= 0 && gap <= 40, `${size}: the country picked (${code}) under the head (${Math.round(gap)}px)`);
        }
    } else {
        check(info.ctaBar && !info.ctaBottom && !info.ctaTop, `${size}: « I am live » small in the bar of the phone, never over the cards`);
    }
    await page.context().close();
}

async function country(browser, [width, height]) {
    // The page of a country: the cards of the feed under its filters, never one card over the width
    const page = await (await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })).newPage();
    await page.goto(`${BASE}/ocd`, { waitUntil: 'load' });
    const link = await page.$('.o_ocd_home .o_ocd_chip:not(.o_ocd_chip_all)');
    if (!link) {
        await page.context().close();
        return;
    }
    const href = await link.getAttribute('href');
    await page.goto(`${BASE}${href}`, { waitUntil: 'load' });
    await page.waitForTimeout(1200);
    const size = `${href} ${width}x${height}`;
    const info = await page.evaluate(() => {
        const cards = [...document.querySelectorAll('.o_ocd_feed_person')];
        const widths = cards.map((card) => card.getBoundingClientRect().width);
        return {
            over: document.documentElement.scrollWidth - innerWidth,
            cards: cards.length,
            cut: cards.filter((card) => card.scrollHeight > card.clientHeight + 1).length,
            narrowest: widths.length ? Math.min(...widths) : null,
            widest: widths.length ? Math.max(...widths) : null,
        };
    });
    check(info.over <= 0, `${size}: nothing wider than the page (${info.over}px)`);
    check(!info.cut, `${size}: no card cut (${info.cut})`);
    if (info.cards && width >= 768) {
        check(info.narrowest >= 320, `${size}: cards 320 px wide at least (${Math.round(info.narrowest)})`);
        check(info.widest <= 640, `${size}: no card stretched over the page (${Math.round(info.widest)})`);
    }
    await page.context().close();
}

async function home(browser, [width, height]) {
    const page = await (await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })).newPage();
    await page.goto(`${BASE}/ocd`, { waitUntil: 'load' });
    await page.waitForTimeout(800);
    const size = `home ${width}x${height}`;
    const info = await page.evaluate(() => {
        const chips = [...document.querySelectorAll('.o_ocd_home .o_ocd_chip:not(.o_ocd_chip_all)')];
        return {
            over: document.documentElement.scrollWidth - innerWidth,
            chips: chips.length,
            empty: chips.filter((chip) => chip.querySelector('.o_ocd_chip_count')?.textContent.trim() === '0').length,
            all: !!document.querySelector('.o_ocd_home .o_ocd_chip_all'),
        };
    });
    check(info.over <= 0, `${size}: nothing wider than the page (${info.over}px)`);
    check(info.empty <= 1, `${size}: one country without a live at most, the visitor's (${info.empty} of ${info.chips})`);
    check(info.all, `${size}: « All countries » after them`);
    await page.context().close();
}

// The space of a vendor, from the personal link of a vendor of the demo (OCD_SPACE_LINK, e.g.
// /ocd/espace/<token>): the entries of the menu are the same at every size (the phone too), no
// heading under the block that follows it, no amount cut in « My figures »
const SPACE_LINK = process.env.OCD_SPACE_LINK;
const spaceEntries = {};

async function space(browser, [width, height]) {
    const page = await (await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })).newPage();
    await page.goto(`${BASE}${SPACE_LINK}`, { waitUntil: 'load' });
    await page.goto(`${BASE}/ocd/espace/moi`, { waitUntil: 'load' });
    await page.waitForTimeout(1000);
    const size = `my space ${width}x${height}`;
    const info = await page.evaluate(() => {
        const menu = document.querySelector('.o_ocd_space_menu');
        const shown = (el) => el.getBoundingClientRect().width > 0 && getComputedStyle(el).display !== 'none';
        const covered = [...document.querySelectorAll('.o_ocd_section')].filter((heading) => {
            const next = heading.nextElementSibling;
            return next && shown(next) && next.getBoundingClientRect().top < heading.getBoundingClientRect().bottom - 1;
        }).map((heading) => heading.textContent.trim());
        return {
            over: document.documentElement.scrollWidth - innerWidth,
            menu: menu && shown(menu),
            entries: menu ? [...menu.querySelectorAll('a')].filter((a) => !a.classList.contains('o_ocd_space_menu_more'))
                .map((a) => a.getAttribute('href')) : [],
            covered,
        };
    });
    spaceEntries[width] = info.entries;
    check(info.over <= 0, `${size}: nothing wider than the page (${info.over}px)`);
    check(info.menu, `${size}: the menu of the space is there`);
    check(!info.covered.length, `${size}: no heading under the block that follows it ${info.covered.join(', ')}`);
    if (width < 768) {
        // On a phone, every page of the space keeps the menu at the bottom (back to the home page)
        for (const href of info.entries) {
            await page.goto(`${BASE}${href}`, { waitUntil: 'load' });
            const nav = await page.evaluate(() => {
                const el = document.querySelector('.o_ocd_nav');
                return !!el && getComputedStyle(el).display !== 'none' && !!el.querySelector('a[href="/ocd"]');
            });
            check(nav, `${size}: ${href} has the menu at the bottom`);
        }
    }
    await page.goto(`${BASE}/ocd/espace/moi/chiffres`, { waitUntil: 'load' });
    await page.waitForTimeout(800);
    const cut = await page.evaluate(() => [...document.querySelectorAll('.o_ocd_figures_tile > b')]
        .filter((b) => b.scrollWidth > b.clientWidth + 1).map((b) => b.textContent.trim()));
    check(!cut.length, `${size}: no amount cut in « My figures » ${cut.join(', ')}`);
    await page.context().close();
}

async function board(browser, [width, height]) {
    const page = await (await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })).newPage();
    await page.goto(`${BASE}/web/login`, { waitUntil: 'load' });
    await page.fill('input[name="login"]', LOGIN);
    await page.fill('input[name="password"]', PASSWORD);
    await page.press('input[name="password"]', 'Enter');
    await page.waitForSelector('.o_main_navbar', { timeout: 60000 });
    await page.goto(`${BASE}/odoo/action-ocd_live.ocd_live_verification_action`, { waitUntil: 'load' });
    await page.waitForSelector('.o_ocd_verification_body', { timeout: 60000 });
    await page.waitForTimeout(1000);
    const size = `to check ${width}x${height}`;
    const info = await page.evaluate(() => {
        const columns = [...document.querySelectorAll('.o_ocd_verification_column')];
        const outside = [...document.querySelectorAll('.o_ocd_verification_card *')].filter((el) =>
            el.getBoundingClientRect().right > el.closest('.o_ocd_verification_card').getBoundingClientRect().right + 1);
        return {
            narrowest: columns.length ? Math.min(...columns.map((column) => column.getBoundingClientRect().width)) : null,
            sideways: columns.filter((column) => column.scrollWidth > column.clientWidth + 1).length,
            outside: outside.length,
            emptyColumns: columns.filter((column) => !column.querySelector('.o_ocd_verification_card')).length,
            board: document.querySelector('.o_ocd_verification_body').scrollWidth - document.querySelector('.o_ocd_verification_body').clientWidth,
        };
    });
    check(info.narrowest === null || info.narrowest >= 279, `${size}: columns 280 px wide at least (${Math.round(info.narrowest)})`);
    check(!info.sideways, `${size}: no column scrolls sideways (${info.sideways})`);
    check(!info.outside, `${size}: nothing wider than its card (${info.outside})`);
    check(!info.emptyColumns, `${size}: no empty column on the board (${info.emptyColumns})`);
    check(info.board <= 0, `${size}: the board scrolls inside the page, not the page (${info.board}px)`);
    await page.context().close();
}

// The pages of the site on a phone (chantier 25.5): nothing wider than the screen, the title of the
// page at a phone size (26 px, never 32 px on three lines), the title of the bar on one line, the bar
// at the bottom low; the first product and the first boutique found are checked too
const SITE_PHONE_PATHS = ['/', '/lives', '/shop', '/lives/programme', '/lives/pays', '/vote', '/billets', '/evenements',
    '/express', '/business', '/ambassadeurs', '/points-relais', '/ocd/connexion', '/reserver/studio', '/ocd/garantie',
    '/shop/cart', '/lives/pass'];

async function sitePhone(browser, [width, height]) {
    const context = await browser.newContext({ viewport: { width, height }, locale: 'fr-FR', isMobile: true, hasTouch: true });
    const page = await context.newPage();
    const paths = [...SITE_PHONE_PATHS];
    await page.goto(`${BASE}/shop`, { waitUntil: 'load' });
    const product = await page.evaluate(() => document.querySelector('a.o_ocd_product')?.getAttribute('href'));
    if (product) {
        paths.push(product);
        await page.goto(`${BASE}${product}`, { waitUntil: 'load' });
        const boutique = await page.evaluate(() => document.querySelector('a[href^="/ocd/boutique/"]')?.getAttribute('href'));
        if (boutique) {
            paths.push(boutique.split('?')[0]);
        }
    }
    for (const path of paths) {
        const response = await page.goto(`${BASE}${path}`, { waitUntil: 'load' });
        if (!response || response.status() >= 400) {
            continue;  // a module not installed in this base
        }
        await page.waitForTimeout(600);
        const size = `site ${path} ${width}x${height}`;
        const info = await page.evaluate(() => {
            const shown = (el) => el && el.getBoundingClientRect().height > 0 && getComputedStyle(el).display !== 'none';
            const h1 = [...document.querySelectorAll('#wrapwrap h1')].find(shown);
            const bar = document.querySelector('.o_ocd_header_title');
            const nav = document.querySelector('.o_ocd_nav');
            return {
                over: document.documentElement.scrollWidth - innerWidth,
                h1: h1 ? parseFloat(getComputedStyle(h1).fontSize) : 0,
                bar: shown(bar) ? bar.getBoundingClientRect().height / parseFloat(getComputedStyle(bar).fontSize) : 0,
                nav: shown(nav) ? nav.getBoundingClientRect().height : 0,
            };
        });
        check(info.over <= 0, `${size}: nothing wider than the screen (${info.over}px)`);
        check(info.h1 <= 27, `${size}: the title of the page at a phone size (${info.h1}px)`);
        check(info.bar < 1.8, `${size}: the title of the bar on one line (${info.bar.toFixed(1)} lines)`);
        check(info.nav <= 64, `${size}: the bar at the bottom low (${Math.round(info.nav)}px)`);
    }
    await context.close();
}

// The screens of the team on a phone and a tablet (chantier 25): nothing wider than the screen, no
// chat bubbles of Odoo over a phone screen, on a phone no card cut to the height of the screen
// (« To check »: one column open, its cards whole; « Dispatch »: one step, its parcels whole)
const TEAM_SCREENS = {
    dashboard: 'ocd_live.ocd_live_dashboard_action',
    planning: 'ocd_live.ocd_live_planning_action',
    verification: 'ocd_live.ocd_live_verification_action',
    automations: 'ocd_live.ocd_live_automations_action',
    settings: 'ocd_live.ocd_live_settings_action',
    regie: 'ocd_live_shop.ocd_live_regie_action',
    dispatch: 'ocd_live_shop.ocd_live_dispatch_action',
    orders: 'ocd_live_shop.ocd_live_orders_action',
    couriers: 'ocd_live_shop.ocd_live_couriers_action',
    inbox: 'ocd_live_whatsapp.ocd_whatsapp_inbox_action',
};
const TEAM_SIZES = [[390, 844], [450, 800], [900, 1000]];

async function team(browser, [width, height]) {
    const phone = width < 768;
    const context = await browser.newContext({ viewport: { width, height }, locale: 'fr-FR', isMobile: phone, hasTouch: phone });
    const page = await context.newPage();
    await page.goto(`${BASE}/web/login`, { waitUntil: 'load' });
    await page.fill('input[name="login"]', LOGIN);
    await page.fill('input[name="password"]', PASSWORD);
    await page.press('input[name="password"]', 'Enter');
    await page.waitForSelector('.o_main_navbar', { timeout: 60000 });
    for (const [name, action] of Object.entries(TEAM_SCREENS)) {
        const response = await page.goto(`${BASE}/odoo/action-${action}`, { waitUntil: 'load' });
        if (!response || response.status() >= 400) {
            continue;  // a module not installed in this base
        }
        await page.waitForTimeout(2500);
        const size = `team ${name} ${width}x${height}`;
        const info = await page.evaluate(() => {
            const bubbles = document.querySelector('.o-mail-ChatHub-bubbles');
            // the column shown scrolls inside itself: its cards are cut to the height of the screen
            const cut = [...document.querySelectorAll('.o_ocd_verification_open, .o_ocd_dispatch_column_on, .o_ocd_regie_live, .o_ocd_orders_scroll, .o_ocd_auto_rows')]
                .filter((pane) => pane.offsetParent !== null && pane.scrollHeight > pane.clientHeight + 1);
            return {
                over: document.documentElement.scrollWidth - innerWidth,
                bubbles: !!bubbles && bubbles.offsetParent !== null && bubbles.getBoundingClientRect().height > 0,
                cut: cut.length,
            };
        });
        check(info.over <= 0, `${size}: nothing wider than the screen (${info.over}px)`);
        if (phone) {
            check(!info.bubbles, `${size}: no chat bubbles of Odoo over the screen`);
            check(!info.cut, `${size}: no card cut (${info.cut})`);
        }
    }
    await context.close();
}

(async () => {
    const browser = await chromium.launch();
    for (const size of SITE_SIZES) {
        await feed(browser, size);
        await home(browser, size);
        await country(browser, size);
    }
    if (SPACE_LINK) {
        for (const size of [[390, 844], [820, 1180], [1440, 900]]) {
            await space(browser, size);
        }
        const large = spaceEntries[1440] || [];
        for (const width of [390, 820]) {
            const missing = large.filter((href) => !(spaceEntries[width] || []).includes(href));
            check(!missing.length, `my space ${width}: every entry of the computer ${missing.join(' ')}`);
        }
    }
    for (const size of BACK_SIZES) {
        await board(browser, size);
    }
    for (const size of TEAM_SIZES) {
        await team(browser, size);
    }
    for (const size of [[390, 844], [450, 800]]) {
        await sitePhone(browser, size);
    }
    await browser.close();
    console.log(failures.length ? `${failures.length} rule(s) broken` : 'Every rule holds.');
    process.exit(failures.length ? 1 : 0);
})();
