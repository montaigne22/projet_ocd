import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Payment page of OCD Live. The payment form is the one of Odoo; as in the design, the total
 * stands just above the payment button.
 */
export class OcdLivePay extends Interaction {
    static selector = ".o_ocd_pay";

    setup() {
        const total = this.el.querySelector(".o_ocd_payment + .o_ocd_total");
        const button = this.el.querySelector("button[name='o_payment_submit_button']");
        if (total && button) {
            button.parentElement.before(total);
        }
    }
}

registry.category("public.interactions").add("ocd_live.pay", OcdLivePay);
