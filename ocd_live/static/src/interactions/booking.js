import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const fold = (text) => (text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

/**
 * Number field with the dialing code of the country: the flag and the example of number follow
 * the chosen country. Without JavaScript, the list of the phone; with it, a sheet to search the
 * country by its name or its code ("cam", "+237"), made from the same list.
 */
export class OcdLivePhone extends Interaction {
    static selector = ".o_ocd_phone";
    dynamicContent = {
        ".o_ocd_dial_select": { "t-on-change": this.onChangeCountry },
        ".o_ocd_dial_button": { "t-on-click": this.openSheet },
        ".o_ocd_dial_close": { "t-on-click": this.closeSheet },
        ".o_ocd_dial_search": { "t-on-input": this.filter, "t-on-keydown": this.onSearchKey },
        ".o_ocd_dial_list": { "t-on-click": this.onPick, "t-on-keydown": this.onListKey },
        ".o_ocd_dial_sheet": { "t-on-click": this.onSheetClick },
    };

    setup() {
        this.selectEl = this.el.querySelector(".o_ocd_dial_select");
        this.inputEl = this.el.querySelector("input[name='phone']");
        this.buttonEl = this.el.querySelector(".o_ocd_dial_button");
        this.sheetEl = this.el.querySelector(".o_ocd_dial_sheet");
        this.searchEl = this.el.querySelector(".o_ocd_dial_search");
        this.listEl = this.el.querySelector(".o_ocd_dial_list");
        this.noneEl = this.el.querySelector(".o_ocd_dial_none");
        // The sheet needs <dialog>: an old browser keeps the list of the phone
        this.enhanced = Boolean(this.buttonEl && this.sheetEl?.showModal && this.listEl);
    }

    start() {
        if (!this.enhanced) {
            return;
        }
        this.buildList();
        this.buttonEl.hidden = false;
        this.el.querySelector(".o_ocd_dial").classList.add("o_ocd_dial_enhanced");
    }

    buildList() {
        const fragment = document.createDocumentFragment();
        for (const group of this.selectEl.querySelectorAll("optgroup")) {
            const title = document.createElement("div");
            title.className = "o_ocd_dial_group";
            title.textContent = group.label;
            fragment.appendChild(title);
            for (const option of group.querySelectorAll("option")) {
                const item = document.createElement("button");
                item.type = "button";
                item.className = "o_ocd_dial_item";
                item.setAttribute("role", "option");
                item.dataset.value = option.value;
                item.dataset.search = `${fold(option.dataset.name)} ${option.dataset.dial.replace("+", "")} ${option.dataset.dial}`;
                item.setAttribute("aria-selected", option.selected ? "true" : "false");
                const flag = document.createElement("span");
                flag.className = `o_ocd_flag o_ocd_flag_${option.dataset.flag}`;
                const name = document.createElement("span");
                name.className = "o_ocd_dial_name";
                name.textContent = option.dataset.name;
                const dial = document.createElement("span");
                dial.className = "o_ocd_dial_number";
                dial.textContent = option.dataset.dial;
                item.append(flag, name, dial);
                fragment.appendChild(item);
            }
        }
        this.listEl.replaceChildren(fragment);
    }

    openSheet() {
        this.searchEl.value = "";
        this.filter();
        this.sheetEl.showModal();
        const current = this.listEl.querySelector("[aria-selected='true']");
        current?.scrollIntoView({ block: "center" });
        // On a phone the keyboard would hide half of the list: the search is focused on demand
        if (window.matchMedia("(pointer: fine)").matches) {
            this.searchEl.focus();
        } else {
            current?.focus({ preventScroll: true });
        }
    }

    closeSheet() {
        this.sheetEl.close();
    }

    onSheetClick(ev) {
        if (ev.target === this.sheetEl) {
            this.closeSheet(); // a tap outside the sheet
        }
    }

    filter() {
        const query = fold(this.searchEl.value.trim());
        const digits = query.replace(/\D/g, "");
        let shown = 0;
        let groupTitle = null;
        let groupShown = 0;
        const closeGroup = () => {
            if (groupTitle) {
                groupTitle.hidden = groupShown === 0;
            }
        };
        for (const child of this.listEl.children) {
            if (child.classList.contains("o_ocd_dial_group")) {
                closeGroup();
                groupTitle = child;
                groupShown = 0;
                continue;
            }
            const search = child.dataset.search;
            const match = !query || search.includes(query) || (digits && search.includes(`+${digits}`));
            child.hidden = !match;
            if (match) {
                shown += 1;
                groupShown += 1;
            }
        }
        closeGroup();
        // A searched country appears once, even when it is also among the suggested ones
        if (query) {
            const seen = new Set();
            for (const item of this.listEl.querySelectorAll(".o_ocd_dial_item:not([hidden])")) {
                if (seen.has(item.dataset.value)) {
                    item.hidden = true;
                } else {
                    seen.add(item.dataset.value);
                }
            }
        }
        this.noneEl.hidden = shown > 0;
    }

    visibleItems() {
        return [...this.listEl.querySelectorAll(".o_ocd_dial_item:not([hidden])")];
    }

    onSearchKey(ev) {
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.visibleItems()[0]?.focus();
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            const first = this.visibleItems()[0];
            if (first) {
                this.pick(first.dataset.value);
            }
        }
    }

    onListKey(ev) {
        if (!["ArrowDown", "ArrowUp"].includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        const items = this.visibleItems();
        const index = items.indexOf(document.activeElement);
        const next = items[index + (ev.key === "ArrowDown" ? 1 : -1)];
        if (next) {
            next.focus();
        } else if (ev.key === "ArrowUp") {
            this.searchEl.focus();
        }
    }

    onPick(ev) {
        const item = ev.target.closest(".o_ocd_dial_item");
        if (item) {
            this.pick(item.dataset.value);
        }
    }

    pick(value) {
        this.selectEl.value = value;
        this.selectEl.dispatchEvent(new Event("change", { bubbles: true }));
        this.closeSheet();
        this.inputEl?.focus();
    }

    onChangeCountry() {
        const option = this.selectEl.selectedOptions[0];
        if (!option) {
            return;
        }
        for (const flag of this.el.querySelectorAll(".o_ocd_dial .o_ocd_flag")) {
            flag.className = `${flag.classList.contains("o_ocd_dial_flag") ? "o_ocd_flag o_ocd_dial_flag" : "o_ocd_flag"} o_ocd_flag_${option.dataset.flag}`;
        }
        const code = this.el.querySelector(".o_ocd_dial_code");
        if (code) {
            code.textContent = option.dataset.dial;
        }
        if (this.inputEl && option.dataset.example) {
            this.inputEl.placeholder = option.dataset.example;
        }
        for (const item of this.listEl?.querySelectorAll(".o_ocd_dial_item") || []) {
            item.setAttribute("aria-selected", item.dataset.value === option.value ? "true" : "false");
        }
        this.el.dispatchEvent(new Event("ocd-phone-change", { bubbles: true }));
    }
}

/**
 * "Who are you?": the banner shown during the live follows what the vendor types.
 */
export class OcdLiveInfos extends Interaction {
    static selector = ".o_ocd_infos";
    dynamicContent = {
        "input[name='name'], input[name='city'], input[name='phone']": { "t-on-input": this.updateBanner },
        "input[name='category_id']": { "t-on-change": this.updateBanner },
        _root: { "t-on-ocd-phone-change": this.updateBanner },
    };

    setup() {
        this.bannerEl = this.el.querySelector(".o_ocd_banner");
        this.defaultName = this.bannerEl?.querySelector(".o_ocd_banner_name")?.textContent || "";
    }

    start() {
        this.updateBanner();
    }

    updateBanner() {
        if (!this.bannerEl) {
            return;
        }
        const value = (name) => this.el.querySelector(`input[name='${name}']`)?.value.trim() || "";
        const category = this.el.querySelector("input[name='category_id']:checked");
        const dial = this.el.querySelector(".o_ocd_dial_select")?.selectedOptions[0]?.dataset.dial || "";
        const phone = value("phone");
        const texts = {
            ".o_ocd_banner_name": value("name") || this.defaultName,
            ".o_ocd_banner_category": category?.dataset.label || "",
            ".o_ocd_banner_city": value("city"),
            ".o_ocd_banner_phone": phone ? `WhatsApp ${dial} ${phone}` : "",
        };
        for (const [selector, text] of Object.entries(texts)) {
            const el = this.bannerEl.querySelector(selector);
            if (el) {
                el.textContent = text;
            }
        }
    }
}

// Platforms of the live links accepted by the directory (as checked by the server)
const LIVE_HOSTS = {
    "tiktok.com": "TikTok",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
};

function livePlatform(value) {
    let text = (value || "").trim();
    if (text && !text.includes("://")) {
        text = `https://${text}`;
    }
    try {
        const url = new URL(text);
        if (url.protocol !== "https:") {
            return false;
        }
        const host = url.hostname.toLowerCase().replace(/^www\./, "");
        for (const [domain, platform] of Object.entries(LIVE_HOSTS)) {
            if (host === domain || host.endsWith(`.${domain}`)) {
                return platform;
            }
        }
    } catch {
        // Not a link yet
    }
    return false;
}

/**
 * "Send the link of your live": tells at once whether the link is a live link.
 */
export class OcdLiveSendLink extends Interaction {
    static selector = ".o_ocd_send_link";
    dynamicContent = {
        "input[name='url']": { "t-on-input": this.checkLink },
    };

    start() {
        this.checkLink();
    }

    checkLink() {
        const value = this.el.querySelector("input[name='url']").value;
        const platform = livePlatform(value);
        const ok = this.el.querySelector(".o_ocd_link_ok");
        const bad = this.el.querySelector(".o_ocd_link_bad");
        ok.hidden = !platform;
        bad.hidden = Boolean(platform) || !value.trim();
        if (platform) {
            ok.querySelector(".o_ocd_link_platform").textContent = platform;
        }
    }
}

registry.category("public.interactions").add("ocd_live.phone", OcdLivePhone);
registry.category("public.interactions").add("ocd_live.send_link", OcdLiveSendLink);
registry.category("public.interactions").add("ocd_live.infos", OcdLiveInfos);
