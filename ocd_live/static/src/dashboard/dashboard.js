import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

/**
 * Dashboard of the team, as in the validated design (BoDashboard): the figures of the day, the
 * bookings received per day (chart or table), what to do now, the money received and what
 * comes today. Every figure and every line opens the matching records.
 */
export class OcdLiveDashboard extends Component {
    static template = "ocd_live.Dashboard";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    mode = signal("chart");
    hovered = signal(-1);

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        onWillStart(() => this.load());
    }

    async load() {
        this.data.set(await this.orm.call("ocd.live.dashboard", "get_dashboard_data", []));
    }

    open(action) {
        if (action) {
            this.actionService.doAction(action);
        }
    }

    showTable() {
        this.mode.set("table");
        this.hovered.set(-1);
    }

    todoCount(count) {
        return count === 1 ? _t("1 activity") : _t("%s activities", count);
    }

    barLabel(bar) {
        return bar.value === 1
            ? _t("%(day)s: 1 booking", { day: bar.full })
            : _t("%(day)s: %(count)s bookings", { day: bar.full, count: bar.value });
    }

    get tip() {
        const index = this.hovered();
        const bars = this.data()?.chart.bars || [];
        if (index < 0 || !bars[index]) {
            return null;
        }
        const center = ((index + 0.5) / bars.length) * 100;
        return {
            text: this.barLabel(bars[index]),
            style: `left: clamp(0px, calc(${center}% - 85px), calc(100% - 170px))`,
        };
    }
}

registry.category("actions").add("ocd_live.dashboard", OcdLiveDashboard);
