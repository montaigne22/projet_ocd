import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Quantity with − and + (product page, my products): the field stays a normal number field,
 * so the form also works without JavaScript.
 */
export class OcdStepper extends Interaction {
    static selector = ".o_ocd_stepper_js";
    dynamicContent = {
        ".o_ocd_stepper_less": { "t-on-click": () => this.step(-1) },
        ".o_ocd_stepper_more": { "t-on-click": () => this.step(1) },
    };

    step(delta) {
        const input = this.el.querySelector(".o_ocd_stepper_value");
        const min = input.min === "" ? 0 : parseInt(input.min);
        const max = input.max === "" ? Infinity : parseInt(input.max);
        const value = Math.min(max, Math.max(min, (parseInt(input.value) || 0) + delta));
        input.value = value;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }
}

/**
 * Product page: the values chosen (colour, size...) give the variant, its price and its stock;
 * the values whose variants are sold out cannot be chosen.
 */
export class OcdProductPage extends Interaction {
    static selector = ".o_ocd_product_page[data-variants]";
    dynamicContent = {
        _root: { "t-on-change": this.update },
    };

    setup() {
        this.data = JSON.parse(this.el.dataset.variants);
    }

    start() {
        this.update();
    }

    selected() {
        return [...this.el.querySelectorAll(".o_ocd_variant_input:checked")].map((input) => parseInt(input.value));
    }

    variantOf(values) {
        return this.data.variants.find((variant) => values.every((value) => variant.values.includes(value)));
    }

    money(amount) {
        const { symbol, position, digits } = this.data.currency;
        const number = new Intl.NumberFormat(document.documentElement.lang || undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: digits,
        }).format(amount);
        return position === "before" ? `${symbol} ${number}` : `${number} ${symbol}`;
    }

    update() {
        const values = this.selected();
        // Values that only lead to sold-out variants
        for (const input of this.el.querySelectorAll(".o_ocd_variant_input")) {
            const others = values.filter((value) => {
                const other = this.el.querySelector(`.o_ocd_variant_input[value="${value}"]`);
                return other && other.name !== input.name;
            });
            const variant = this.variantOf([...others, parseInt(input.value)]);
            const gone = !variant || (variant.qty !== null && variant.qty <= 0);
            input.closest(".o_ocd_product_value").classList.toggle("o_ocd_gone", gone);
        }
        const variant = this.variantOf(values);
        const price = this.el.querySelector(".o_ocd_variant_price");
        const stock = this.el.querySelector(".o_ocd_variant_stock");
        const add = this.el.querySelector(".o_ocd_variant_add");
        const qtyInput = this.el.querySelector("input[name=quantity]");
        if (!variant) {
            if (add) {
                add.disabled = true;
            }
            return;
        }
        if (price) {
            price.textContent = variant.price_text;
        }
        const texts = this.data.texts;
        let qty = qtyInput ? Math.max(1, parseInt(qtyInput.value) || 1) : 1;
        if (variant.qty !== null) {
            if (qtyInput) {
                qtyInput.max = Math.max(variant.qty, 1);
                qty = Math.min(qty, Math.max(variant.qty, 1));
                qtyInput.value = qty;
            }
            if (stock) {
                stock.textContent = variant.qty <= 0 ? texts.out : variant.qty <= 3 ? texts.low.replace("%s", variant.qty) : texts.in_stock;
                stock.classList.toggle("o_ocd_variant_low", variant.qty <= 3);
            }
        } else if (stock) {
            stock.textContent = texts.in_stock;
            stock.classList.remove("o_ocd_variant_low");
        }
        if (add) {
            const out = variant.qty !== null && variant.qty <= 0;
            add.disabled = out;
            add.textContent = out ? texts.out : texts.add.replace("%s", qty > 1 ? this.money(variant.price * qty) : variant.price_text);
        }
    }
}

/**
 * Where do we deliver: the districts of the city, then the delivery method of the address and
 * its price, as soon as the city or the district changes.
 */
export class OcdDeliveryForm extends Interaction {
    static selector = ".o_ocd_delivery_form";
    dynamicContent = {
        ".o_ocd_delivery_city": { "t-on-change": () => this.refresh(true) },
        ".o_ocd_delivery_district": { "t-on-change": () => this.refresh(false) },
        ".o_ocd_input": { "t-on-input": this.clearError },
        ".o_ocd_delivery_country": { "t-on-change": this.changeCountry },
    };

    changeCountry(ev) {
        // The cities and the districts are those of the country
        window.location.assign(`/shop/checkout?pays=${encodeURIComponent(ev.currentTarget.value)}`);
    }

    clearError(ev) {
        // The message of a field goes away as soon as the field is corrected
        const field = ev.currentTarget.closest(".o_ocd_field");
        ev.currentTarget.removeAttribute("aria-invalid");
        field?.querySelectorAll(".o_ocd_error").forEach((el) => el.remove());
    }

