import { onWillStart, signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";

/**
 * Applications of the live hosts, as in the validated design (BoRecrutement): the kanban of
 * Odoo by step, with the offer on top (online or not, positions filled, refused).
 */
export class OcdHostKanbanController extends KanbanController {
    static template = "ocd_live_recruitment.HostKanbanView";
    summary = signal(null);

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            const jobId = this.props.context?.ocd_job_id;
            if (jobId) {
                this.summary.set(await this.orm.call("hr.applicant", "ocd_job_summary", [jobId]));
            }
        });
    }
}

registry.category("views").add("ocd_host_kanban", { ...kanbanView, Controller: OcdHostKanbanController });
