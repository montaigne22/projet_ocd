import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { callWhatsappAction } from "@whatsapp_cloud/whatsapp_utils";

import { Component, proxy, t, useOnChange, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/** Information on the customer of a WhatsApp conversation, and the actions on it. */
export class WhatsappInfoPanel extends Component {
    static components = { ActionPanel };
    static template = "whatsapp_cloud.WhatsappInfoPanel";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.props = useProps({
            close: t.function().optional(),
            thread: t.object(),
        });
        this.state = proxy({ info: null, loading: true });
        useOnChange(
            () => [
                this.props.thread,
                this.channel.whatsapp_partner_id,
                this.channel.whatsapp_user_id,
                this.channel.whatsapp_to_identify,
            ],
            () => this.load()
        );
    }

    get channel() {
        return this.props.thread.channel;
    }

    get validUntilText() {
        return this.channel.whatsapp_channel_valid_until?.toLocaleString(
            luxon.DateTime.DATETIME_SHORT
        );
    }

    get waitingSinceText() {
        return this.channel.whatsapp_waiting_since?.toLocaleString(luxon.DateTime.DATETIME_SHORT);
    }

    async load() {
        this.state.loading = true;
        this.state.info = await this.orm.call("discuss.channel", "whatsapp_get_info", [
            [this.channel.id],
        ]);
        this.state.loading = false;
    }

    async call(method, args = []) {
        await callWhatsappAction(this.store, this.channel, method, args);
        await this.load();
    }

    async toggleTag(tag) {
        const ids = this.state.info.tags.map((t) => t.id);
        const tagIds = ids.includes(tag.id) ? ids.filter((id) => id !== tag.id) : [...ids, tag.id];
        await this.call("whatsapp_action_set_tags", [tagIds]);
    }

    hasTag(tag) {
        return this.state.info.tags.some((t) => t.id === tag.id);
    }

    openRecord(item) {
        this.store.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: item.model,
            res_id: item.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
