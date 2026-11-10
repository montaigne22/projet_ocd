import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

/**
 * Tools of Odoo used by OCD Live, as in the validated design (BoOutils): what each application
 * and module is used for, whether it is installed here, and what is not needed.
 */
export class OcdLiveTools extends Component {
    static template = "ocd_live.Tools";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    area = signal("all");

    setup() {
        this.orm = useService("orm");
        onWillStart(async () => this.data.set(await this.orm.call("ocd.live.tools", "get_tools_data", [])));
    }

    faded(row) {
        const area = this.area();
        return area !== "all" && !row.tags.includes(area);
    }
}

registry.category("actions").add("ocd_live.tools", OcdLiveTools);
