import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const NEW_LIVES_DELAY = 60000;
const LOAD_AHEAD = 3; // cards still to see when the next ones are asked
const SLIDE_DELAY = 4500; // the carousel of the products turns by itself until the person touches it

/**
 * Feed of the lives, one card per screen (like TikTok): the cards snap while the person swipes,
 * the next ones are loaded before the end, the bar shows the country of the card on screen and
 * the address keeps the card (back or reload come back to it). Arrow keys and Page Up/Down go
 * from card to card. Without JavaScript, the page and its « See more lives » link still work.
 *
 * The media of the card on screen comes alive: its short video plays without sound (a tap pauses
 * it, the speaker turns the sound on for the next ones too), the carousel of its products turns
 * by itself until the person touches it. Neither when the person asked for less motion or to
 * save data: the video then waits for a tap.
 */
export class OcdLiveFeed extends Interaction {
    static selector = ".o_ocd_feed_wrap";
    dynamicContent = {
        ".o_ocd_feed": { "t-on-keydown": this.onKey, "t-on-click": this.onMediaClick },
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
        this.sound = false;
        this.slideRun = 0;
        this.autoplay = !this.reducedMotion() && !navigator.connection?.saveData;
    }

    start() {
        this.el.querySelector(".o_ocd_feed_more")?.remove(); // loaded while scrolling
        this.fit();
        this.addListener(window, "resize", () => this.fit());
        // Not a dynamic content: a scroll must not refresh the page content
        this.addListener(this.scrollerEl, "scroll.noUpdate", (ev) => this.onScroll(ev), { passive: true, capture: true });
        // The videos and the carousels say when they play, pause or are touched (captured: these
        // events do not bubble up to the feed)
        for (const event of ["playing", "pause", "ended"]) {
            this.addListener(this.scrollerEl, `${event}.noUpdate`, (ev) => this.onVideoState(ev), { capture: true });
        }
        this.addListener(this.scrollerEl, "pointerdown.noUpdate", (ev) => this.onSlidesTouch(ev), { passive: true });
        this.addListener(this.scrollerEl, "wheel.noUpdate", (ev) => this.onSlidesTouch(ev), { passive: true });
        this.addListener(document, "visibilitychange.noUpdate", () => this.onVisibility());
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
        for (const video of this.scrollerEl.querySelectorAll("video")) {
            video.pause();
        }
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
        document.dispatchEvent(new CustomEvent("ocd-url-change"));
        const cards = this.cards();
        this.liven(card, cards[cards.indexOf(card) + 1]);
        if (cards.length - cards.indexOf(card) <= LOAD_AHEAD) {
            this.load();
        }
    }