    async refresh(cityChanged) {
        const city = this.el.querySelector(".o_ocd_delivery_city");
        const district = this.el.querySelector(".o_ocd_delivery_district");
        let result;
        try {
            result = await this.waitFor(rpc("/ocd/livraison/tarif", {
                country_id: parseInt(this.el.querySelector("[name=delivery_country_id]").value),
                city_id: parseInt(city.value) || false,
                district_id: cityChanged ? false : parseInt(district.value) || false,
            }));
        } catch {
            return; // Network hiccup: the price is checked again when the form is sent
        }
        if (cityChanged) {
            const first = district.querySelector("option[value='']");
            district.replaceChildren(first);
            for (const row of result.districts || []) {
                district.append(new Option(row.name, row.id));
            }
            const none = !(result.districts || []).length;
            district.classList.toggle("d-none", none);
            this.el.querySelector(".o_ocd_delivery_no_district").classList.toggle("d-none", !none);
        }
        const method = result.method;
        this.el.querySelector(".o_ocd_delivery_name").textContent = method ? method.name : "";
        this.el.querySelector(".o_ocd_delivery_note").textContent = method ? method.note : result.none;
        this.el.querySelector(".o_ocd_delivery_fee").textContent = method ? method.fee : "";
        if (method) {
            this.el.querySelector(".o_ocd_delivery_total").textContent = method.total;
        }
        this.renderParcels(method ? method.rows || [] : [], result.remove_label);
    }

    renderParcels(rows, removeLabel) {
        // One line per parcel: its price, or why the vendor cannot deliver to the address
        const box = this.el.querySelector(".o_ocd_delivery_parcels");
        if (!box) {
            return;
        }
        box.replaceChildren(...rows.map((row) => {
            const line = document.createElement("div");
            line.className = "o_ocd_delivery_parcel" + (row.error ? " o_ocd_delivery_parcel_ko" : "");
            const text = document.createElement("span");
            text.className = "o_ocd_delivery_parcel_text";
            const title = document.createElement("b");
            title.textContent = row.title;
            const sub = document.createElement("small");
            sub.textContent = row.error || row.sub;
            if (row.error) {
                sub.className = "o_ocd_error";
            }
            text.append(title, sub);
            line.append(text);
            if (row.error) {
                const remove = document.createElement("button");
                Object.assign(remove, { type: "submit", name: "vendor_id", value: row.vendor_id, className: "o_ocd_link o_ocd_delivery_remove" });
                remove.setAttribute("form", "ocd-remove-vendor");
                remove.textContent = removeLabel;
                line.append(remove);
            } else {
                const fee = document.createElement("b");
                fee.textContent = row.fee;
                line.append(fee);
            }
            return line;
        }));
    }
}

/**
 * My products: the photo taken shows before it is sent.
 */
export class OcdPhotoPick extends Interaction {
    static selector = ".o_ocd_photo_pick";
    dynamicContent = {
        ".o_ocd_photo_input": { "t-on-change": this.show },
    };

    show(ev) {
        const file = ev.currentTarget.files[0];
        this.el.classList.toggle("o_ocd_has_photo", !!file);
        if (file) {
            const preview = this.el.querySelector(".o_ocd_photo_preview");
            if (this.url) {
                URL.revokeObjectURL(this.url);
            }
            this.url = URL.createObjectURL(file);
            preview.src = this.url;
        }
    }

    destroy() {
        if (this.url) {
            URL.revokeObjectURL(this.url);
        }
    }
}

/**
 * My delivery prices: the districts of the city chosen.
 */
export class OcdVendorRatesForm extends Interaction {
    static selector = ".o_ocd_my_rates_form";
    dynamicContent = {
        ".o_ocd_rates_city": { "t-on-change": this.loadDistricts },
    };

    async loadDistricts(ev) {
        let districts = [];
        try {
            districts = await this.waitFor(rpc("/delivery_cameroon/districts", { city_id: parseInt(ev.currentTarget.value) }));
        } catch {
            return;
        }
        const list = this.el.querySelector(".o_ocd_rates_district_list");
        list.replaceChildren(...districts.map((district) => {
            const label = document.createElement("label");
            label.className = "o_ocd_chip_choice";
            const input = Object.assign(document.createElement("input"), { type: "checkbox", name: "district_ids", value: district.id });
            const chip = Object.assign(document.createElement("span"), { className: "o_ocd_chip", textContent: district.name });
            label.append(input, chip);
            return label;
        }));
    }
}

registry
    .category("public.interactions")
    .add("ocd_live_shop.stepper", OcdStepper)
    .add("ocd_live_shop.product_page", OcdProductPage)
    .add("ocd_live_shop.delivery_form", OcdDeliveryForm)
    .add("ocd_live_shop.photo_pick", OcdPhotoPick)
    .add("ocd_live_shop.vendor_rates_form", OcdVendorRatesForm);
