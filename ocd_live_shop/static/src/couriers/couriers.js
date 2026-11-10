import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const COURIERS = "ocd_live_shop.res_partner_action_ocd_courier";

/**
 * Couriers and cash, as in the validated design (BoLivreurs): a card per OCD courier, then the
 * cash of the evening to count for each of them.
 */
export class OcdLiveCouriers extends Component {
    static template = "ocd_live_shop.Couriers";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    amounts = signal({});

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        onWillStart(() => this.load());
    }

    async load() {
        this.data.set(await this.orm.call("ocd.live.couriers", "get_couriers_data", []));
    }

    countLabel(count) {
        return count === 1 ? _t("1 courier") : _t("%s couriers", count);
    }

    money(amount) {
        return formatMonetary(amount, { currencyId: this.data().currency_id });
    }

    amountOf(row) {
        return this.amounts()[row.id] ?? String(row.due);
    }

    setAmount(row, value) {
        this.amounts.set({ ...this.amounts(), [row.id]: value });
    }

    gap(row) {
        const given = parseFloat(String(this.amountOf(row)).replace(/\s/g, "").replace(",", ".")) || 0;
        return given - row.due;
    }

    async setStatus(card, status) {
        await this.orm.call("ocd.live.couriers", "ocd_set_status", [card.id, status]);
        await this.load();
    }

    async save(row) {
        const given = parseFloat(String(this.amountOf(row)).replace(/\s/g, "").replace(",", ".")) || 0;
        const difference = await this.orm.call("ocd.live.couriers", "ocd_save_remittance", [row.id, given]);
        this.notification.add(
            difference ? _t("Saved: the difference is reported to the manager.") : _t("Cash saved."),
            { type: difference ? "warning" : "success" }
        );
        await this.load();
    }

    openCourier(card) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: card.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newCourier() {
        this.actionService.doAction(COURIERS, { viewType: "form" });
    }

    openRemittances() {
        this.actionService.doAction(this.data().remittances_action);
    }

    switchView(viewType) {
        this.actionService.doAction(COURIERS, { viewType });
    }
}

registry.category("actions").add("ocd_live_shop.couriers", OcdLiveCouriers);
