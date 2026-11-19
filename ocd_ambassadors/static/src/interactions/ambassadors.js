import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const SHOWN_MS = 4000;
const RECO_COOKIE = "ocd_reco";

function readCookie(name) {
    const row = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
    return row ? row.slice(name.length + 1) : "";
}

/**
 * « Grâce recommends this product to you »: the link of an ambassador left a small cookie
 * (« <product>:<first name> »); the page itself is the same for everyone (kept in memory for the
 * crowds), the name is written here, as text only.
 */
export class OcdAmbassadorReco extends Interaction {
    static selector = ".o_ocd_amb_reco[data-product]";

    start() {
        const [productId, name] = readCookie(RECO_COOKIE).split(":");
        if (!name || productId !== this.el.dataset.product) {
            return;
        }
        let first = "";
        try {
            first = decodeURIComponent(name).trim().slice(0, 40);
        } catch {
            return;
        }
        const text = this.el.querySelector(".o_ocd_amb_reco_text");
        if (!first || !text) {
            return;
        }
        text.textContent = text.textContent.replace("%s", first);
        this.el.querySelector("i").textContent = first.slice(0, 1).toUpperCase();
        this.el.hidden = false;
    }
}

/**
 * The text of « Share », changed by the ambassador: the link stays at the end (added when it is
 * missing), the buttons share what is written.
 */
export class OcdAmbassadorShareText extends Interaction {
    static selector = ".o_ocd_amb_text";
    dynamicContent = {
        _root: { "t-on-input": this.update },
    };

    start() {
        this.update();
    }

    update() {
        const link = this.el.dataset.link || "";
        const typed = this.el.value.trim();
        const full = !link || typed.includes(link) ? typed : `${typed} ${link}`.trim();
        // The share sheet adds the address of the page after the text: the link once only
        const withoutLink = link ? full.replace(link, "").replace(/\s+$/, "") : full;
        const pane = this.el.closest(".o_ocd_amb_pane") || document;
        for (const button of pane.querySelectorAll(".o_ocd_amb_share")) {
            button.dataset.text = withoutLink;
        }
        for (const button of pane.querySelectorAll(".o_ocd_clip_share_file")) {
            button.dataset.text = withoutLink;
        }
        for (const anchor of pane.querySelectorAll(".o_ocd_amb_wa")) {
            anchor.href = `https://wa.me/?text=${encodeURIComponent(full)}`;
        }
    }
}

/**
 * « Copy the link »: in the clipboard, said for a few seconds; without a clipboard, the link is
 * shown to copy by hand.
 */
export class OcdAmbassadorCopy extends Interaction {
    static selector = ".o_ocd_amb_copy[data-copy]";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.copy },
    };

    async copy() {
        const value = this.el.dataset.copy;
        try {
            await this.waitFor(navigator.clipboard.writeText(value));
        } catch {
            window.prompt("", value);
            return;
        }
        const done = document.querySelector(".o_ocd_amb_copied");
        if (done) {
            done.hidden = false;
            this.waitForTimeout(() => (done.hidden = true), SHOWN_MS);
        }
    }
}

registry.category("public.interactions").add("ocd_ambassadors.reco", OcdAmbassadorReco);
registry.category("public.interactions").add("ocd_ambassadors.share_text", OcdAmbassadorShareText);
registry.category("public.interactions").add("ocd_ambassadors.copy", OcdAmbassadorCopy);
