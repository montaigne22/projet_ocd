import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const REFRESH_MS = 20000;

/**
 * During the live, shows the product the control room puts on screen. A light request every
 * 20 seconds keeps working on a weak network.
 */
export class OcdBoutiqueLive extends Interaction {
    static selector = ".o_ocd_live_shop_live";

    setup() {
        this.vendorId = parseInt(this.el.dataset.vendorId);
        this.card = this.el.querySelector(".o_ocd_onscreen");
    }

    start() {
        this.timer = setInterval(() => this.refresh(), REFRESH_MS);
    }

    async refresh() {
        let product;
        try {
            product = await this.waitFor(rpc(`/ocd/boutique/${this.vendorId}/live`, {}));
        } catch {
            return; // Network hiccup: ask again later
        }
        if (!this.card) {
            return;
        }
        this.card.classList.toggle("d-none", !product.id);
        if (!product.id) {
            return;
        }
        this.card.href = product.url;
        this.card.querySelector(".o_ocd_onscreen_name").textContent = product.name;
        this.card.querySelector(".o_ocd_onscreen_price").textContent = product.price;
        const photo = this.card.querySelector(".o_ocd_onscreen_photo");
        if (product.image) {
            photo.replaceChildren(Object.assign(document.createElement("img"), {
                src: product.image,
                alt: "",
                className: "o_ocd_photo_img",
            }));
        }
    }

    destroy() {
        clearInterval(this.timer);
    }
}

const YOUTUBE_API = "https://www.youtube.com/iframe_api";
const TIKTOK_PLAYER = "https://www.tiktok.com/player/v1/";
const TIKTOK_SILENT_MS = 5000;
let youtubeReady = null;

/** The API of the YouTube player, loaded once, on the first tap. */
function loadYoutube() {
    if (window.YT?.Player) {
        return Promise.resolve(window.YT);
    }
    if (!youtubeReady) {
        youtubeReady = new Promise((resolve, reject) => {
            const previous = window.onYouTubeIframeAPIReady;
            window.onYouTubeIframeAPIReady = () => {
                previous?.();
                resolve(window.YT);
            };
            const script = document.createElement("script");
            script.src = YOUTUBE_API;
            script.async = true;
            script.onerror = () => {
                youtubeReady = null;
                reject(new Error("YouTube unavailable"));
            };
            document.head.appendChild(script);
        });
    }
    return youtubeReady;
}

