import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const STORAGE_KEY = "ocd_live_voice_language";

/**
 * Reads the page aloud: the recording of the chosen language when the team recorded one,
 * otherwise the voice of the phone in that language. The sentence is shown while it is read.
 * The chosen language is remembered on this browser.
 */
export class OcdLiveVoice extends Interaction {
    static selector = ".o_ocd_live_voice";
    dynamicContent = {
        ".o_ocd_live_voice_play": { "t-on-click": this.onPlay },
        ".o_ocd_lang_item": { "t-on-click": this.onChooseLanguage },
    };

    setup() {
        this.key = this.el.dataset.voiceKey;
        this.language = this.el.dataset.lang || "";
        this.menuEl = this.el.querySelector(".o_ocd_lang");
        this.captionEl = document.querySelector(".o_ocd_caption");
        let saved = null;
        try {
            saved = window.localStorage.getItem(STORAGE_KEY);
        } catch {
            // Storage blocked (private browsing): the first language is used
        }
        if (saved && this.el.querySelector(`.o_ocd_lang_item[data-code="${CSS.escape(saved)}"]`)) {
            this.setLanguage(saved);
        }
    }

    setLanguage(code) {
        this.language = code;
        if (!this.menuEl) {
            return;
        }
        this.menuEl.querySelector(".o_ocd_lang_code").textContent = code.toUpperCase();
        for (const item of this.menuEl.querySelectorAll(".o_ocd_lang_item")) {
            item.setAttribute("aria-checked", item.dataset.code === code ? "true" : "false");
        }
    }

    onChooseLanguage(ev) {
        this.setLanguage(ev.currentTarget.dataset.code);
        this.menuEl.open = false;
        try {
            window.localStorage.setItem(STORAGE_KEY, this.language);
        } catch {
            // Storage blocked: the choice is kept for this page only
        }
    }

    async onPlay() {
        if (this.captionEl && !this.captionEl.hidden) {
            // Second touch: stop and hide the sentence
            this.stop();
            return;
        }
        const data = await this.waitFor(rpc(`/ocd/voix/${encodeURIComponent(this.key)}`, { lang: this.language }));
        this.stop();
        if (this.captionEl) {
            if (data.text) {
                this.captionEl.textContent = data.text;
            }
            this.captionEl.hidden = false;
        }
        if (data.url) {
            this.audio = new Audio(data.url);
            this.audio.addEventListener("ended", () => this.hideCaption());
            this.audio.play();
        } else if (data.text && data.speech_code && window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(data.text);
            utterance.lang = data.speech_code;
            utterance.addEventListener("end", () => this.hideCaption());
            window.speechSynthesis.speak(utterance);
        } else {
            this.captionTimeout = this.waitForTimeout(() => this.hideCaption(), 6000);
        }
    }

    hideCaption() {
        if (this.captionEl) {
            this.captionEl.hidden = true;
        }
    }

    stop() {
        if (this.audio) {
            this.audio.pause();
            this.audio = null;
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        clearTimeout(this.captionTimeout);
        this.hideCaption();
    }

    destroy() {
        this.stop();
    }
}

registry.category("public.interactions").add("ocd_live.voice", OcdLiveVoice);
