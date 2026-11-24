import { Component, onMounted, proxy, signal, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";

/**
 * Listen to a message of the calls or to a recording in Odoo itself: a small window with the
 * player of the browser, no new tab (a tab opened after the answer of the server is often taken
 * for a pop-up and blocked: Safari, Firefox, the mobile app, a blocker).
 */
export class AudioPlayerDialog extends Component {
    static template = "whatsapp_cloud_call.AudioPlayerDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        title: t.string().optional(""),
        url: t.string(),
        downloadUrl: t.string().optional(""),
        fileName: t.string().optional(""),
    });

    setup() {
        this.state = proxy({ error: false });
        this.audio = signal.ref();
        onMounted(() => {
            const playing = this.audio()?.play();
            // the browser may refuse to start by itself: the play button of the player is there
            playing?.catch?.(() => {});
        });
    }

    onError() {
        this.state.error = true;
    }
}

/** ir.actions.client "whatsapp_call_audio": params {title, url, download_url, file_name}. */
export function audioPlayerAction(env, action) {
    const params = action.params || {};
    if (!params.url) {
        return;
    }
    env.services.dialog.add(AudioPlayerDialog, {
        title: params.title || "",
        url: params.url,
        downloadUrl: params.download_url || "",
        fileName: params.file_name || "",
    });
}

registry.category("actions").add("whatsapp_call_audio", audioPlayerAction);
