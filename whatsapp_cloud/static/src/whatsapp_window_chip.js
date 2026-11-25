import { ChatWindow } from "@mail/core/common/chat_window";
import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { computedUntilStale } from "@mail/utils/common/signal";
import { whatsappWindowLeft } from "@whatsapp_cloud/whatsapp_utils";

import { Component, t, useProps } from "@odoo/owl";

/**
 * « 2 h 15 left »: the time left to answer the customer of a WhatsApp conversation for free (the
 * 24-hour window after their last message), updated every minute, urgent the last hour. When the
 * window is closed: « 24 h passed » if `showClosed`, else nothing.
 */
export class WhatsappWindowChip extends Component {
    static template = "whatsapp_cloud.WindowChip";

    setup() {
        super.setup();
        this.props = useProps({
            channel: t.object(),
            compact: t.boolean().optional(),
            showClosed: t.boolean().optional(),
        });
        this.left = computedUntilStale(
            () => whatsappWindowLeft(this.props.channel.whatsapp_channel_valid_until),
            (left) => left?.ms
        );
    }
}

// Used in the header of the conversations, of the chat windows and in their list
// (whatsapp_window_chip.xml)
Object.assign(ChatWindow.components, { WhatsappWindowChip });
Object.assign(DiscussContent.components, { WhatsappWindowChip });
Object.assign(MessagingMenuItem.components, { WhatsappWindowChip });
