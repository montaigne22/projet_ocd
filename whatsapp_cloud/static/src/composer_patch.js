import { Composer } from "@mail/core/common/composer";
import { registerComposerAction } from "@mail/core/common/composer_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { callWhatsappAction } from "./whatsapp_utils";

const isWhatsAppComposer = ({ composer, store }) =>
    Boolean(composer.targetThread?.channel?.isWhatsApp && store.self_user?.share === false && !composer.message);

/**
 * "Send a template" at the bottom of a WhatsApp conversation, next to the emojis and Send: a
 * template goes at any time (a ticket, an order...). When the 24-hour window is closed, the bar
 * above the composer offers it instead (composer_patch.xml).
 */
registerComposerAction("whatsapp-send-template", {
    condition: (params) => isWhatsAppComposer(params) && !params.composer.targetThread.channel.whatsappNoteOnly,
    disabledCondition: ({ owner }) => owner.areAllActionsDisabled,
    icon: "oi_whatsapp",
    name: _t("Send a template"),
    onSelected: ({ composer, store }) =>
        callWhatsappAction(store, composer.targetThread.channel, "whatsapp_action_send_template"),
    sequenceQuick: 15,
});

/**
 * In a WhatsApp conversation, the composer says what it writes: a message to the customer (and
 * /note for an internal note), or, more than 24 hours after their last message, an internal note
 * only (the customer is written to with a template).
 */
patch(Composer.prototype, {
    get placeholder() {
        const channel = this.thread?.channel;
        if (!this.props.placeholder && channel?.isWhatsApp && this.store.self_user?.share === false) {
            if (channel.whatsappNoteOnly) {
                return _t("Internal note… (more than 24 h: write to the customer with a template)");
            }
            return _t("Message to %(name)s… (/note: an internal note, not sent)", { name: channel.displayName });
        }
        return super.placeholder;
    },
    onClickWhatsappTemplate() {
        return callWhatsappAction(this.store, this.thread.channel, "whatsapp_action_send_template");
    },
});
