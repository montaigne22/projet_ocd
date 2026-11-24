import { Composer } from "@mail/core/common/composer";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

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
});
