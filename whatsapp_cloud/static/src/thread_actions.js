import { registerThreadAction } from "@mail/core/common/thread_actions";
import { joinChannelAction } from "@mail/discuss/core/public_web/thread_actions";
import { WhatsappInfoPanel } from "@whatsapp_cloud/whatsapp_info_panel";
import { callWhatsappAction } from "@whatsapp_cloud/whatsapp_utils";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const isWhatsappAgent = ({ channel, store }) =>
    channel?.channel_type === "whatsapp" && store.self_user?.share === false;

registerThreadAction("whatsapp-info", {
    actionPanelComponent: WhatsappInfoPanel,
    actionPanelComponentProps: ({ thread }) => ({ thread }),
    actionPanelOuterClass: "o-whatsapp-InfoPanel bg-inherit",
    condition: (params) => isWhatsappAgent(params) && !params.owner.isDiscussSidebarChannelActions,
    icon: "info",
    name: _t("Customer"),
    sequence: 10,
    sequenceGroup: 7,
});

registerThreadAction("whatsapp-send-template", {
    condition: (params) => isWhatsappAgent(params) && !params.owner.isDiscussSidebarChannelActions,
    icon: "oi_whatsapp",
    name: _t("Send a template"),
    onSelected: ({ channel, store }) =>
        callWhatsappAction(store, channel, "whatsapp_action_send_template"),
    sequence: 20,
    sequenceGroup: 7,
});

registerThreadAction("whatsapp-resolve", {
    condition: (params) =>
        isWhatsappAgent(params) &&
        params.channel.whatsapp_state !== "done" &&
        !params.owner.isDiscussSidebarChannelActions,
    icon: "task_alt",
    name: _t("Mark as resolved"),
    onSelected: ({ channel, store }) => callWhatsappAction(store, channel, "whatsapp_action_resolve"),
    sequence: 30,
    sequenceGroup: 7,
});

// For a WhatsApp conversation, "join" means taking it: the agent handles it.
patch(joinChannelAction, {
    name({ channel }) {
        if (channel?.channel_type === "whatsapp") {
            return _t("Take the conversation");
        }
        return typeof super.name === "function" ? super.name(...arguments) : super.name;
    },
    onSelected({ channel, store }) {
        if (channel?.channel_type === "whatsapp") {
            return callWhatsappAction(store, channel, "whatsapp_action_take");
        }
        return super.onSelected(...arguments);
    },
});
