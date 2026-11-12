import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * My card in the lives: the name of the file chosen shows under its button, a video too heavy
 * is refused before it is sent (a phone video can weigh a lot), and the form is sent with its
 * progress; the server then prepares the video in the background (the page says it).
 */
export class OcdCardForm extends Interaction {
    static selector = ".o_ocd_card_form";
    dynamicContent = {
        ".o_ocd_card_file": { "t-on-change": this.onFile },
        _root: { "t-on-submit": this.onSubmit },
    };

    setup() {
        this.maxVideoBytes = Number(this.el.dataset.maxVideoMb || 60) * 1024 * 1024;
    }

    onFile(ev) {
        const input = ev.currentTarget;
        const section = input.closest(".o_ocd_card_upload");
        const file = input.files?.[0];
        const nameEl = section.querySelector(".o_ocd_card_file_name");
        const tooBigEl = section.querySelector(".o_ocd_card_too_big");
        const tooBig = Boolean(file && input.dataset.kind === "video" && file.size > this.maxVideoBytes);
        if (tooBigEl) {
            tooBigEl.hidden = !tooBig;
        }
        if (tooBig) {
            input.value = "";
        }
        if (nameEl) {
            nameEl.textContent = file && !tooBig ? file.name : "";
        }
        // A new file replaces the current one: no « remove » with it
        const remove = section.querySelector("input[type=checkbox]");
        if (remove && file && !tooBig) {
            remove.checked = false;
        }
    }

    /** With a file chosen, the form is sent in the background with its progress (a video of a
     * phone takes time on a mobile network), then the page opens again; a refusal of the server
     * or of the network says what to do. Without one, the form is sent as usual. */
    onSubmit(ev) {
        const withFile = [...this.el.querySelectorAll(".o_ocd_card_file")].some((input) => input.files?.length);
        this.show(".o_ocd_card_failed", false);
        this.show(".o_ocd_card_refused", false);
        if (!withFile || !window.FormData || !window.XMLHttpRequest) {
            this.wait(true);
            return;
        }
        ev.preventDefault();
        const request = new XMLHttpRequest();
        request.open("POST", this.el.action);
        request.upload.addEventListener("progress", (progress) => {
            if (progress.lengthComputable) {
                this.progress(progress.loaded / progress.total);
            }
        });
        request.addEventListener("load", () => {
            if (request.status >= 200 && request.status < 400 && request.responseURL) {
                window.location.assign(request.responseURL);
                return;
            }
            this.wait(false);
            this.show(request.status === 413 ? ".o_ocd_card_refused" : ".o_ocd_card_failed", true);
        });
        request.addEventListener("error", () => {
            this.wait(false);
            this.show(".o_ocd_card_failed", true);
        });
        this.wait(true);
        this.progress(0);
        request.send(new FormData(this.el));
    }

    show(selector, visible) {
        const el = this.el.querySelector(selector);
        if (el) {
            el.hidden = !visible;
        }
    }

    wait(on) {
        const button = this.el.querySelector("button[type=submit]");
        if (button) {
            // After the form has left: a disabled button would not be sent with it
            setTimeout(() => (button.disabled = on));
        }
        this.show(".o_ocd_card_sending", on);
        this.show(".o_ocd_card_progress", on);
    }

    progress(share) {
        const percent = Math.round(Math.min(Math.max(share, 0), 1) * 100);
        const bar = this.el.querySelector(".o_ocd_card_progress_bar i");
        if (bar) {
            bar.style.width = `${percent}%`;
        }
        const value = this.el.querySelector(".o_ocd_card_progress_value");
        if (value) {
            value.textContent = `${percent} %`;
        }
    }
}

registry.category("public.interactions").add("ocd_live.card_form", OcdCardForm);
