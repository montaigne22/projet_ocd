import { Component, onMounted, onWillStart, onWillUnmount, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

// While a video is checked or clips are made, the screen asks again every few seconds
const REFRESH_SECONDS = 5;
// A piece that does not arrive is sent again, waiting longer each time
const RETRY_SECONDS = [2, 4, 8, 15, 30, 30, 30, 60, 60, 60];

function sizeText(bytes) {
    if (bytes >= 1024 ** 3) {
        return _t("%s GB", (bytes / 1024 ** 3).toFixed(1));
    }
    return _t("%s MB", Math.max(1, Math.round(bytes / 1024 ** 2)));
}

/**
 * « Video of the live and clips » (design ClipsAutomatiques): the team sends the video of a live
 * in pieces of 8 MB; a piece that does not arrive is sent again, and the same file chosen again
 * after closing the page goes on where it stopped. The parts of the video and their shift (with
 * a preview of the first moment), then the clips of the live: See, Make again, Hide.
 */
export class OcdClipsScreen extends Component {
    static template = "ocd_clips.Screen";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    sending = signal(null);
    playing = signal(null);
    previewStamp = signal(0);

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.bookingId = this.props.action?.params?.booking_id || this.props.action?.context?.active_id;
        onWillStart(() => this.load());
        onMounted(() => {
            this.refresher = setInterval(() => this.data()?.busy && !this.sending() && this.load(true), REFRESH_SECONDS * 1000);
        });
        onWillUnmount(() => {
            clearInterval(this.refresher);
            this.stopped = true;
        });
    }

    /** `silent`: the refresh while the clips are made, without the « Loading… » of Odoo each time. */
    async load(silent = false) {
        const orm = silent ? this.orm.silent : this.orm;
        this.data.set(await orm.call("ocd.live.booking", "ocd_clips_screen_data", [[this.bookingId]]));
    }

    async call(method, ...args) {
        this.data.set(await this.orm.call("ocd.live.booking", method, [[this.bookingId], ...args]));
    }

    // === SENDING THE VIDEO === //

    async onFile(ev) {
        const file = ev.target.files?.[0];
        ev.target.value = "";
        if (!file || this.sending()) {
            return;
        }
        if (file.size > this.data().max_bytes) {
            this.notification.add(_t("The video is too heavy: 4 GB at most."), { type: "danger" });
            return;
        }
        let part;
        try {
            part = await this.orm.call("ocd.live.booking", "ocd_clips_start_upload", [[this.bookingId], file.name, file.size]);
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("The video could not be sent."), { type: "danger" });
            return;
        }
        await this.send(file, part);
    }

    async send(file, part) {
        const chunk = this.data().chunk_bytes;
        let received = part.received;
        this.sending.set({ name: file.name, received, total: file.size, line: "" });
        while (received < file.size && !this.stopped) {
            const piece = file.slice(received, Math.min(received + chunk, file.size));
            const answer = await this.sendPiece(part, received, piece);
            if (!answer) {
                this.sending.set(null);
                this.notification.add(_t("Sending stopped: choose the same file again to go on where it stopped."), {
                    type: "warning",
                    sticky: true,
                });
                await this.load();
                return;
            }
            received = answer.received;
            this.sending.set({ name: file.name, received, total: file.size, line: "" });
        }
        this.sending.set(null);
        if (received >= file.size) {
            this.notification.add(_t("Video received: it is checked, then the clips are made."), { type: "success" });
        }
        await this.load();
    }

    async sendPiece(part, offset, piece) {
        const url = `/ocd/clips/envoi/${part.id}?token=${encodeURIComponent(part.token)}&offset=${offset}`;
        for (let attempt = 0; attempt <= RETRY_SECONDS.length; attempt++) {
            try {
                const response = await fetch(url, {
                    method: "POST",
                    body: piece,
                    headers: { "Content-Type": "application/octet-stream" },
                    credentials: "same-origin",
                });
                if (response.ok) {
                    return await response.json();
                }
            } catch {
                // The network cut: sent again below
            }
            if (this.stopped || attempt === RETRY_SECONDS.length) {
                return null;
            }
            const seconds = RETRY_SECONDS[attempt];
            this.sending.set({
                ...this.sending(),
                line: _t("The network cut: tries again in %s s.", seconds),
            });
            await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
        }
        return null;
    }

    get sendingPercent() {
        const sending = this.sending();
        return sending ? Math.floor((sending.received * 100) / Math.max(sending.total, 1)) : 0;
    }

    get sendingLine() {
        const sending = this.sending();
        return _t("%(received)s of %(total)s sent", {
            received: sizeText(sending.received),
            total: sizeText(sending.total),
        });
    }

    // === THE PARTS === //

    async shift(part, seconds) {
        await this.call("ocd_clips_shift", part.id, seconds);
        this.previewStamp.set(Date.now());
    }

    async removePart(part) {
        if (!window.confirm(_t("Remove this part of the video? Its clips are planned again."))) {
            return;
        }
        await this.call("ocd_clips_remove_part", part.id);
    }

    get previewUrl() {
        return `/ocd/clips/apercu/${this.bookingId}?t=${this.previewStamp() || this.data().updated_at}`;
    }

    // === THE CLIPS === //

    async act(clip, what) {
        await this.call("ocd_clips_act", clip.id, what);
    }

    see(clip) {
        this.playing.set(clip);
    }

    close() {
        this.playing.set(null);
    }
}

registry.category("actions").add("ocd_clips.screen", OcdClipsScreen);
