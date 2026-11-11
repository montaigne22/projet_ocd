import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

/**
 * "Order on WhatsApp" link of the product pages: the message names the product, the chosen
 * options (size, colour...) and the page, so that the team knows what to prepare.
 */
export class WhatsappOrder extends Interaction {
    static selector = ".o_whatsapp_order";
    dynamicContent = {
        _root: { "t-on-click": this.onClick },
    };

    getOptions() {
        const selector = this.el.dataset.whatsappOptions || "input.js_variant_change:checked";
        const options = [];
        for (const el of document.querySelectorAll(selector)) {
            const label =
                el.dataset.valueName ||
                el.getAttribute("aria-label") ||
                el.closest("li")?.querySelector("label")?.textContent ||
                el.textContent;
            const text = (label || "").replace(/\s+/g, " ").trim();
            if (text && !options.includes(text)) {
                options.push(text);
            }
        }
        return options;
    }

    onClick(ev) {
        const { whatsappNumber, whatsappProduct } = this.el.dataset;
        const whatsappIntro = this.el.querySelector(".o_whatsapp_intro")?.textContent.trim() || "";
        if (!whatsappNumber) {
            return;
        }
        ev.preventDefault();
        const options = this.getOptions();
        const product = options.length
            ? `${whatsappProduct} (${options.join(", ")})`
            : whatsappProduct;
        const text = `${whatsappIntro} ${product}\n${window.location.href}`;
        window.open(
            `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(text)}`,
            "_blank",
            "noopener"
        );
    }
}

registry.category("public.interactions").add("whatsapp_cloud_sale.whatsapp_order", WhatsappOrder);
