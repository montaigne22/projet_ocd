import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const ORDERS = "sale.action_orders";

/**
 * Orders of the shop, as in the validated design (BoCommandes): the orders of the week grouped
 * by day, with their payment and their delivery, and the detail of the chosen order beside
 * them (lines and share of each vendor, parcels, what to do, history).
 */
export class OcdLiveOrders extends Component {
    static template = "ocd_live_shop.Orders";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    detail = signal(null);
    filter = signal("all");

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        onWillStart(() => this.load());
    }

    async load() {
        const data = await this.orm.call("ocd.live.orders", "get_orders_data", []);
        this.data.set(data);
        const selected = this.detail()?.id || data.selected;
        if (selected) {
            await this.select(selected);
        }
    }

    async select(orderId) {
        this.detail.set(await this.orm.call("ocd.live.orders", "get_order_detail", [orderId]));
    }

    keep(row) {
        const filter = this.filter();
        return filter === "all" || row[filter];
    }

    get groups() {
        return this.data()
            .groups.map((group) => ({ ...group, rows: group.rows.filter((row) => this.keep(row)) }))
            .filter((group) => group.rows.length);
    }

    get rows() {
        return this.groups.flatMap((group) => group.rows);
    }

    money(amount) {
        return formatMonetary(amount, { currencyId: this.data().currency_id });
    }

    sum(rows) {
        return this.money(rows.reduce((total, row) => total + row.amount, 0));
    }

    filterLabel(key) {
        const rows = this.data().groups.flatMap((group) => group.rows);
        const count = rows.filter((row) => key === "all" || row[key]).length;
        const labels = {
            all: _t("All"),
            todo: _t("To deliver"),
            issue: _t("Late or problem"),
            cod: _t("Paid at the door"),
        };
        return `${labels[key]} · ${count}`;
    }

    countLabel(rows) {
        return rows.length === 1 ? _t("1 order") : _t("%s orders", rows.length);
    }

    openOrder() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: this.detail().id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openParcel(parcel) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.picking",
            res_id: parcel.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async switchToOcd(parcel) {
        await this.orm.call("ocd.live.dispatch", "ocd_switch_to_ocd", [parcel.id]);
        this.notification.add(_t("%s goes to an OCD courier.", parcel.ref), { type: "success" });
        await this.load();
    }

    async retry(parcel) {
        await this.orm.call("ocd.live.dispatch", "ocd_retry", [parcel.id]);
        this.notification.add(_t("New attempt for %s.", parcel.ref), { type: "success" });
        await this.load();
    }

    openDispatch() {
        this.actionService.doAction("ocd_live_shop.ocd_live_dispatch_action");
    }

    switchView(viewType) {
        this.actionService.doAction(ORDERS, { viewType });
    }
}

registry.category("actions").add("ocd_live_shop.orders", OcdLiveOrders);
