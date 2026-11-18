import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * A clip on the product page (« Seen in live ») or the replay: its image only; the video (about
 * 6 MB) loads at the touch, in a viewer over the page. The play is told once per page to the
 * figures of the vendor.
 */
export class OcdClipPlayer extends Interaction {
    static selector = ".o_ocd_clip_open[data-video]";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.open },
    };

    setup() {
        this.counted = false;
    }

    viewer() {
        let dialog = document.querySelector("dialog.o_ocd_clip_viewer");
        if (!dialog) {
            dialog = document.createElement("dialog");
            dialog.className = "o_ocd_clip_viewer";
            dialog.setAttribute("aria-label", _t("Clip"));
            const video = document.createElement("video");
            video.controls = true;
            video.playsInline = true;
            video.preload = "none";
            const close = document.createElement("button");
            close.type = "button";
            close.className = "o_ocd_clip_viewer_close";
            close.setAttribute("aria-label", _t("Close"));
            close.textContent = "×";
            close.addEventListener("click", () => dialog.close());
            dialog.addEventListener("click", (ev) => ev.target === dialog && dialog.close());
            dialog.addEventListener("close", () => {
                video.pause();
                video.removeAttribute("src");
                video.load();
            });
            dialog.append(video, close);
            document.body.appendChild(dialog);
        }
        return dialog;
    }

    open() {
        const dialog = this.viewer();
        const video = dialog.querySelector("video");
        video.src = this.el.dataset.video;
        const poster = this.el.querySelector("img")?.src;
        if (poster) {
            video.poster = poster;
        }
        if (dialog.showModal) {
            dialog.showModal();
        } else {
            dialog.setAttribute("open", "open");
        }
        video.play().catch(() => {});
        this.count();
    }

    count() {
        const url = this.el.dataset.count;
        if (this.counted || !url) {
            return;
        }
        this.counted = true;
        if (!navigator.sendBeacon?.(url)) {
            fetch(url, { method: "POST", keepalive: true }).catch(() => {});
        }
    }
}

registry.category("public.interactions").add("ocd_clips.clip_player", OcdClipPlayer);
