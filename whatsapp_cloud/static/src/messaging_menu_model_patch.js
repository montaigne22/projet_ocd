import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

MENU_TABS.WHATSAPP = "whatsapp";

/** @type {MessagingMenu} */
const messagingMenuModelPatch = {
    setup() {
        super.setup(...arguments);
        this.whatsappTab = fields.One("MessagingMenuTab", {
            compute() {
                if (!this.store.has_access_whatsapp) {
                    return;
                }
                return {
                    id: MENU_TABS.WHATSAPP,
                    icon: "oi_whatsapp",
                    activeIcon: "oi_whatsapp",
                    label: _t("WhatsApp"),
                    sequence: 85,
                    emptyState: {
                        title: _t("No WhatsApp conversation"),
                        subtitle: _t(
                            "The conversations start when a customer writes to the WhatsApp number of the company."
                        ),
                    },
                    filters: [
                        {
                            id: "whatsapp_unread",
                            text: _t("Unread"),
                            includesChannel: (c) => c.isUnread,
                        },
                        {
                            id: "whatsapp_mine",
                            text: _t("Mine"),
                            includesChannel: (c) => c.whatsappIsMine,
                        },
                        {
                            id: "whatsapp_unassigned",
                            text: _t("Not assigned"),
                            includesChannel: (c) => !c.whatsapp_user_id && c.whatsapp_state !== "done",
                        },
                        {
                            id: "whatsapp_waiting",
                            text: _t("Waiting for an answer"),
                            includesChannel: (c) => Boolean(c.whatsapp_waiting_since),
                        },
                    ],
                    includesChannel: (c) =>
                        c.channel_type === "whatsapp" &&
                        (c.self_member_id?.is_pinned ||
                            c.isLocallyPinned ||
                            (!c.whatsapp_user_id && c.whatsapp_state !== "done")),
                    recordType: "discuss.channel",
                };
            },
            eager: true,
        });
    },
};
patch(MessagingMenu.prototype, messagingMenuModelPatch);
