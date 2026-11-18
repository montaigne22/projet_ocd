import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * « Put in promo »: what the customers will see, while the vendor chooses (« The customers see:
 * 9,000 F instead of 12,000 F »). The server checks everything again; without JavaScript, the
 * form works the same.
 */
export class OcdVendorPromo extends Interaction {
    static selector = ".o_ocd_promo_form";
    dynamicContent = {
        _root: { "t-on-change": this.update, "t-on-input": this.update },
    };

    start() {
        this.until = JSON.parse(this.el.dataset.until || "{}");
        this.update();
    }

    money(amount) {
        const lang = document.documentElement.lang || "fr";
        const number = new Intl.NumberFormat(lang, { maximumFractionDigits: 2 }).format(amount);
        const symbol = this.el.dataset.symbol || "";
        return this.el.dataset.position === "before" ? `${symbol} ${number}` : `${number} ${symbol}`;
    }

    update() {
        const reference = parseFloat(this.el.dataset.reference) || 0;
        const percent = this.el.querySelector("input[name='percent']:checked");
        const days = this.el.querySelector("input[name='days']:checked");
        const priceField = this.el.querySelector(".o_ocd_promo_price");
        const other = !percent || percent.value === "autre";
        priceField.hidden = !other;
        let price;
        if (other) {
            price = parseFloat((this.el.querySelector("input[name='price']").value || "").replace(/[\s  ]/g, "")
                .replace(",", "."));
        } else {
            price = reference * (100 - parseInt(percent.value)) / 100;
            if (price >= 1000 && Number.isInteger(reference)) {
                const rounded = Math.ceil(price / 50) * 50;
                price = rounded < reference ? rounded : price;
            }
        }
        const preview = this.el.querySelector(".o_ocd_promo_preview");
        if (!price || price <= 0 || price >= reference) {
            preview.hidden = true;
            return;
        }
        const off = `-${Math.round((reference - price) * 100 / reference)} %`;
        preview.querySelector(".o_ocd_promo_preview_title").textContent = this.el.dataset.title
            .replace("%(price)s", this.money(price)).replace("%(was)s", this.el.dataset.was);
        preview.querySelector(".o_ocd_promo_preview_line").textContent = this.el.dataset.line
            .replace("%(off)s", off).replace("%(until)s", (days && this.until[days.value]) || "");
        preview.hidden = false;
    }
}

registry.category("public.interactions").add("ocd_live_shop.vendor_promo", OcdVendorPromo);
