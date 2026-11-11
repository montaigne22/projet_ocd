import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * "Share" button of the image that announces a live: the share sheet of the phone gets the
 * image itself (WhatsApp, status, Facebook...). The image is fetched as soon as the page is
 * shown, because the phones open the share sheet only right after the tap. Without sharing of
 * files, the text and the link are shared; without any sharing, the image is downloaded.
 */
export class OcdLiveShareFile extends Interaction {
    static selector = ".o_ocd_share_file";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.share },
    };

    setup() {
        this.file = null;
    }

    start() {
        this.loading = this.load();
    }

    async load() {
        const { ocdUrl, ocdName } = this.el.dataset;
        try {
            const response = await this.waitFor(fetch(ocdUrl, { credentials: "same-origin" }));
            if (!response.ok) {
                return;
            }
            const blob = await this.waitFor(response.blob());
            this.file = new File([blob], ocdName || "ocd-live.png", { type: blob.type || "image/png" });
        } catch {
            this.file = null;
        }
    }

    async share() {
        const { ocdText, ocdLink } = this.el.dataset;
        if (!this.file) {
            await this.waitFor(this.loading);
        }
        try {
            if (this.file && navigator.canShare?.({ files: [this.file] })) {
                await this.waitFor(navigator.share({ files: [this.file], text: ocdText }));
                return;
            }
            if (navigator.share) {
                await this.waitFor(navigator.share({ text: ocdText, url: ocdLink }));
                return;
            }
        } catch (error) {
            if (error?.name === "AbortError") {
                return; // the person closed the share sheet
            }
        }
        this.download();
    }

    download() {
        const link = document.createElement("a");
        link.href = this.el.dataset.ocdDownload;
        link.download = this.el.dataset.ocdName || "";
        document.body.appendChild(link);
        link.click();
        link.remove();
    }
}

registry.category("public.interactions").add("ocd_live.share_file", OcdLiveShareFile);
