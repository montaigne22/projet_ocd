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
 * Product page: the values chosen (colour, size...) give the variant, its price, its stock and
 * its photo (the one of the colour). A sold-out choice can still be chosen: it offers « Tell me
 * when it is back ». The address keeps the choice (?v=), to share the red dress. The photos open
 * full screen: swipe from one to the next, pinch or tap twice to zoom, the back button of the
 * phone closes them.
 */
export class OcdProductPage extends Interaction {
    static selector = ".o_ocd_product_page[data-variants]";
    dynamicContent = {
        _root: { "t-on-change": this.onChange },
        ".o_ocd_gallery_slide": { "t-on-click": this.onSlide },
        ".o_ocd_viewer_close": { "t-on-click": this.closeViewer },
    };

    setup() {
        this.data = JSON.parse(this.el.dataset.variants);
        this.trackEl = this.el.querySelector(".o_ocd_gallery_track");
        this.dotsEl = this.el.querySelector(".o_ocd_gallery_dots");
        this.viewerEl = this.el.querySelector(".o_ocd_viewer");
        this.overlay = false;
    }

    start() {
        this.update({ initial: true });
        if (this.trackEl) {
            this.addListener(this.trackEl, "scroll", () => this.syncDots(), { passive: true });
        }
        if (this.viewerEl?.showModal) {
            const track = this.viewerEl.querySelector(".o_ocd_viewer_track");
            this.addListener(track, "scroll", () => this.syncCount(), { passive: true });
            this.addListener(track, "dblclick", (ev) => this.toggleZoom(ev));
            this.addListener(this.viewerEl, "close", () => this.onViewerClosed());
            this.addListener(window, "popstate", () => this.viewerEl.open && this.viewerEl.close());
        }
        // The photos of the other colours, ready before they are chosen
        this.waitForTimeout(() => this.preload(), 1200);
    }

    // === VARIANT === //

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

    onChange(ev) {
        if (ev.target.classList.contains("o_ocd_variant_input")) {
            this.update({ initial: false });
        } else if (ev.target.name === "quantity") {
            this.update({ initial: true });
        }
    }

