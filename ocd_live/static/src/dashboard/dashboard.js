import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

/**
 * Figures of the day for the team. Each tile opens the matching list.
 */
export class OcdLiveDashboard extends Component {
    static template = "ocd_live.Dashboard";
    props = useProps(standardActionServiceProps);
    data = signal({ sections: [] });

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        onWillStart(() => this.load());
    }

    async load() {
        this.data.set(await this.orm.call("ocd.live.dashboard", "get_dashboard_data", []));
    }

    open(tile) {
        this.actionService.doAction(tile.action);
    }
}

registry.category("actions").add("ocd_live.dashboard", OcdLiveDashboard);
