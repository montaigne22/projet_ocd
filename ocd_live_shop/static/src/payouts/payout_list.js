import { onWillStart, onWillUpdateProps, signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

/**
 * Payouts of the vendors, as in the validated design (BoReversements): the list of Odoo with,
 * above it, what to pay on the next payout day, what to recover and what was paid this week.
 */
export class OcdPayoutListRenderer extends ListRenderer {
    static template = "ocd_live_shop.PayoutListRenderer";
    summary = signal(null);

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(() => this.loadSummary());
        onWillUpdateProps(() => this.loadSummary());
    }

    async loadSummary() {
        this.summary.set(await this.orm.call("ocd.payout", "ocd_summary", []));
    }
}

registry.category("views").add("ocd_payout_list", { ...listView, Renderer: OcdPayoutListRenderer });
