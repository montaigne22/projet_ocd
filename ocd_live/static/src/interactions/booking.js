import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Number field with the dialing code of the country: the flag follows the chosen country.
 */
export class OcdLivePhone extends Interaction {
    static selector = ".o_ocd_phone";
    dynamicContent = {
        ".o_ocd_dial_select": { "t-on-change": this.onChangeCountry },
    };

    setup() {
        this.selectEl = this.el.querySelector(".o_ocd_dial_select");
        this.flagEl = this.el.querySelector(".o_ocd_flag");
    }

    onChangeCountry() {
        const option = this.selectEl.selectedOptions[0];
        if (option && this.flagEl) {
            this.flagEl.className = `o_ocd_flag o_ocd_flag_${option.dataset.flag}`;
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