    onScroll(ev) {
        if (ev.target !== this.scrollerEl) {
            if (ev.target.classList?.contains("o_ocd_feed_slides")) {
                this.showSlide(ev.target);
            }
            return;
        }
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

    // === MEDIA OF THE CARD ON SCREEN === //

    reducedMotion() {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    /** The card on screen plays its video and turns its carousel; the others stop. The video of
     * the next card is prepared, so that it starts at once. */
    liven(card, nextCard) {
        for (const video of this.scrollerEl.querySelectorAll("video")) {
            if (!card.contains(video) && !video.paused) {
                video.pause();
            }
        }
        const video = card.querySelector(".o_ocd_feed_video");
        if (video && this.autoplay && !video.dataset.stopped) {
            this.play(video);
        }
        const nextVideo = nextCard?.querySelector(".o_ocd_feed_video");
        if (nextVideo && nextVideo.preload === "none") {
            nextVideo.preload = "metadata";
        }
        this.turnSlides(card);
    }

    play(video) {
        video.muted = !this.sound;
        video.play()?.catch(() => {
            // The browser refuses the sound before a tap: without sound then
            if (!video.muted) {
                video.muted = true;
                this.setSound(false);
                video.play()?.catch(() => {});
            }
        });
    }

    onMediaClick(ev) {
        const soundEl = ev.target.closest(".o_ocd_feed_sound");
        if (soundEl) {
            this.setSound(!this.sound);
            const video = soundEl.closest(".o_ocd_feed_media").querySelector("video");
            if (video) {
                video.muted = !this.sound;
                if (video.paused) {
                    delete video.dataset.stopped;
                    this.play(video);
                }
            }
            return;
        }
        const playEl = ev.target.closest(".o_ocd_feed_play, .o_ocd_feed_video");
        if (playEl) {
            const video = playEl.closest(".o_ocd_feed_media").querySelector("video");
            if (video.paused) {
                delete video.dataset.stopped;
                this.play(video);
            } else {
                video.dataset.stopped = "1"; // paused by the person: it stays paused
                video.pause();
            }
            return;
        }
        const arrowEl = ev.target.closest(".o_ocd_feed_arrow");
        if (arrowEl) {
            const slidesEl = arrowEl.closest(".o_ocd_feed_media").querySelector(".o_ocd_feed_slides");
            slidesEl.dataset.touched = "1";
            this.moveSlide(slidesEl, arrowEl.classList.contains("o_ocd_feed_prev") ? -1 : 1);
        }
    }

    setSound(on) {
        this.sound = on;
        for (const button of this.scrollerEl.querySelectorAll(".o_ocd_feed_sound")) {
            button.setAttribute("aria-pressed", on ? "true" : "false");
        }
    }

    onVideoState(ev) {
        const video = ev.target;
        if (!(video instanceof HTMLVideoElement)) {
            return;
        }
        const playing = ev.type === "playing";
        const mediaEl = video.closest(".o_ocd_feed_media");
        mediaEl?.classList.toggle("o_ocd_playing", playing);
        const button = mediaEl?.querySelector(".o_ocd_feed_play");
        if (button) {
            button.setAttribute("aria-label", playing ? _t("Pause the video") : _t("Play the video"));
        }
    }

    onVisibility() {
        const card = this.activeKey && this.scrollerEl.querySelector(`[data-key="${CSS.escape(this.activeKey)}"]`);
        const video = card?.querySelector(".o_ocd_feed_video");
        if (!video) {
            return;
        }
        if (document.hidden) {
            video.pause();
        } else if (this.autoplay && !video.dataset.stopped) {
            this.play(video);
        }
    }

    slideWidth(slidesEl) {
        return slidesEl.clientWidth || 1;
    }

    /** The dots and the arrows follow the slide on screen. */
    showSlide(slidesEl) {
        const count = slidesEl.children.length;
        const index = Math.round(slidesEl.scrollLeft / this.slideWidth(slidesEl));
        const mediaEl = slidesEl.closest(".o_ocd_feed_media");
        mediaEl.querySelectorAll(".o_ocd_feed_dots i").forEach((dot, i) => dot.classList.toggle("o_ocd_on", i === index));
        const prev = mediaEl.querySelector(".o_ocd_feed_prev");
        const next = mediaEl.querySelector(".o_ocd_feed_next");
        if (prev) {
            prev.disabled = index <= 0;
        }
        if (next) {
            next.disabled = index >= count - 1;
        }
    }

    moveSlide(slidesEl, offset, wrap = false) {
        const count = slidesEl.children.length;
        let index = Math.round(slidesEl.scrollLeft / this.slideWidth(slidesEl)) + offset;
        if (wrap) {
            index = (index + count) % count;
        }
        index = Math.min(Math.max(index, 0), count - 1);
        slidesEl.scrollTo({ left: index * this.slideWidth(slidesEl), behavior: this.motion() });
    }

    /** The carousel of the card on screen turns by itself, until the person touches it. */
    turnSlides(card) {
        const run = ++this.slideRun;
        const slidesEl = card.querySelector(".o_ocd_feed_slides");
        if (!slidesEl || slidesEl.children.length < 2 || this.reducedMotion()) {
            return;
        }
        this.showSlide(slidesEl);
        const turn = () => {
            if (run !== this.slideRun || slidesEl.dataset.touched || document.hidden) {
                if (run === this.slideRun && !slidesEl.dataset.touched) {
                    this.waitForTimeout(turn, SLIDE_DELAY); // hidden page: later
                }
                return;
            }
            this.moveSlide(slidesEl, 1, true);
            this.waitForTimeout(turn, SLIDE_DELAY);
        };
        this.waitForTimeout(turn, SLIDE_DELAY);
    }

    onSlidesTouch(ev) {
        const slidesEl = ev.target.closest?.(".o_ocd_feed_slides");
        if (slidesEl) {
            slidesEl.dataset.touched = "1";
        }
    }

    goTo(offset) {
        const cards = this.cards();
        const index = cards.findIndex((card) => card.dataset.key === this.activeKey);
        const target = cards[Math.min(Math.max(index + offset, 0), cards.length - 1)];
        if (target) {
            // The feed only: scrollIntoView would also move the page under the bar
            this.scrollerEl.scrollTo({ top: target.offsetTop, behavior: this.motion() });
            target.focus({ preventScroll: true });
        }
    }

    motion() {
        return this.reducedMotion() ? "auto" : "smooth";
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
            this.scrollerEl.scrollTo({ top: start.offsetTop, behavior: this.motion() });
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
