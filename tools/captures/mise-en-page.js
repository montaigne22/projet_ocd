// Layout check of the screens that grow with the data: the feed of the lives, the home page and
// « To check » of the back office. Fails (exit 1) when a rule is broken, at the sizes of a phone,
// a tablet, a laptop (1366 x 657) and large screens:
// - nothing wider than the page;
// - feed: no card cut, the cards wide enough for their product (tablet and up), « I am live »
//   above the cards on a large screen and at the bottom on a phone, a country picked brings its
//   band under the head;
// - home: only the countries with a live and the one of the visitor, then « All countries »;
// - the page of a country: its cards not cut, never one card stretched over the page;
// - « To check »: no column squeezed under 280 px, no card wider than its column, no empty
//   column on the board;
// - with OCD_SPACE_LINK (the personal link of a vendor of the demo): « My space » has every entry
//   of the computer on a phone and a tablet, no heading covered, no amount cut in « My figures ».
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
        };
    });
    const large = width >= 768;
    check(info.over <= 0, `${size}: nothing wider than the page (${info.over}px)`);
    check(!info.cut.length, `${size}: no card cut ${info.cut.join(' ')}`);
    if (large) {
        check(info.narrowest >= 320, `${size}: cards 320 px wide at least (${Math.round(info.narrowest)})`);
        check(info.smallestPhoto === null || info.smallestPhoto >= 120,
            `${size}: product photos 120 px wide at least (${Math.round(info.smallestPhoto)})`);
        check(info.ctaTop && !info.ctaBottom, `${size}: « I am live » above the cards, not over them`);
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
        check(info.ctaBottom && !info.ctaTop, `${size}: « I am live » at the bottom of the phone`);
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
    await browser.close();
    console.log(failures.length ? `${failures.length} rule(s) broken` : 'Every rule holds.');
    process.exit(failures.length ? 1 : 0);
})();
