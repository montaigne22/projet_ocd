import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

/**
 * A WhatsApp conversation laid out like WhatsApp, in Discuss and in the chat windows: the customer
 * on the left, the team on the right (every agent, not only the one reading), the notices in the
 * middle.
 */
patch(Message.prototype, {
    get isWhatsAppLayout() {
        return Boolean(this.props.thread?.channel?.isWhatsApp && !this.env.messageCard);
    },
    get isAlignedRight() {
        if (this.isWhatsAppLayout) {
            return this.props.message.isWhatsAppTeam;
        }
        return super.isAlignedRight;
    },
    get attClass() {
        const result = super.attClass;
        if (this.isWhatsAppLayout) {
            result["o-whatsapp-team"] = this.props.message.isWhatsAppTeam;
            result["o-whatsapp-customer"] = this.props.message.isWhatsAppCustomer;
        }
        return result;
    },
});
