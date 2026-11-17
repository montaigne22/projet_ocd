import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const STORAGE_KEY = "ocd_boutiques_seen";

/**
 * « Visits of your boutique » in the figures of the vendor (chantier 3): one per phone and per
 * day. The page itself is the same for everyone and kept in memory for the crowds of a live; the
 * visit is told by a small request once the page is shown, at most once a day per boutique on
 * this phone (the server checks it again).
 */
export class OcdBoutiqueVisit extends Interaction {
    static selector = ".o_ocd_vitrine[data-visit]";

    start() {
        const vendorId = this.el.dataset.visit;
        const today = new Date().toISOString().slice(0, 10);
        let seen = {};
        try {
            seen = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
        } catch {
            seen = {};
        }
        if (seen.day !== today) {
            seen = { day: today, ids: [] };
        }
        if (seen.ids.includes(vendorId)) {
            return;
        }
        seen.ids = [...seen.ids, vendorId].slice(-50);
        try {
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(seen));
        } catch {
            // Private browsing: the server still counts the phone once a day
        }
        const url = `/ocd/boutique/${encodeURIComponent(vendorId)}/vu`;
        if (!navigator.sendBeacon?.(url)) {
            fetch(url, { method: "POST", keepalive: true }).catch(() => {});
        }
    }
}

registry.category("public.interactions").add("ocd_live_shop.boutique_visit", OcdBoutiqueVisit);
