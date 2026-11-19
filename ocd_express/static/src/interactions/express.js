import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * « New parcel »: what the sender receives, updated while they type (the money collected, the
 * delivery they pay, the collecting, what is left). The amount or the value is shown according
 * to « already paid ». Without JavaScript, the form works the same: the parcel shows the exact
 * amounts once created.
 */
export class OcdExpressParcelForm extends Interaction {
    static selector = ".o_ocd_ex_form";
    dynamicContent = {
        _root: { "t-on-change": this.update, "t-on-input": this.update },
    };

    start() {
        this.update();
    }

    money(amount) {
        const symbol = this.el.dataset.symbol || "";
        // As the amounts of the page: 15 000 F
        const text = String(Math.round(amount)).replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
        return this.el.dataset.position === "before" ? `${symbol} ${text}` : `${text} ${symbol}`;
    }

    read(name) {
        const input = this.el.querySelector(`[name='${name}']`);
        return parseFloat(((input && input.value) || "").replace(/[^\d]/g, "")) || 0;
    }

    update() {
        const prepaid = this.el.querySelector("input[name='prepaid']:checked")?.value === "1";
        const customerPays = this.el.querySelector("input[name='fee_by']:checked")?.value === "customer";
        const amountBox = this.el.querySelector(".o_ocd_ex_amount");
        const valueBox = this.el.querySelector(".o_ocd_ex_value");
        if (amountBox && valueBox) {
            amountBox.hidden = prepaid;
            valueBox.hidden = !prepaid;
        }
        // At a relay point (chantier 10): the price of the relay points
        const chosen = this.el.querySelector("select[name='place']")?.selectedOptions[0];
        const fee = parseFloat(chosen?.dataset.fee || this.el.dataset.fee) || 0;
        const rate = parseFloat(this.el.dataset.rate) || 0;
        const minimum = parseFloat(this.el.dataset.min) || 0;
        const goods = prepaid ? 0 : this.read("amount");
        const collecting = goods > 0 ? Math.min(Math.max((goods * rate) / 100, minimum), goods) : 0;
        const cod = goods + (customerPays ? fee : 0);
        const net = goods - (customerPays ? 0 : fee) - collecting;
        const set = (selector, text) => {
            const node = this.el.querySelector(selector);
            if (node) {
                node.textContent = text;
            }
        };
        set(".o_ocd_ex_sum_cod", this.money(cod));
        set(".o_ocd_ex_sum_fee", customerPays ? _t("paid by your customer") : `− ${this.money(fee)}`);
        set(".o_ocd_ex_sum_rate", collecting ? `− ${this.money(collecting)}` : _t("nothing"));
        if (!prepaid && !goods) {
            // Nothing typed yet: nothing to say
            set(".o_ocd_ex_sum_net", "-");
            return;
        }
        set(".o_ocd_ex_sum_net", net < 0 ? _t("You owe %s", this.money(-net)) : this.money(net));
    }
}

/**
 * « Send my position » on the page of the customer: the phone gives its position, the courier
 * sees it. Hidden when the browser has no position.
 */
export class OcdExpressPosition extends Interaction {
    static selector = ".o_ocd_ex_position";
    dynamicContent = {
        _root: { "t-on-submit.prevent": this.send },
    };

    start() {
        const button = this.el.querySelector("button");
        if (button && navigator.geolocation) {
            button.hidden = false;
        }
    }

    send() {
        const button = this.el.querySelector("button");
        if (button) {
            button.disabled = true;
            button.textContent = _t("Reading the position…");
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.el.querySelector("input[name='latitude']").value = position.coords.latitude;
                this.el.querySelector("input[name='longitude']").value = position.coords.longitude;
                this.el.submit();
            },
            () => {
                if (button) {
                    button.disabled = false;
                    button.textContent = _t("Position refused: allow it in your browser");
                }
            },
            { enableHighAccuracy: true, timeout: 15000 }
        );
    }
}

registry.category("public.interactions").add("ocd_express.parcel_form", OcdExpressParcelForm);
registry.category("public.interactions").add("ocd_express.position", OcdExpressPosition);
