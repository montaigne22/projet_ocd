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
    /** In a WhatsApp conversation: written by the customer (on the left, like in WhatsApp). */
    get isWhatsAppCustomer() {
        const channel = this.thread?.channel;
        return Boolean(
            channel?.isWhatsApp && this.author_id && this.author_id.id === channel.whatsapp_partner_id
        );
    },
    /**
     * In a WhatsApp conversation: a message of the team to the customer (on the right, in green),
     * whoever wrote it (any agent, an automatic answer, a template); not the notices nor the notes.
     */
    get isWhatsAppTeam() {
        const channel = this.thread?.channel;
        if (
            !channel?.isWhatsApp ||
            ["notification", "tracking"].includes(this.message_type) ||
            this.isNote ||
            this.isWhatsAppCustomer
        ) {
            return false;
        }
        return channel.whatsapp_partner_id ? true : this.isSelfAuthored;
    },
    /** In a WhatsApp conversation: an internal note of the team (/note), never sent to the
     * customer: in the middle, in yellow. */
    get isWhatsAppNote() {
        return Boolean(this.thread?.channel?.isWhatsApp && this.isNote);
    },
    get bubbleColor() {
        if (this.isWhatsAppNote) {
            return "orange";
        }
        if (this.thread?.channel?.isWhatsApp && !this.isHighlightedFromMention) {
            if (this.isWhatsAppTeam) {
                return "green";
            }
            if (this.isWhatsAppCustomer) {
                return "blue";
            }
        }
        return super.bubbleColor;
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
