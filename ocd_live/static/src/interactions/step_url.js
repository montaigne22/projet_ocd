import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * A step of the booking shown again after a form sent with an error (/reserver/confirmer,
 * /reserver/attente) takes the address of the step: reloading the page, going back or the phone
 * reopening the tab shows the step again, and not an address that only takes a form.
 */
export class OcdLiveStepUrl extends Interaction {
    static selector = ".o_ocd_app[data-ocd-url]";

    start() {
        const url = this.el.dataset.ocdUrl;
        if (url && window.location.pathname !== url) {
            window.history.replaceState(window.history.state, "", url);
        }
    }
}

registry.category("public.interactions").add("ocd_live.step_url", OcdLiveStepUrl);
