import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.whatsapp_channel_valid_until = fields.Datetime();
        this.whatsapp_waiting_since = fields.Datetime();
        /** Changes when the 24-hour window closes, to show it without reloading. */
        this.whatsappWindowTick = 0;
        this.onChange(
            () => [this.whatsapp_channel_valid_until],
            function refreshWhenWindowCloses(validUntil) {
                if (!validUntil) {
                    return;
                }
                const delay = validUntil.diff(DateTime.now()).as("milliseconds");
                if (delay <= 0 || delay > 2 ** 31 - 1) {
                    return;
                }
                const timeout = setTimeout(() => this.whatsappWindowTick++, delay + 1000);
                return () => clearTimeout(timeout);
            }
        );
    },

    get isWhatsApp() {
        return this.channel_type === "whatsapp";
    },
    get whatsappWindowOpen() {
        void this.whatsappWindowTick;
        return Boolean(
            this.whatsapp_channel_valid_until && this.whatsapp_channel_valid_until > DateTime.now()
        );
    },
    get whatsappIsMine() {
        return Boolean(this.whatsapp_user_id && this.whatsapp_user_id === this.store.self_user?.id);
    },
    get whatsappStateLabel() {
        return (
            {
                new: _t("New"),
                open: _t("In progress"),
                done: _t("Resolved"),
            }[this.whatsapp_state] || ""
        );
    },
    computeCorrespondent() {
        if (this.isWhatsApp) {
            const customer = this.channel_member_ids.find(
                (member) => member.partner_id?.id === this.whatsapp_partner_id
            );
            return customer || super.computeCorrespondent();
        }
        return super.computeCorrespondent();
    },
    get importantCounter() {
        if (this.isWhatsApp) {
            return this.self_member_id?.message_unread_counter_ui || 0;
        }
        return super.importantCounter;
    },
    get autoOpenChatWindowOnNewMessage() {
        return (
            (this.isWhatsApp && !this.store.chatHub.compact && Boolean(this.self_member_id)) ||
            super.autoOpenChatWindowOnNewMessage
        );
    },
    get inChathubOnNewMessage() {
        if (this.isWhatsApp) {
            return Boolean(this.self_member_id);
        }
        return super.inChathubOnNewMessage;
    },
    get composerHidden() {
        if (this.isWhatsApp) {
            return !this.self_member_id || !this.whatsappWindowOpen;
        }
        return super.composerHidden;
    },
    get composerHiddenText() {
        if (this.isWhatsApp) {
            if (!this.self_member_id) {
                return _t("Take the conversation to answer the customer.");
            }
            return _t(
                "More than 24 hours since the last message of the customer: WhatsApp allows only a template now (Send a template)."
            );
        }
        return super.composerHiddenText;
    },
    showThreadIcon() {
        return this.isWhatsApp || super.showThreadIcon(...arguments);
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
