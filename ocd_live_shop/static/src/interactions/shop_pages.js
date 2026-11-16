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
        this.showStores(variant);
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
                const low = variant.qty <= this.data.low_stock;
                stock.textContent = variant.qty <= 0 ? texts.out : low ? texts.low.replace("%s", variant.qty) : texts.in_stock;
                stock.classList.toggle("o_ocd_variant_low", low);
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

    /** In their stores: the choice store by store (« Available · only 2 left », « Sold out »),
     * hidden when it is sold out everywhere. */
    showStores(variant) {
        const box = this.el.querySelector(".o_ocd_product_store_stock");
        if (!box) {
            return;
        }
        const out = !variant || !variant.stores || (variant.qty !== null && variant.qty <= 0);
        box.classList.toggle("d-none", out);
        if (out) {
            return;
        }
        const texts = this.data.texts;
        const label = box.querySelector(".o_ocd_store_stock_variant");
        if (label) {
            label.textContent = variant.label;
        }
        box.querySelectorAll(".o_ocd_store_stock_pill").forEach((pill, index) => {
            const level = variant.stores[index] || 0;
            pill.textContent = level <= 0
                ? texts.store_out
                : level <= this.data.low_stock ? texts.store_low.replace("%s", level) : texts.store_in;
            pill.classList.toggle("o_ocd_store_stock_in", level > 0);
            pill.classList.toggle("o_ocd_store_stock_out", level <= 0);
        });
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

// An amount typed on a phone, read like `tools.parse_amount` on the server (which decides): the
// currency and the spaces of the thousands go, then one amount, with cents only when the currency
// has some. No look-behind: the phones of 2020 must read this file.
const AMOUNT_CURRENCY = /(^|[^a-z])(f\s?cfa|cfa|xaf|xof|francs?|frs?|eur|euros?|usd|dollars?|f)(?![a-z])\.?/gi;
const AMOUNT = /^(\d{1,3}(?:([.,])\d{3})(?:\2\d{3})*|\d+)(?:([.,])(\d+))?$/;

export function readAmount(text, decimals = 0) {
    const value = String(text || "")
        .replace(AMOUNT_CURRENCY, "$1 ")
        .replace(/[€$\s  ']/g, "");
    const match = value.match(AMOUNT);
    if (!match || (match[3] && match[3] === match[2]) || (match[4] && match[4].length > decimals)) {
        return null;
    }
    const whole = parseInt(match[1].replace(/[.,]/g, ""), 10);
    return match[4] ? whole + parseInt(match[4], 10) / 10 ** match[4].length : whole;
}

// A light photo already small enough goes as taken
const KEEP_AS_TAKEN = 300 * 1024;

/**
 * A photo reduced on the phone before it is sent (longest side `maxPx`, JPEG): a 6 MB photo goes
 * in about 300 KB. The photo as taken when it is light already, or when the phone cannot.
 */
export async function shrinkPhoto(file, maxPx) {
    if (!maxPx || !file.type.startsWith("image/") || !window.createImageBitmap) {
        return file;
    }
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, maxPx / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size <= KEEP_AS_TAKEN) {
        bitmap.close?.();
        return file;
    }
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    context.fillStyle = "#fff"; // a transparent image gets a white background, not a black one
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close?.();
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    if (!blob || blob.size >= file.size) {
        return file;
    }
    const name = file.name.replace(/\.[^.]*$/, "") || "photo";
    return new File([blob], `${name}.jpg`, { type: "image/jpeg", lastModified: Date.now() });
}

function replaceInputFile(input, file) {
    try {
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
    } catch {
        // An old phone: the photo goes as taken (the server still checks its size)
    }
}

/**
 * My products, the form to add a product, made for a phone on a slow network:
 * - the photo shows at once, then is reduced (longest side `data-max-px`, JPEG): a 6 MB photo
 *   goes in about 300 KB; if the phone cannot, it goes as taken;
 * - the name, the price and the photo are checked before sending, with the messages of the
 *   server (`data-messages`): a mistake no longer costs a sending, nor the photo;
 * - a second tap while the form is on its way does nothing (the server also adds one product per
 *   form, with its token).
 * Without JavaScript the form still works: the server checks everything again.
 */
export class OcdProductForm extends Interaction {
    static selector = ".o_ocd_my_products_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
        ".o_ocd_photo_input": { "t-on-change": this.onPhoto },
        "#mp-name": { "t-on-input": () => this.showError("name", "") },
        "#mp-price": { "t-on-input": () => this.showError("price", "") },
    };

    setup() {
        this.messages = JSON.parse(this.el.dataset.messages || "{}");
        this.maxBytes = parseInt(this.el.dataset.maxBytes) || 0;
        this.maxPx = parseInt(this.el.dataset.maxPx) || 0;
        this.decimals = parseInt(this.el.dataset.decimals) || 0;
        this.input = this.el.querySelector(".o_ocd_photo_input");
        this.pick = this.el.querySelector(".o_ocd_photo_pick");
        this.button = this.el.querySelector(".o_ocd_my_products_send");
        this.shrinking = null;
        this.photoCount = 0;
        this.sending = false;
    }

    start() {
        // Back on this page from the next one: the phone may show it as it was left
        this.addListener(window, "pageshow", (ev) => ev.persisted && this.unlock());
    }

    destroy() {
        if (this.url) {
            URL.revokeObjectURL(this.url);
        }
    }

    kept() {
        return this.el.querySelector(".o_ocd_photo_kept");
    }

    async onPhoto() {
        const file = this.input.files[0];
        this.pick.classList.toggle("o_ocd_has_photo", !!file || !!this.kept() || !!this.el.dataset.hasPhoto);
        if (!file) {
            return;
        }
        this.kept()?.remove(); // the new photo replaces the one kept after an error
        this.el.querySelector(".o_ocd_photo_current")?.setAttribute("hidden", "");
        this.el.querySelector(".o_ocd_photo_added")?.removeAttribute("hidden");
        this.showError("photo", "");
        this.showPreview(file);
        const count = ++this.photoCount;
        this.shrinking = this.shrink(file).catch(() => file);
        const sent = await this.waitFor(this.shrinking);
        if (count !== this.photoCount) {
            return; // another photo was chosen meanwhile
        }
        this.shrinking = null;
        if (sent !== file) {
            this.replaceFile(sent);
        }
        if (this.maxBytes && sent.size > this.maxBytes) {
            this.showError("photo", this.messages.photo_big);
        }
    }

    showPreview(file) {
        if (this.url) {
            URL.revokeObjectURL(this.url);
        }
        this.url = URL.createObjectURL(file);
        this.el.querySelector(".o_ocd_photo_preview").src = this.url;
    }

    shrink(file) {
        return shrinkPhoto(file, this.maxPx);
    }

    replaceFile(file) {
        try {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            this.input.files = transfer.files;
        } catch {
            // An old phone: the photo goes as taken (the server still checks its size)
        }
    }

    async onSubmit(ev) {
        if (this.sending) {
            ev.preventDefault(); // a second tap: the form is already on its way
            return;
        }
        if (this.shrinking) {
            ev.preventDefault();
            await this.waitFor(this.shrinking);
            this.protectSyncAfterAsync(() => this.send())();
            return;
        }
        if (!this.check()) {
            ev.preventDefault();
            return;
        }
        this.lock();
    }

    send() {
        if (!this.sending && this.check()) {
            this.lock();
            this.el.submit();
        }
    }

    check() {
        const name = this.el.querySelector("#mp-name");
        const price = this.el.querySelector("#mp-price");
        const file = this.input.files[0];
        let photo = "";
        if (!file && !this.kept() && !this.el.dataset.hasPhoto) {
            photo = this.messages.photo; // a product corrected keeps its photo
        } else if (file && this.maxBytes && file.size > this.maxBytes) {
            photo = this.messages.photo_big;
        }
        const errors = {
            photo,
            name: name.value.trim() ? "" : this.messages.name,
            price: !price.value.trim()
                ? this.messages.price_empty
                : readAmount(price.value, this.decimals) > 0
                ? ""
                : this.messages.price,
        };
        for (const [key, message] of Object.entries(errors)) {
            this.showError(key, message);
        }
        const first = Object.keys(errors).find((key) => errors[key]);
        if (first === "photo") {
            this.pick.scrollIntoView({ block: "center" });
        } else if (first) {
            this.el.querySelector(`#mp-${first}`).focus();
        }
        return !first;
    }

    showError(key, message) {
        const span = this.el.querySelector(`#mp-${key}-error`);
        const field = key === "photo" ? this.input : this.el.querySelector(`#mp-${key}`);
        if (span) {
            span.textContent = message || "";
            span.hidden = !message;
        }
        if (message) {
            field?.setAttribute("aria-invalid", "true");
        } else {
            field?.removeAttribute("aria-invalid");
        }
    }

    lock() {
        this.sending = true;
        this.label = this.button.textContent;
        this.button.textContent = this.messages.sending;
        this.button.setAttribute("aria-disabled", "true");
        this.el.setAttribute("aria-busy", "true");
    }

    unlock() {
        this.sending = false;
        if (this.label) {
            this.button.textContent = this.label;
        }
        this.button.removeAttribute("aria-disabled");
        this.el.removeAttribute("aria-busy");
    }
}

/**
 * My products: the filters by state show the products at once, without a new page on a slow
 * network. The links still give the same page without JavaScript; the address keeps the filter.
 */
export class OcdProductFilters extends Interaction {
    static selector = ".o_ocd_my_products_filters";
    dynamicContent = {
        "a[data-state]": { "t-on-click": this.choose },
    };

    choose(ev) {
        ev.preventDefault();
        const chosen = ev.currentTarget;
        const state = chosen.dataset.state;
        for (const chip of this.el.querySelectorAll("a[data-state]")) {
            if (chip === chosen) {
                chip.setAttribute("aria-current", "true");
            } else {
                chip.removeAttribute("aria-current");
            }
        }
        const list = document.querySelector(".o_ocd_my_products_list");
        let shown = 0;
        for (const row of list.querySelectorAll(".o_ocd_my_product[data-status]")) {
            const visible = state === "all" || row.dataset.status === state;
            row.hidden = !visible;
            shown += visible ? 1 : 0;
        }
        const none = list.querySelector(".o_ocd_my_products_none");
        if (none) {
            none.hidden = shown > 0;
        }
        history.replaceState(history.state, "", chosen.href);
    }
}

/**
 * My stores, the form of a place: a store or a home (the parts of a store hidden for a home), the
 * position taken by the phone (« I am in my store »: refused beyond 200 m of accuracy), the
 * districts of the city chosen, the photo of the front reduced like the photos of the products,
 * the hours of a day shown when it is open, checks before sending and one sending only.
 * Without JavaScript the form still works (no position then: the server says so).
 */
export class OcdPlaceForm extends Interaction {
    static selector = ".o_ocd_place_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
        "input[name='kind']": { "t-on-change": this.onKind },
        ".o_ocd_place_locate": { "t-on-click": this.locate },
        ".o_ocd_place_city": { "t-on-change": this.loadDistricts },
        ".o_ocd_photo_input": { "t-on-change": this.onPhoto },
        ".o_ocd_place_day input[type='checkbox']": { "t-on-change": this.onDay },
    };

    setup() {
        this.messages = JSON.parse(this.el.dataset.messages || "{}");
        this.maxPx = parseInt(this.el.dataset.maxPx) || 0;
        this.maxBytes = parseInt(this.el.dataset.maxBytes) || 0;
        this.sending = false;
        this.shrinking = null;
    }

    field(name) {
        return this.el.querySelector(`[name='${name}']`);
    }

    kind() {
        return this.el.querySelector("input[name='kind']:checked")?.value || this.field("kind")?.value || "store";
    }

    onKind() {
        const home = this.kind() === "home";
        for (const el of this.el.querySelectorAll(".o_ocd_place_store_only")) {
            el.hidden = home;
        }
        for (const el of this.el.querySelectorAll(".o_ocd_place_home_only")) {
            el.hidden = !home;
        }
    }

    onDay(ev) {
        const day = ev.currentTarget.closest(".o_ocd_place_day");
        day.querySelector(".o_ocd_place_day_hours").hidden = !ev.currentTarget.checked;
        day.querySelector(".o_ocd_place_day_closed").hidden = ev.currentTarget.checked;
    }

    showError(id, message) {
        const span = this.el.querySelector(`#pl-${id}-error`);
        if (span) {
            span.textContent = message || "";
            span.hidden = !message;
        }
    }

    locate() {
        const status = this.el.querySelector(".o_ocd_place_position");
        if (!navigator.geolocation) {
            this.showError("position", this.messages.unavailable);
            return;
        }
        status.textContent = this.messages.locating;
        this.showError("position", "");
        navigator.geolocation.getCurrentPosition(
            this.protectSyncAfterAsync((position) => {
                const { latitude, longitude, accuracy } = position.coords;
                const meters = Math.round(accuracy);
                if (meters > 200) {
                    status.textContent = "";
                    this.showError("position", this.messages.vague.replace("%s", meters));
                    return;
                }
                this.field("latitude").value = latitude.toFixed(7);
                this.field("longitude").value = longitude.toFixed(7);
                this.field("accuracy").value = meters;
                this.field("position_taken").value = "1";
                this.el.dataset.hasPosition = "1";
                status.textContent = this.messages.located.replace("%s", meters);
            }),
            this.protectSyncAfterAsync((error) => {
                status.textContent = "";
                this.showError("position", error.code === 1 ? this.messages.denied : this.messages.unavailable);
            }),
            { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
        );
    }

    async loadDistricts(ev) {
        let districts = [];
        try {
            districts = await this.waitFor(rpc("/delivery_cameroon/districts", { city_id: parseInt(ev.currentTarget.value) }));
        } catch {
            return;
        }
        const select = this.el.querySelector(".o_ocd_place_district");
        // The empty choice keeps the text of the page (« Choose », in the language of the vendor)
        const empty = select.querySelector('option[value=""]')?.cloneNode(true)
            || Object.assign(document.createElement("option"), { value: "" });
        empty.selected = true;
        select.replaceChildren(empty, ...districts.map((district) =>
            Object.assign(document.createElement("option"), { value: district.id, textContent: district.name })
        ));
    }

    async onPhoto() {
        const input = this.el.querySelector(".o_ocd_photo_input");
        const file = input.files[0];
        const pick = input.closest(".o_ocd_photo_pick");
        pick.classList.toggle("o_ocd_has_photo", !!file || !!this.el.dataset.hasPhoto);
        if (!file) {
            return;
        }
        this.el.querySelector(".o_ocd_photo_kept")?.remove();
        this.showError("photo", "");
        if (this.url) {
            URL.revokeObjectURL(this.url);
        }
        this.url = URL.createObjectURL(file);
        pick.querySelector(".o_ocd_photo_preview").src = this.url;
        this.shrinking = shrinkPhoto(file, this.maxPx).catch(() => file);
        const sent = await this.waitFor(this.shrinking);
        this.shrinking = null;
        if (sent !== file) {
            replaceInputFile(input, sent);
        }
        if (this.maxBytes && sent.size > this.maxBytes) {
            this.showError("photo", this.messages.photo_big);
        }
    }

    destroy() {
        if (this.url) {
            URL.revokeObjectURL(this.url);
        }
    }

    check() {
        const store = this.kind() === "store";
        const proof = store && this.el.dataset.proof;
        const errors = {
            name: store && !this.field("name").value.trim() ? this.messages.name : "",
            district: !this.field("district_id").value ? this.messages.district : "",
            photo: proof && !this.el.querySelector(".o_ocd_photo_input").files.length && !this.el.dataset.hasPhoto
                ? this.messages.photo : "",
            position: proof && !this.el.dataset.hasPosition ? this.messages.position : "",
        };
        for (const [key, message] of Object.entries(errors)) {
            this.showError(key, message);
        }
        const first = Object.keys(errors).find((key) => errors[key]);
        if (first) {
            this.el.querySelector(`#pl-${first}-error`)?.scrollIntoView({ block: "center" });
        }
        return !first;
    }

    async onSubmit(ev) {
        if (this.sending) {
            ev.preventDefault();
            return;
        }
        if (this.shrinking) {
            ev.preventDefault();
            await this.waitFor(this.shrinking);
            this.protectSyncAfterAsync(() => {
                if (!this.sending && this.check()) {
                    this.lock();
                    this.el.submit();
                }
            })();
            return;
        }
        if (!this.check()) {
            ev.preventDefault();
            return;
        }
        this.lock();
    }

    lock() {
        this.sending = true;
        const button = this.el.querySelector(".o_ocd_place_send");
        button.textContent = this.messages.sending;
        button.setAttribute("aria-disabled", "true");
    }
}

/**
 * The boutique: the itinerary, the call or the message of a store counted for its vendor
 * (« 18 itineraries this week »), by a beacon; the link opens as usual.
 */
export class OcdPlaceTap extends Interaction {
    static selector = "[data-tap]";
    dynamicContent = {
        _root: { "t-on-click": this.tap },
    };

    tap() {
        navigator.sendBeacon?.(this.el.dataset.tap);
    }
}

/**
 * Send pieces to another store: a store chosen shows its free pieces (the page again, without
 * the quantities), the button says how many pieces leave and where to.
 */
export class OcdSendPieces extends Interaction {
    static selector = ".o_ocd_stock_send_form";
    dynamicContent = {
        ".o_ocd_stock_send_place": { "t-on-change": this.choosePlace },
        ".o_ocd_stepper_value": { "t-on-change": this.count, "t-on-input": this.count },
    };

    start() {
        this.count();
    }

    choosePlace() {
        const from = this.el.querySelector("[name=de]").value;
        const to = this.el.querySelector("[name=a]").value;
        window.location.assign(`${this.el.getAttribute("action")}?de=${encodeURIComponent(from)}&a=${encodeURIComponent(to)}`);
    }

    count() {
        let total = 0;
        for (const input of this.el.querySelectorAll(".o_ocd_stepper_value")) {
            total += Math.max(0, parseInt(input.value) || 0);
        }
        const { labelNone, labelOne, labelMany } = this.el.dataset;
        const label = total === 0 ? labelNone : total === 1 ? labelOne : labelMany.replace("__COUNT__", total);
        this.el.querySelector(".o_ocd_stock_send_button").textContent = label;
    }
}

/**
 * The price labels of a store: the button prints the page (the print styles keep the labels only).
 */
export class OcdPrint extends Interaction {
    static selector = "[data-print]";
    dynamicContent = {
        _root: { "t-on-click": () => window.print() },
    };
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
    .add("ocd_live_shop.product_form", OcdProductForm)
    .add("ocd_live_shop.product_filters", OcdProductFilters)
    .add("ocd_live_shop.place_form", OcdPlaceForm)
    .add("ocd_live_shop.place_tap", OcdPlaceTap)
    .add("ocd_live_shop.print", OcdPrint)
    .add("ocd_live_shop.send_pieces", OcdSendPieces)
    .add("ocd_live_shop.vendor_rates_form", OcdVendorRatesForm);