function clock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const rest = String(total % 60).padStart(2, "0");
    return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${String(minutes).padStart(2, "0")}:${rest}`;
}

/**
 * Replay: the video plays in the page (YouTube, TikTok, Facebook), loaded on the first tap. A
 * product touched, or its mark on the bar, goes to its moment; while the video plays, the
 * product on screen lights up and the button of the bottom orders it. Without a player (an
 * Instagram video, a link of another site, a player that does not answer), the links open the
 * video on its site, and the moment touched is still the one ordered.
 */
export class OcdReplayMoments extends Interaction {
    static selector = ".o_ocd_replay";
    dynamicContent = {
        ".o_ocd_replay_open": { "t-on-click": this.onPlay },
        ".o_ocd_moment_go": { "t-on-click": this.onMoment },
        ".o_ocd_player_mark": { "t-on-click": this.onMark },
    };

    setup() {
        const data = this.el.dataset;
        this.platform = data.platform || "";
        this.video = data.video || "";
        this.seek = Boolean(data.seek) && ["youtube", "tiktok", "facebook"].includes(this.platform);
        this.startAt = parseInt(data.start) || 0;
        this.total = parseInt(data.total) || 0;
        this.frameEl = this.el.querySelector(".o_ocd_player_frame");
        this.player = null; // YouTube player, or the iframe of TikTok and Facebook
        this.tiktokReady = false;
        this.silent = false;
        this.pending = null;
    }

    start() {
        this.addListener(window, "message", (ev) => this.onMessage(ev));
    }

    destroy() {
        clearInterval(this.ticker);
    }

    // === WHAT THE PERSON TOUCHES === //

    onPlay(ev) {
        if (!this.seek) {
            return; // opens the video on its site
        }
        ev.preventDefault();
        this.play(this.startAt);
    }

    onMoment(ev) {
        const link = ev.currentTarget;
        this.choose(link.closest(".o_ocd_moment"));
        if (!this.seek || (this.platform === "tiktok" && this.player && !this.tiktokReady && this.silent)) {
            return; // opens the video on its site
        }
        ev.preventDefault();
        this.play(parseInt(link.dataset.seconds) || 0);
        this.el.querySelector(".o_ocd_player")?.scrollIntoView({ block: "start", behavior: "smooth" });
    }

    onMark(ev) {
        const seconds = parseInt(ev.currentTarget.dataset.seconds) || 0;
        this.choose(this.momentAt(seconds));
        if (this.seek) {
            this.play(seconds);
        }
    }

    // === THE PRODUCT ON SCREEN === //

    momentAt(seconds) {
        let found = null;
        for (const row of this.el.querySelectorAll(".o_ocd_moment")) {
            if (parseInt(row.dataset.seconds) <= seconds + 1) {
                found = row;
            }
        }
        return found || this.el.querySelector(".o_ocd_moment");
    }

    choose(row) {
        if (!row || row.classList.contains("o_ocd_on")) {
            return;
        }
        for (const other of this.el.querySelectorAll(".o_ocd_moment")) {
            other.classList.toggle("o_ocd_on", other === row);
        }
        const link = row.querySelector(".o_ocd_moment_go");
        const cta = document.querySelector(".o_ocd_bottom_cta");
        if (cta && link?.dataset.orderUrl) {
            cta.href = link.dataset.orderUrl;
            const label = cta.querySelector("span:last-child");
            if (label) {
                label.textContent = link.dataset.orderLabel;
            }
        }
    }

    onTime(seconds, duration) {
        const total = duration || this.total;
        const fill = this.el.querySelector(".o_ocd_player_fill");
        if (fill && total) {
            fill.style.width = `${Math.min(100, (seconds / total) * 100)}%`;
        }
        const now = this.el.querySelector(".o_ocd_player_now");
        if (now) {
            now.textContent = clock(seconds);
        }
        this.choose(this.momentAt(seconds));
    }

    // === THE PLAYERS === //

    showFrame() {
        this.el.querySelector(".o_ocd_player")?.classList.add("o_ocd_playing");
    }

    play(seconds) {
        this.showFrame();
        this.onTime(seconds);
        if (this.platform === "youtube") {
            this.playYoutube(seconds);
        } else if (this.platform === "tiktok") {
            this.playTiktok(seconds);
        } else if (this.platform === "facebook") {
            this.playFacebook(seconds);
        }
    }

    async playYoutube(seconds) {
        if (this.player?.seekTo) {
            this.player.seekTo(seconds, true);
            this.player.playVideo();
            return;
        }
        if (this.player) {
            this.pending = seconds; // the player is being made
            return;
        }
        this.player = "loading";
        let YT;
        try {
            YT = await this.waitFor(loadYoutube());
        } catch {
            this.player = null;
            window.open(this.el.querySelector(".o_ocd_replay_open")?.href, "_blank", "noopener");
            return;
        }
        const holder = document.createElement("div");
        this.frameEl.replaceChildren(holder);
        this.player = new YT.Player(holder, {
            videoId: this.video,
            playerVars: { start: Math.floor(seconds), autoplay: 1, playsinline: 1, rel: 0, modestbranding: 1 },
            events: {
                onReady: (event) => {
                    if (this.pending !== null) {
                        event.target.seekTo(this.pending, true);
                        this.pending = null;
                    }
                    event.target.playVideo();
                    clearInterval(this.ticker);
                    this.ticker = setInterval(() => {
                        if (this.player?.getCurrentTime && this.player.getPlayerState?.() === 1) {
                            this.onTime(this.player.getCurrentTime(), this.player.getDuration?.());
                        }
                    }, 500);
                },
            },
        });
    }

    playTiktok(seconds) {
        if (!this.player) {
            const iframe = document.createElement("iframe");
            const params = "autoplay=1&controls=1&progress_bar=1&play_button=1&volume_control=1&timestamp=1&loop=0&rel=0&native_context_menu=0&closed_caption=1";
            iframe.src = `${TIKTOK_PLAYER}${encodeURIComponent(this.video)}?${params}`;
            iframe.allow = "autoplay; fullscreen; encrypted-media; picture-in-picture";
            iframe.title = this.el.querySelector("h1")?.textContent || "TikTok";
            this.frameEl.replaceChildren(iframe);
            this.player = iframe;
            this.pending = seconds;
            // A player that never answers: the moments open the video on TikTok
            this.waitForTimeout(() => {
                this.silent = !this.tiktokReady;
            }, TIKTOK_SILENT_MS);
            return;
        }
        if (!this.tiktokReady) {
            this.pending = seconds;
            return;
        }
        this.tiktokSend({ type: "seekTo", value: seconds });
        this.tiktokSend({ type: "play" });
    }

    tiktokSend(message) {
        this.player?.contentWindow?.postMessage({ ...message, "x-tiktok-player": true }, "*");
    }

    playFacebook(seconds) {
        // The player of Facebook starts at a second: going to a moment loads it from there
        const iframe = this.player || document.createElement("iframe");
        const href = encodeURIComponent(this.video);
        iframe.src = `https://www.facebook.com/plugins/video.php?href=${href}&show_text=false&autoplay=true&mute=0&t=${Math.floor(seconds)}`;
        iframe.allow = "autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share";
        iframe.allowFullscreen = true;
        iframe.title = this.el.querySelector("h1")?.textContent || "Facebook";
        if (!this.player) {
            this.frameEl.replaceChildren(iframe);
            this.player = iframe;
        }
    }

    onMessage(ev) {
        const data = ev.data;
        if (this.platform !== "tiktok" || !data || typeof data !== "object" || !data["x-tiktok-player"]) {
            return;
        }
        if (ev.source !== this.player?.contentWindow) {
            return;
        }
        if (data.type === "onPlayerReady") {
            this.tiktokReady = true;
            this.silent = false;
            if (this.pending) {
                this.tiktokSend({ type: "seekTo", value: this.pending });
            }
            this.tiktokSend({ type: "play" });
            this.pending = null;
        } else if (data.type === "onCurrentTime" && data.value) {
            this.onTime(data.value.currentTime || 0, data.value.duration || 0);
        }
    }
}

registry
    .category("public.interactions")
    .add("ocd_live_shop.boutique_live", OcdBoutiqueLive)
    .add("ocd_live_shop.replay_moments", OcdReplayMoments);
