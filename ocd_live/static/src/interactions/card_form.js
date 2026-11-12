import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * My card in the lives: the name of the file chosen shows under its button, a video too heavy
 * is refused before it is sent (a phone video can weigh a lot), and while the form is sent the
 * button waits (the server prepares the video, it can take a minute).
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

    onSubmit() {
        const button = this.el.querySelector("button[type=submit]");
        if (button) {
            // After the form has left: a disabled button would not be sent with it
            setTimeout(() => (button.disabled = true));
        }
        const sending = this.el.querySelector(".o_ocd_card_sending");
        if (sending) {
            sending.hidden = false;
        }
    }
}

registry.category("public.interactions").add("ocd_live.card_form", OcdCardForm);
