import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const SHOWN_MS = 4000;

/**
 * "Share" button of the header: opens the share sheet of the phone, or copies the link when
 * the browser has none and says so.
 */
export class OcdLiveShare extends Interaction {
    static selector = ".o_ocd_share[data-url]";
    dynamicContent = {
        _root: { "t-on-click": this.share },
    };

    async share() {
        const url = this.el.dataset.url;
        if (navigator.share) {
            try {
                await this.waitFor(navigator.share({ url, title: document.title }));
                return;
            } catch (error) {
                if (error?.name === "AbortError") {
                    return;
                }
            }
        }
        try {
            await this.waitFor(navigator.clipboard.writeText(url));
        } catch {
            window.prompt("", url);
            return;
        }
        const done = document.querySelector(".o_ocd_share_done");
        if (done) {
            done.hidden = false;
            this.waitForTimeout(() => (done.hidden = true), SHOWN_MS);
        }
    }
}

registry.category("public.interactions").add("ocd_live.share", OcdLiveShare);
