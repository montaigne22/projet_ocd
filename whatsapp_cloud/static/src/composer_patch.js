import { Composer } from "@mail/core/common/composer";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** In a WhatsApp conversation, the composer says how to write an internal note (/note). */
patch(Composer.prototype, {
    get placeholder() {
        const channel = this.thread?.channel;
        if (!this.props.placeholder && channel?.isWhatsApp && this.store.self_user?.share === false) {
            return _t("Message to %(name)s… (/note: an internal note, not sent)", { name: channel.displayName });
        }
        return super.placeholder;
    },
});
