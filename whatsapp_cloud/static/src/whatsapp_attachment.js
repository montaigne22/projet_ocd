import { Component, onWillUnmount, proxy, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { humanSize } from "@web/core/utils/binary";
import { url } from "@web/core/utils/urls";

/** The sound playing now: one at a time, like in WhatsApp. */
let playingAudio = null;

const RATES = [1, 1.5, 2];

function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) {
        return "0:00";
    }
    const total = Math.floor(seconds);
    const minutes = Math.floor(total / 60);
    const rest = String(total % 60).padStart(2, "0");
    return minutes >= 60
        ? `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, "0")}:${rest}`
        : `${minutes}:${rest}`;
}

/** "audio", "video" or "document": how WhatsApp shows a file that is not an image. */
export function whatsappMediaKind(attachment) {
    const mimetype = (attachment.mimetype || "").split(";")[0];
    if (mimetype.startsWith("audio/")) {
        return "audio";
    }
    if (mimetype.startsWith("video/")) {
        return "video";
    }
    return "document";
}

/**
 * A file of a WhatsApp conversation shown like in WhatsApp, inside the conversation: a sound as a
 * small player (play, progress to move in it, time, speed), a video played in place, a document as a
 * line (icon, name, type and size; opened in the viewer of Odoo when it can, else downloaded). The
 * file is read from Odoo as it plays (no download first); when the browser cannot play it, it says
 * so and offers the download.
 */
export class WhatsAppAttachment extends Component {
    static template = "whatsapp_cloud.WhatsAppAttachment";
    props = useProps({
        attachment: t.any(),
        open: t.function().optional(),
    });

    setup() {
        this.state = proxy({ playing: false, current: 0, duration: 0, rate: 1, error: false });
        this.media = signal.ref();
        onWillUnmount(() => {
            const media = this.media();
            if (media && playingAudio === media) {
                playingAudio = null;
            }
            media?.pause?.();
        });
    }

    get attachment() {
        return this.props.attachment;
    }
    get kind() {
        return whatsappMediaKind(this.attachment);
    }
    get src() {
        return url(this.attachment.urlRoute, this.attachment.urlQueryParams);
    }
    get downloadUrl() {
        return this.attachment.downloadUrl;
    }
    get poster() {
        return this.attachment.has_thumbnail ? this.attachment.thumbnailUrl : undefined;
    }
    get typeLabel() {
        const name = this.attachment.name || "";
        const dot = name.lastIndexOf(".");
        if (dot > 0 && dot > name.length - 7) {
            return name.slice(dot + 1).toUpperCase();
        }
        const subtype = (this.attachment.mimetype || "").split(";")[0].split("/")[1] || "";
        return subtype.length <= 6 ? subtype.toUpperCase() : _t("File");
    }
    get sizeLabel() {
        return this.attachment.file_size ? humanSize(this.attachment.file_size) : "";
    }
    get timeLabel() {
        const { playing, current, duration } = this.state;
        return formatTime(playing || current ? current : duration);
    }
    get rateLabel() {
        return `${this.state.rate}×`;
    }
    get playTitle() {
        return this.state.playing ? _t("Pause") : _t("Play");
    }

    // === SOUND === //

    togglePlay() {
        const audio = this.media();
        if (!audio || this.state.error) {
            return;
        }
        if (audio.paused) {
            if (playingAudio && playingAudio !== audio) {
                playingAudio.pause();
            }
            playingAudio = audio;
            audio.playbackRate = this.state.rate;
            audio.play().catch(() => {});
        } else {
            audio.pause();
        }
    }
    onSeek(ev) {
        const audio = this.media();
        const value = Number(ev.target.value);
        if (audio && Number.isFinite(value)) {
            audio.currentTime = value;
            this.state.current = value;
        }
    }
    cycleRate() {
        const next = RATES[(RATES.indexOf(this.state.rate) + 1) % RATES.length];
        this.state.rate = next;
        const audio = this.media();
        if (audio) {
            audio.playbackRate = next;
        }
    }
    onLoadedMetadata() {
        const duration = this.media()?.duration;
        this.state.duration = Number.isFinite(duration) ? duration : 0;
    }
    onTimeUpdate() {
        const audio = this.media();
        if (audio) {
            this.state.current = audio.currentTime;
            if (!this.state.duration && Number.isFinite(audio.duration)) {
                this.state.duration = audio.duration;
            }
        }
    }
    onPlay() {
        this.state.playing = true;
    }
    onPause() {
        this.state.playing = false;
    }
    onEnded() {
        this.state.playing = false;
        this.state.current = 0;
        if (playingAudio === this.media()) {
            playingAudio = null;
        }
    }
    onError() {
        this.state.error = true;
        this.state.playing = false;
    }

    // === DOCUMENT === //

    onKeydownDocument(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.onClickDocument();
        }
    }
    onClickDocument() {
        if (this.attachment.isViewable && this.props.open) {
            this.props.open();
        } else {
            window.open(this.downloadUrl, "_self");
        }
    }
}
