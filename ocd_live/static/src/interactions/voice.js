import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const STORAGE_KEY = "ocd_live_voice_language";

/**
 * Reads the page aloud: the recording of the chosen language when the team recorded one,
 * otherwise the voice of the phone in that language. The chosen language is remembered.
 */
export class OcdLiveVoice extends Interaction {
    static selector = ".o_ocd_live_voice";
    dynamicContent = {
        ".o_ocd_live_voice_play": { "t-on-click": this.onPlay },
        ".o_ocd_live_voice_lang": { "t-on-change": this.onChangeLanguage },
    };

    setup() {
        this.key = this.el.dataset.voiceKey;
        this.languageEl = this.el.querySelector(".o_ocd_live_voice_lang");
        let saved = null;
        try {
            saved = window.localStorage.getItem(STORAGE_KEY);
        } catch {
            // Storage blocked (private browsing): the first language is used
        }
        if (saved && this.languageEl && [...this.languageEl.options].some((o) => o.value === saved)) {
            this.languageEl.value = saved;
        }
    }

    onChangeLanguage() {
        try {
            window.localStorage.setItem(STORAGE_KEY, this.languageEl.value);
        } catch {
            // Storage blocked: the choice is kept for this page only
        }
    }

    async onPlay() {
        const language = this.languageEl ? this.languageEl.value : "";
        const data = await this.waitFor(rpc(`/ocd/voix/${encodeURIComponent(this.key)}`, { lang: language }));
        this.stop();
        if (data.url) {
            this.audio = new Audio(data.url);
            this.audio.play();
        } else if (data.text && data.speech_code && window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(data.text);
            utterance.lang = data.speech_code;
            window.speechSynthesis.speak(utterance);
        }
    }

    stop() {
        if (this.audio) {
            this.audio.pause();
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
    }

    destroy() {
        this.stop();
    }
}

registry.category("public.interactions").add("ocd_live.voice", OcdLiveVoice);
