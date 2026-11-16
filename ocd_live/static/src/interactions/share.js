import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const SHOWN_MS = 4000;
// How long a tap waits for images still loading: a phone opens its share sheet only right after
// the tap, so the images are fetched before (the menu opened, the finger on the button)
const WAIT_IMAGES_MS = 2500;

/**
 * A "Share" button: opens the share sheet of the phone, or copies the link when the browser has
 * none and says so.
 * - data-url: the page to share; data-text: a line with it (the name and the price);
 * - data-image / data-images (JSON list): images shared as files when the phone can (the
 *   WhatsApp status takes an image), else the link alone;
 * - data-track: an address told once the sharing is done (the first steps of a vendor).
 */
export class OcdLiveShare extends Interaction {
    static selector = ".o_ocd_share[data-url]";
    dynamicContent = {
        _root: {
            "t-on-click": this.share,
            "t-on-pointerdown": this.prepare,
            "t-on-focus": this.prepare,
        },
    };

    setup() {
        this.files = null;
        this.preparing = null;
    }

    start() {
        const details = this.el.closest("details");
        if (details) {
            this.addListener(details, "toggle", () => details.open && this.prepare());
        }
        if (this.el.dataset.images) {
            this.prepare(); // a page of images (the catalogue): they are shown already
        }
    }

    sources() {
        if (this.el.dataset.images) {
            try {
                return JSON.parse(this.el.dataset.images);
            } catch {
                return [];
            }
        }
        return this.el.dataset.image ? [this.el.dataset.image] : [];
    }

    prepare() {
        const sources = this.sources();
        if (this.preparing || !sources.length || !navigator.canShare) {
            return this.preparing;
        }
        const fetchFile = (src, index) =>
            fetch(src)
                .then((response) => (response.ok ? response.blob() : null))
                .then((blob) => blob && new File([blob], `ocd-live-${index + 1}.jpg`, { type: blob.type || "image/jpeg" }))
                .catch(() => null);
        this.preparing = Promise.all(sources.map(fetchFile)).then((files) => {
            this.files = files.filter(Boolean);
            return this.files;
        });
        return this.preparing;
    }

    track() {
        if (this.el.dataset.track && navigator.sendBeacon) {
            navigator.sendBeacon(this.el.dataset.track);
        }
    }

    async share() {
        const url = this.el.dataset.url;
        const text = this.el.dataset.text || "";
        if (navigator.share) {
            try {
                let files = this.files;
                if (!files && this.preparing) {
                    const late = new Promise((resolve) => setTimeout(() => resolve(null), WAIT_IMAGES_MS));
                    files = await this.waitFor(Promise.race([this.preparing, late]));
                }
                if (files?.length && navigator.canShare({ files })) {
                    // With images, some apps keep only the text: the link goes in it
                    await this.waitFor(navigator.share({ files, text: [text, url].filter(Boolean).join("\n") }));
                    this.track();
                    return;
                }
                const data = { url, title: document.title };
                if (text) {
                    data.text = text;
                }
                await this.waitFor(navigator.share(data));
                this.track();
                return;
            } catch (error) {
                if (error?.name === "AbortError") {
                    return;
                }
            }
        }
        try {
            await this.waitFor(navigator.clipboard.writeText([text, url].filter(Boolean).join(" ")));
        } catch {
            window.prompt("", url);
            return;
        }
        this.track();
        const done = document.querySelector(".o_ocd_share_done");
        if (done) {
            done.hidden = false;
            this.waitForTimeout(() => (done.hidden = true), SHOWN_MS);
        }
    }
}

registry.category("public.interactions").add("ocd_live.share", OcdLiveShare);
