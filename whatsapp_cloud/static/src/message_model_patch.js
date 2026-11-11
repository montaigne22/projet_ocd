import { Message } from "@mail/core/common/message_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const STATUS = {
    queued: { icon: "schedule", label: _t("Being sent") },
    sent: { icon: "check", label: _t("Sent") },
    delivered: { icon: "done_all", label: _t("Delivered") },
    read: { icon: "done_all", label: _t("Read") },
    failed: { icon: "error", label: _t("Not delivered") },
    skipped: { icon: "block", label: _t("Not sent") },
};

/** @type {import("models").Message} */
const messagePatch = {

    get whatsappStatus() {
        return this.whatsapp_status ? STATUS[this.whatsapp_status] : undefined;
    },
    get whatsappStatusTitle() {
        const status = this.whatsappStatus;
        if (!status) {
            return "";
        }
        return this.whatsapp_error ? `${status.label}: ${this.whatsapp_error}` : status.label;
    },
    get canReplyTo() {
        if (this.thread?.channel?.channel_type === "whatsapp") {
            return (
                !this.isEmpty &&
                this.message_type !== "notification" &&
                !this.thread.channel.composerHidden
            );
        }
        return super.canReplyTo;
    },
};
patch(Message.prototype, messagePatch);
