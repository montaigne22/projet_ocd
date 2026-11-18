import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * « Share » of a clip in the space of the vendor (design ClipsAutomatiques): the share sheet of
 * the phone gets the video itself (WhatsApp status, TikTok, Reels, Facebook) and its text, also
 * copied (TikTok and Reels keep only the video: the vendor pastes the text). The video (about
 * 6 MB) is fetched at the first touch of the button, or when it plays; a phone that asks for a
 * second touch once the video is there gets it. Without sharing of files, the video is saved.
 */
export class OcdClipShare extends Interaction {
    static selector = ".o_ocd_clip_share_file";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.share, "t-on-pointerdown": this.prepare },
    };

    setup() {
        this.file = null;
        this.loading = null;
        this.label = this.el.querySelector("span");
        this.text = this.label?.textContent;
    }

    start() {
        const video = document.querySelector(".o_ocd_clip_video video");
        if (video) {
            this.addListener(video, "play", () => this.prepare());
        }
    }

    prepare() {
        if (!this.loading && navigator.canShare) {
            const { video, name } = this.el.dataset;
            this.loading = fetch(video, { credentials: "same-origin" })
                .then((response) => (response.ok ? response.blob() : null))
                .then((blob) => {
                    this.file = blob ? new File([blob], name || "ocd-live.mp4", { type: "video/mp4" }) : null;
                    return this.file;
                })
                .catch(() => null);
        }
        return this.loading;
    }

    copied() {
        const box = document.querySelector(".o_ocd_clip_copied");
        if (box) {
            box.hidden = false;
        }
    }

    async share() {
        const { text, link } = this.el.dataset;
        // The text first, while the touch is fresh: TikTok and Reels keep only the video
        navigator.clipboard?.writeText(text).then(() => this.copied(), () => {});
        if (navigator.canShare) {
            if (!this.file) {
                this.setLabel(_t("Preparing the clip…"));
                await this.waitFor(this.prepare());
                this.setLabel(this.text);
            }
            if (this.file && navigator.canShare({ files: [this.file] })) {
                try {
                    await this.waitFor(navigator.share({ files: [this.file], text }));
                    return;
                } catch (error) {
                    if (error?.name === "AbortError") {
                        return;
                    }
                    if (error?.name === "NotAllowedError") {
                        // The video took long: the phone wants a new touch
                        this.setLabel(_t("Ready: touch again to share"));
                        return;
                    }
                }
            }
        }
        if (navigator.share) {
            try {
                await this.waitFor(navigator.share({ text, url: link }));
                return;
            } catch (error) {
                if (error?.name === "AbortError") {
                    return;
                }
            }
        }
        this.download();
    }

    setLabel(text) {
        if (this.label) {
            this.label.textContent = text;
        }
    }

    download() {
        const anchor = document.createElement("a");
        anchor.href = this.el.dataset.download;
        anchor.download = this.el.dataset.name || "";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
    }
}

registry.category("public.interactions").add("ocd_clips.clip_share", OcdClipShare);
