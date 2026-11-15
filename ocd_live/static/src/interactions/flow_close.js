import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * The cross that leaves a booking (header of its steps, on the phone). A form of the step the
 * vendor already filled in (their name, their phone...) asks before leaving, so that a wrong
 * touch does not lose it; an untouched step leaves at once. Without JavaScript the cross is a
 * plain link to the home page.
 */
export class OcdFlowClose extends Interaction {
    static selector = ".o_ocd_flow_close";
    dynamicContent = {
        _root: { "t-on-click": this.onClick },
        _document: {
            "t-on-input": this.onTyped,
            "t-on-change": this.onTyped,
        },
    };

    setup() {
        this.typed = false;
    }

    onTyped(ev) {
        // Only what the vendor types or chooses in a form of the page counts
        if (ev.target.closest?.("form") && ev.target.type !== "hidden") {
            this.typed = true;
        }
    }

    onClick(ev) {
        if (this.typed && !window.confirm(_t("Leave the booking? What you typed will be lost."))) {
            ev.preventDefault();
        }
    }
}

registry.category("public.interactions").add("ocd_live.flow_close", OcdFlowClose);
