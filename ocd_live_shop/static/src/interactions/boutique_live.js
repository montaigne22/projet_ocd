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

/**
 * Replay: the moment touched is the one ordered with the button of the bottom.
 */
export class OcdReplayMoments extends Interaction {
    static selector = ".o_ocd_replay";
    dynamicContent = {
        ".o_ocd_moment_go": { "t-on-click": this.pick },
    };

    pick(ev) {
        const link = ev.currentTarget;
        for (const row of this.el.querySelectorAll(".o_ocd_moment")) {
            row.classList.toggle("o_ocd_on", row.contains(link));
        }
        const now = this.el.querySelector(".o_ocd_video_now");
        if (now) {
            now.textContent = link.dataset.time;
        }
        const cta = document.querySelector(".o_ocd_bottom_cta .o_ocd_cta");
        if (cta && link.dataset.orderUrl) {
            cta.href = link.dataset.orderUrl;
            cta.querySelector("span:last-child").textContent = link.dataset.orderLabel;
        }
    }
}

registry
    .category("public.interactions")
    .add("ocd_live_shop.boutique_live", OcdBoutiqueLive)
    .add("ocd_live_shop.replay_moments", OcdReplayMoments);
