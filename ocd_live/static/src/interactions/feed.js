import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const NEW_LIVES_DELAY = 60000;
const LOAD_AHEAD = 3; // cards still to see when the next ones are asked

/**
 * Feed of the lives, one card per screen (like TikTok): the cards snap while the person swipes,
 * the next ones are loaded before the end, the bar shows the country of the card on screen and
 * the address keeps the card (back or reload come back to it). Arrow keys and Page Up/Down go
 * from card to card. Without JavaScript, the page and its « See more lives » link still work.
 */
export class OcdLiveFeed extends Interaction {
    static selector = ".o_ocd_feed_wrap";
    dynamicContent = {
        ".o_ocd_feed": { "t-on-keydown": this.onKey },
        ".o_ocd_feed_chip": { "t-on-click": this.onChip },
        ".o_ocd_feed_new": { "t-on-click": this.showNew },
        ".o_ocd_feed_top_link": { "t-on-click": this.backToTop },
    };

    setup() {
        this.scrollerEl = this.el.querySelector(".o_ocd_feed");
        this.barEl = this.el.querySelector(".o_ocd_feed_bar");
        this.first = this.el.dataset.first || "";
        this.next = this.el.dataset.next === "" ? null : Number(this.el.dataset.next);
        this.since = this.el.dataset.since;
        this.loading = false;
        this.activeKey = null;
    }

    start() {
        this.el.querySelector(".o_ocd_feed_more")?.remove(); // loaded while scrolling
        this.fit();
        this.addListener(window, "resize", () => this.fit());
        // Not a dynamic content: a scroll must not refresh the page content
        this.addListener(this.scrollerEl, "scroll", () => this.onScroll(), { passive: true });
        this.observer = new IntersectionObserver((entries) => this.onVisible(entries), {
            root: this.scrollerEl,
            threshold: 0.6,
        });
        this.cards().forEach((card) => this.observer.observe(card));
        this.restore();
        this.waitForTimeout(() => this.checkNew(), NEW_LIVES_DELAY);
    }

    destroy() {
        this.observer?.disconnect();
    }

    cards() {
        return [...this.scrollerEl.querySelectorAll(".o_ocd_feed_card")];
    }

    /** The feed fills the screen between the bar and the menu at the bottom. */
    fit() {
        const top = this.scrollerEl.getBoundingClientRect().top + window.scrollY;
        const bottom = document.querySelector(".o_ocd_bottom")?.offsetHeight || 0;
        const height = Math.max(360, window.innerHeight - top - bottom);
        this.scrollerEl.style.height = `${height}px`;
    }

    restore() {
        const key = new URLSearchParams(window.location.search).get("live");
        const card = key && this.scrollerEl.querySelector(`[data-key="${CSS.escape(key)}"]`);
        if (card) {
            this.scrollerEl.scrollTop = card.offsetTop;
        }
    }

    onVisible(entries) {
        for (const entry of entries) {
            if (entry.isIntersecting) {
                this.activate(entry.target);
            }
        }
    }

    activate(card) {
        if (card.dataset.key === this.activeKey) {
            return;
        }
        this.activeKey = card.dataset.key;
        const country = card.dataset.country;
        if (country) {
            for (const chip of this.barEl?.querySelectorAll(".o_ocd_feed_chip") || []) {
                const on = chip.dataset.country === country;
                chip.classList.toggle("o_ocd_on", on);
                if (on) {
                    chip.setAttribute("aria-current", "true");
                    chip.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
                } else {
                    chip.removeAttribute("aria-current");
                }
            }
        }
        const url = new URL(window.location.href);
        url.searchParams.set("live", this.activeKey);
        if (this.first) {
            url.searchParams.set("pays", this.first);
        }
        url.searchParams.delete("page");
        window.history.replaceState(window.history.state, "", url);
        const cards = this.cards();
        if (cards.length - cards.indexOf(card) <= LOAD_AHEAD) {
            this.load();
        }
    }

    onScroll() {
        const { scrollTop, clientHeight, scrollHeight } = this.scrollerEl;
        if (scrollHeight - scrollTop - clientHeight < clientHeight * LOAD_AHEAD) {
            this.load();
        }
    }

    async load() {
        if (this.loading || this.next === null) {
            return;
        }
        this.loading = true;
        try {
            const result = await this.waitFor(rpc("/lives/flux", { offset: this.next, pays: this.first }));
            const holder = document.createElement("div");
            holder.innerHTML = result.html;
            const known = new Set(this.cards().map((card) => card.dataset.key));
            for (const card of holder.querySelectorAll(".o_ocd_feed_card")) {
                if (known.has(card.dataset.key)) {
                    continue; // the feed changed between two pages: no card twice
                }
                this.scrollerEl.appendChild(card);
                this.services["public.interactions"].startInteractions(card);
                this.observer.observe(card);
            }
            this.next = result.next;
        } catch {
            // Network hiccup: asked again at the next scroll
        } finally {
            this.loading = false;
        }
    }

    goTo(offset) {
        const cards = this.cards();
        const index = cards.findIndex((card) => card.dataset.key === this.activeKey);
        const target = cards[Math.min(Math.max(index + offset, 0), cards.length - 1)];
        if (target) {
            target.scrollIntoView({ block: "start", behavior: this.motion() });
            target.focus({ preventScroll: true });
        }
    }

    motion() {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    }

    onKey(ev) {
        if (ev.target.closest("input, select, textarea, summary")) {
            return;
        }
        const moves = { ArrowDown: 1, PageDown: 1, ArrowUp: -1, PageUp: -1 };
        if (ev.key in moves) {
            ev.preventDefault();
            this.goTo(moves[ev.key]);
        }
    }

    /** A country of the bar: its first card when it is already in the feed, else the feed of
     * this country first (the link of the chip). */
    onChip(ev) {
        const country = ev.currentTarget.dataset.country;
        const start = this.scrollerEl.querySelector(`[data-country-start="${CSS.escape(country)}"]`)
            || (country === this.first ? this.cards()[0] : null);
        if (start) {
            ev.preventDefault();
            start.scrollIntoView({ block: "start", behavior: this.motion() });
        }
    }

    backToTop(ev) {
        ev.preventDefault();
        this.scrollerEl.scrollTo({ top: 0, behavior: this.motion() });
    }

    async checkNew() {
        try {
            const { count } = await this.waitFor(rpc("/lives/nouveaux", { since: this.since }));
            const pill = this.el.querySelector(".o_ocd_feed_new");
            if (count && pill) {
                pill.querySelector(".o_ocd_feed_new_count").textContent = count;
                pill.hidden = false;
                return;
            }
        } catch {
            // asked again later
        }
        this.waitForTimeout(() => this.checkNew(), NEW_LIVES_DELAY);
    }

    showNew() {
        const url = new URL(window.location.href);
        url.searchParams.delete("live");
        window.location.assign(url);
    }
}

registry.category("public.interactions").add("ocd_live.feed", OcdLiveFeed);
