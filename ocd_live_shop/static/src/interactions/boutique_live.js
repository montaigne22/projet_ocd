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
        this.nameEl = this.el.querySelector(".o_ocd_live_shop_on_screen");
    }

    start() {
        this.timer = setInterval(() => this.refresh(), REFRESH_MS);
    }

    async refresh() {
        const product = await this.waitFor(rpc(`/ocd/boutique/${this.vendorId}/live`, {}));
        if (this.nameEl) {
            this.nameEl.textContent = product.name || "-";
        }
    }

    destroy() {
        clearInterval(this.timer);
    }
}

registry.category("public.interactions").add("ocd_live_shop.boutique_live", OcdBoutiqueLive);
