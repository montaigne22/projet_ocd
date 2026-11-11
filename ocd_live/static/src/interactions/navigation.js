import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// Pages that always load normally: back office, payment and accounts of Odoo, files, and the
// steps that pay or confirm (their scripts are not those of the other pages)
const FULL_LOAD = new RegExp(
    "^/(?:[a-z]{2}(?:_[A-Z]{2})?/)?" +
        "(?:odoo|web|payment|my|website|report|shop/(?:checkout|payment|confirmation|address)|" +
        "reserver/(?:confirmer|payer)|ocd/colis)(?:[/?#]|$)"
);
// The page loaded when the finger touches a link is kept a few seconds for the tap
const PREFETCH_MS = 8000;
// The skeleton appears only when the page takes time: no flash for a quick page
const SKELETON_DELAY_MS = 90;

/**
 * The vendors and the couriers known on this browser go from page to page without reloading
 * them (their space, their parcels, the menu): a tap on a link shows at once a skeleton of the
 * page, the page is loaded in the background, then only the content changes; the address, the
 * back button and the title follow. Anything unusual (another layout, other scripts, an error,
 * no network) loads the page normally. The forms are sent normally.
 */
export class OcdNavigation extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".o_ocd_app[data-ocd-fast]";

    setup() {
        this.pages = new Map();
        this.current = null;
        // The address of the page shown: going back to it (an overlay closed) changes nothing
        this.shownUrl = this.pageUrl();
        if ("scrollRestoration" in history) {
            history.scrollRestoration = "manual";
        }
        this.saveState();
    }

    start() {
        this.addListener(document, "click", this.onClick);
        this.addListener(document, "pointerdown", this.onPointerDown, { passive: true });
        this.addListener(window, "popstate", this.onPopState);
        // A page that changes its own address (the chosen colour, the live on screen)
        this.addListener(document, "ocd-url-change", () => (this.shownUrl = this.pageUrl()));
    }

    pageUrl() {
        return window.location.href.split("#")[0];
    }

    get app() {
        return document.querySelector(".o_ocd_app");
    }

    /** The entry of the history of this page knows it is ours and where the page was read. */
    saveState() {
        history.replaceState({ ...(history.state || {}), ocdNavigation: true, scroll: window.scrollY }, "");
    }

    /** The links that change page without reloading it, the others load normally. */
    fastUrl(link) {
        if (!link || !this.app?.hasAttribute("data-ocd-fast") || !link.closest(".o_ocd_app")) {
            return null;
        }
        const href = link.getAttribute("href") || "";
        if (
            !href ||
            href.startsWith("#") ||
            (link.target && link.target !== "_self") ||
            link.hasAttribute("download") ||
            link.closest("[data-ocd-full], .o_ocd_lang")
        ) {
            return null;
        }
        const url = new URL(link.href, window.location.href);
        if (url.origin !== window.location.origin || FULL_LOAD.test(url.pathname)) {
            return null;
        }
        if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
            return null; // a place on this page
        }
        return url;
    }

    onPointerDown(ev) {
        if (ev.button === 0) {
            const url = this.fastUrl(ev.target.closest("a[href]"));
            if (url) {
                this.load(url.href);
            }
        }
    }

    onClick(ev) {
        if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) {
            return;
        }
        const url = this.fastUrl(ev.target.closest("a[href]"));
        if (url) {
            ev.preventDefault();
            this.saveState();
            this.go(url, { push: true });
        }
    }

    onPopState(ev) {
        if (ev.state?.ocdNavigation && this.pageUrl() !== this.shownUrl) {
            this.go(new URL(window.location.href), { push: false, scroll: ev.state.scroll || 0, fresh: true });
        }
    }

    /** The page at `href`, loaded once for the touch and the tap that follows. */
    load(href, { fresh = false } = {}) {
        const key = href.split("#")[0];
        const known = this.pages.get(key);
        if (!fresh && known && Date.now() - known.time < PREFETCH_MS) {
            return known.promise;
        }
        const promise = fetch(key, {
            credentials: "same-origin",
            headers: { "X-OCD-Navigation": "1" },
        }).then(async (response) => ({
            ok: response.ok,
            url: response.url || key,
            html: (response.headers.get("content-type") || "").includes("text/html") ? await response.text() : null,
        }));
        this.pages.set(key, { promise, time: Date.now() });
        promise.catch(() => this.pages.delete(key));
        return promise;
    }

    async go(url, { push, scroll = 0, fresh = false }) {
        const token = (this.current = {});
        const app = this.app;
        const timer = setTimeout(() => this.showSkeleton(app, url), SKELETON_DELAY_MS);
        let page;
        try {
            page = await this.load(url.href, { fresh });
        } catch {
            page = null;
        }
        clearTimeout(timer);
        if (this.isDestroyed || this.current !== token) {
            return; // another tap came after this one
        }
        this.pages.clear();
        const doc = page?.ok && page.html ? new DOMParser().parseFromString(page.html, "text/html") : null;
        const finalUrl = new URL(page?.url || url.href);
        finalUrl.hash = url.hash;
        if (!this.canSwap(doc)) {
            // Error, no network, another layout or other scripts: the page loads normally
            if (push) {
                window.location.assign(finalUrl.href);
            } else {
                window.location.reload();
            }
            return;
        }
        this.swap(app, doc, finalUrl, push);
        const target = url.hash && document.getElementById(decodeURIComponent(url.hash.slice(1)));
        if (target) {
            target.scrollIntoView();
        } else {
            window.scrollTo(0, scroll);
        }
    }

    /** A page that can replace this one: the layout of OCD Live, the same scripts and styles. */
    canSwap(doc) {
        const app = doc?.querySelector(".o_ocd_app");
        if (!app || app.querySelector("script:not([type='application/ld+json']):not([type='application/json'])")) {
            return false;
        }
        const assets = (root) =>
            new Set(
                [...root.querySelectorAll("script[src], link[rel='stylesheet'][href]")].map(
                    (el) => el.getAttribute("src") || el.getAttribute("href")
                )
            );
        const mine = assets(document);
        return [...assets(doc)].every((asset) => mine.has(asset));
    }

    swap(oldApp, doc, url, push) {
        const service = this.services["public.interactions"];
        const newApp = document.importNode(doc.querySelector(".o_ocd_app"), true);
        service.stopInteractions(oldApp);
        oldApp.replaceWith(newApp);
        document.title = doc.title;
        document.documentElement.lang = doc.documentElement.lang;
        if (doc.documentElement.dataset.mainObject) {
            document.documentElement.dataset.mainObject = doc.documentElement.dataset.mainObject;
        }
        // The address first: the scripts of the new page may change it again (step of a booking)
        if (push) {
            history.pushState({ ocdNavigation: true, scroll: 0 }, "", url.href);
        } else if (url.href !== window.location.href) {
            history.replaceState({ ...(history.state || {}), ocdNavigation: true }, "", url.href);
        }
        this.shownUrl = this.pageUrl();
        service.startInteractions(newApp);
        // Screen readers: the new page starts at its title
        const heading = newApp.querySelector("h1") || newApp.querySelector("main");
        if (heading) {
            heading.setAttribute("tabindex", "-1");
            heading.focus({ preventScroll: true });
        }
    }

    /** Grey blocks in the shape of a page, under the header and above the menu, which stay. */
    showSkeleton(app, url) {
        if (!app?.isConnected || app.classList.contains("o_ocd_loading")) {
            return;
        }
        app.classList.add("o_ocd_loading");
        app.setAttribute("aria-busy", "true");
        for (const link of app.querySelectorAll(".o_ocd_nav a, .o_ocd_topnav a")) {
            const on = new URL(link.href, window.location.href).pathname === url.pathname;
            link.classList.toggle("o_ocd_on", on);
        }
        const skeleton = document.createElement("div");
        skeleton.className = "o_ocd_frame o_ocd_narrow o_ocd_skeleton";
        skeleton.setAttribute("aria-hidden", "true");
        const main = document.createElement("div");
        main.className = "o_ocd_main";
        for (const kind of ["title", "line", "chips", "card", "card", "card"]) {
            const block = document.createElement("span");
            block.className = `o_ocd_sk o_ocd_sk_${kind}`;
            main.append(block);
        }
        skeleton.append(main);
        const header = app.querySelector(":scope > .o_ocd_header");
        if (header) {
            header.after(skeleton);
        } else {
            app.prepend(skeleton);
        }
    }
}

registry.category("public.interactions").add("ocd_live.navigation", OcdNavigation);
