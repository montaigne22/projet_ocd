import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("note", {
    condition: ({ channel, store }) =>
        channel?.channel_type === "whatsapp" && store.self_user?.share === false,
    help: _t("Internal note, not sent to the customer"),
    methodName: "execute_command_note",
});
