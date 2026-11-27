import { Component, onWillStart, onWillUnmount, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const PARCELS = "ocd_live_shop.stock_picking_action_ocd_dispatch";
const SEARCH_DELAY_MS = 300;

/**
 * Dispatch of the parcels of the day, as in the validated design (BoDispatch): the parcels by
 * step, who delivers them and the money to collect; beside them the OCD couriers and the
 * vendors who deliver. A late vendor's parcel goes to an OCD courier in one touch.
 */
export class OcdLiveDispatch extends Component {
    static template = "ocd_live_shop.Dispatch";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    filter = signal("all");
    // on a phone: one step of the parcels at a time, chosen in a row of tabs
    step = signal(false);
    // a parcel searched by its reference, its customer (name, number), its district, vendor or courier
    search = signal("");

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.loads = 0;
        onWillStart(() => this.load());
        onWillUnmount(() => clearTimeout(this.searchTimeout));
    }

    async load() {
        // only the answer to the last request is shown (a search typed quickly)
        const load = ++this.loads;
        const data = await this.orm.call("ocd.live.dispatch", "get_dispatch_data", [], { search: this.search() });
        if (load === this.loads) {
            this.data.set(data);
        }
    }

    /** The board follows what the team types, once they pause. */
    onSearch(ev) {
        this.search.set(ev.target.value);
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => this.load(), SEARCH_DELAY_MS);
    }

    clearSearch() {
        clearTimeout(this.searchTimeout);
        this.search.set("");
        this.load();
    }

    get noResult() {
        return this.search().trim() && !this.data().counts.all
            ? _t("No parcel for « %s ».", this.search().trim())
            : "";
    }

    cardsOf(column) {
        const filter = this.filter();
        return this.data().cards.filter(
            (card) => card.column === column.key && (filter === "all" || card.by === filter)
        );
    }

    /** The parcels of a column for the filter: more than its cards beyond the first ones. */
    countOf(column) {
        return column.counts[this.filter()];
    }

    moreLabel(column, cards) {
        return _t("%s more · see the list", this.countOf(column) - cards.length);
    }

    async openColumn(column) {
        const action = await this.orm.call("ocd.live.dispatch", "ocd_column_action", [column.key, this.filter()], {
            search: this.search(),
        });
        this.actionService.doAction(action, { viewType: "list" });
    }

    /** The step shown on a phone: the one chosen, else the first with parcels. */
    get stepKey() {
        const columns = this.data().columns;
        const chosen = this.step();
        if (chosen && columns.some((column) => column.key === chosen)) {
            return chosen;
        }
        return (columns.find((column) => this.countOf(column)) || columns[0])?.key;
    }

    filterLabel(key) {
        const counts = this.data().counts;
        const labels = {
            all: _t("All · %s", counts.all),
            ocd: _t("OCD couriers · %s", counts.ocd),
            vendor: _t("Delivered by the vendors · %s", counts.vendor),
        };
        return labels[key];
    }

    courierLabel(card) {
        return _t("Courier of the parcel %s", card.ref);
    }

    openParcel(card) {
        this.actionService.doAction("ocd_live_shop.stock_picking_action_ocd_dispatch", {
            viewType: "form",
            props: { resId: card.id },
        });
    }

    async assign(card, value) {
        await this.orm.call("ocd.live.dispatch", "ocd_assign", [card.id, parseInt(value, 10) || false]);
        this.notification.add(_t("Courier chosen for %s.", card.ref), { type: "success" });
        await this.load();
    }

    async switchToOcd(card) {
        await this.orm.call("ocd.live.dispatch", "ocd_switch_to_ocd", [card.id]);
        this.notification.add(_t("%s goes to an OCD courier.", card.ref), { type: "success" });
        await this.load();
    }

    async retry(card) {
        await this.orm.call("ocd.live.dispatch", "ocd_retry", [card.id]);
        this.notification.add(_t("New attempt for %s.", card.ref), { type: "success" });
        await this.load();
    }

    openCash() {
        this.actionService.doAction(this.data().cash_action);
    }

    switchView(viewType) {
        this.actionService.doAction(PARCELS, { viewType });
    }
}

registry.category("actions").add("ocd_live_shop.dispatch", OcdLiveDispatch);