    update({ initial = false } = {}) {
        const values = this.selected();
        // Values that only lead to sold-out variants: still chosen, to be told when they are back
        for (const input of this.el.querySelectorAll(".o_ocd_variant_input")) {
            const others = values.filter((value) => {
                const other = this.el.querySelector(`.o_ocd_variant_input[value="${value}"]`);
                return other && other.name !== input.name;
            });
            const variant = this.variantOf([...others, parseInt(input.value)]);
            const gone = !variant || (variant.qty !== null && variant.qty <= 0);
            input.closest(".o_ocd_product_value").classList.toggle("o_ocd_gone", gone);
        }
        for (const fieldset of this.el.querySelectorAll(".o_ocd_product_choice")) {
            const checked = fieldset.querySelector(".o_ocd_variant_input:checked");
            const label = fieldset.querySelector(".o_ocd_choice_value");
            if (checked && label) {
                label.textContent = checked.dataset.name;
            }
        }
        const variant = this.variantOf(values);
        const price = this.el.querySelector(".o_ocd_variant_price");
        const stock = this.el.querySelector(".o_ocd_variant_stock");
        const add = this.el.querySelector(".o_ocd_variant_add");
        const qtyInput = this.el.querySelector("input[name=quantity]");
        this.showPhotos(variant);
        this.showAlert(variant);
        if (!initial) {
            this.keepInAddress(values);
        }
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

    /** « Tell me when it is back » for a choice sold out. */
    showAlert(variant) {
        const box = this.el.querySelector(".o_ocd_stock_alert");
        if (!box || box.querySelector(".o_ocd_ok")) {
            return; // already noted: the message stays
        }
        const out = Boolean(variant && variant.qty !== null && variant.qty <= 0);
        box.classList.toggle("d-none", !out);
        if (out) {
            box.querySelector(".o_ocd_stock_alert_variant").value = variant.id;
            const title = box.querySelector(".o_ocd_stock_alert_title");
            if (title) {
                title.textContent = this.data.texts.gone.replace("%s", variant.label);
            }
        }
    }

    keepInAddress(values) {
        const url = new URL(window.location.href);
        url.searchParams.set("v", [...values].sort((a, b) => a - b).join(","));
        url.searchParams.delete("prevenu");
        url.searchParams.delete("erreur");
        url.hash = "";
        window.history.replaceState(window.history.state, "", url);
        document.dispatchEvent(new CustomEvent("ocd-url-change"));
    }

    // === PHOTOS === //

    photosOf(variant) {
        const { main, extras } = this.data;
        const own = variant?.photo;
        return [own || main, ...(own && main ? [main] : []), ...extras].filter(Boolean);
    }

    showPhotos(variant) {
        if (!this.trackEl) {
            return;
        }
        const photos = this.photosOf(variant);
        const first = this.trackEl.querySelector(".o_ocd_gallery_slide img");
        if (!photos.length || (first && first.getAttribute("src") === photos[0].src && this.trackEl.children.length === photos.length)) {
            return;
        }
        const name = this.el.querySelector("h1")?.textContent || "";
        const slides = photos.map((photo, index) => {
            const slide = document.createElement("a");
            slide.className = "o_ocd_gallery_slide";
            slide.href = photo.full;
            slide.target = "_blank";
            slide.rel = "noopener";
            slide.dataset.index = index;
            slide.setAttribute("aria-label", `${name} · ${index + 1}/${photos.length}`);
            const img = document.createElement("img");
            img.src = photo.src;
            img.alt = "";
            img.className = "o_ocd_photo_img";
            img.decoding = "async";
            slide.appendChild(img);
            return slide;
        });
        this.trackEl.replaceChildren(...slides);
        this.trackEl.scrollLeft = 0;
        if (this.dotsEl) {
            this.dotsEl.replaceChildren(...photos.map(() => document.createElement("i")));
            this.dotsEl.hidden = photos.length < 2;
        }
        this.syncDots();
    }

    syncDots() {
        if (!this.dotsEl || !this.trackEl) {
            return;
        }
        const index = Math.round(this.trackEl.scrollLeft / Math.max(this.trackEl.clientWidth, 1));
        [...this.dotsEl.children].forEach((dot, at) => dot.classList.toggle("o_ocd_on", at === index));
    }

    preload() {
        const seen = new Set();
        for (const variant of this.data.variants) {
            if (variant.photo && !seen.has(variant.photo.src)) {
                seen.add(variant.photo.src);
                new Image().src = variant.photo.src;
            }
        }
    }

    // === VIEWER === //

    onSlide(ev) {
        if (!this.viewerEl?.showModal) {
            return; // the photo opens in a new tab
        }
        ev.preventDefault();
        this.openViewer(parseInt(ev.currentTarget.dataset.index) || 0);
    }

    openViewer(index) {
        const track = this.viewerEl.querySelector(".o_ocd_viewer_track");
        const slides = [...this.trackEl.querySelectorAll(".o_ocd_gallery_slide")].map((slide) => {
            const box = document.createElement("div");
            box.className = "o_ocd_viewer_slide";
            const img = document.createElement("img");
            img.src = slide.href;
            img.alt = slide.getAttribute("aria-label") || "";
            img.decoding = "async";
            box.appendChild(img);
            return box;
        });
        track.replaceChildren(...slides);
        this.viewerEl.showModal();
        track.scrollLeft = index * track.clientWidth;
        this.syncCount();
        // The back button of the phone closes the photos, not the page
        window.history.pushState({ ...(window.history.state || {}), ocdOverlay: true }, "");
        this.overlay = true;
    }

    closeViewer() {
        if (this.overlay && window.history.state?.ocdOverlay) {
            window.history.back(); // closes the viewer (popstate)
        } else {
            this.viewerEl.close();
        }
    }

    onViewerClosed() {
        if (this.overlay && window.history.state?.ocdOverlay) {
            this.overlay = false;
            window.history.back(); // Escape: the entry of the photos goes too
        }
        this.overlay = false;
        for (const slide of this.viewerEl.querySelectorAll(".o_ocd_zoomed")) {
            slide.classList.remove("o_ocd_zoomed");
        }
    }

    syncCount() {
        const track = this.viewerEl.querySelector(".o_ocd_viewer_track");
        const count = this.viewerEl.querySelector(".o_ocd_viewer_count");
        const total = track.children.length;
        const index = Math.min(Math.round(track.scrollLeft / Math.max(track.clientWidth, 1)) + 1, total);
        count.textContent = total > 1 ? `${index} / ${total}` : "";
    }

    toggleZoom(ev) {
        const slide = ev.target.closest(".o_ocd_viewer_slide");
        if (!slide) {
            return;
        }
        const zoomed = slide.classList.toggle("o_ocd_zoomed");
        if (zoomed) {
            // Zoom where the finger is
            const rect = slide.getBoundingClientRect();
            const x = (ev.clientX - rect.left) / rect.width;
            const y = (ev.clientY - rect.top) / rect.height;
            slide.scrollLeft = x * slide.scrollWidth - rect.width / 2;
            slide.scrollTop = y * slide.scrollHeight - rect.height / 2;
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

/**
 * My products: the photo of a colour is sent as soon as it is chosen.
 */
export class OcdColourPhoto extends Interaction {
    static selector = ".o_ocd_colour_photo";
    dynamicContent = {
        ".o_ocd_colour_photo_input": { "t-on-change": this.send },
    };

    send(ev) {
        if (ev.target.files?.length) {
            this.el.classList.add("o_ocd_sending");
            this.el.requestSubmit ? this.el.requestSubmit() : this.el.submit();
        }
    }
}

registry
    .category("public.interactions")
    .add("ocd_live_shop.colour_photo", OcdColourPhoto)
    .add("ocd_live_shop.stepper", OcdStepper)
    .add("ocd_live_shop.product_page", OcdProductPage)
    .add("ocd_live_shop.delivery_form", OcdDeliveryForm)
    .add("ocd_live_shop.photo_pick", OcdPhotoPick)
    .add("ocd_live_shop.vendor_rates_form", OcdVendorRatesForm);
