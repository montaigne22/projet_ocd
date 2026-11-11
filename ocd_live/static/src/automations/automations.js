import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

/**
 * Catalogue of the automations of OCD Live, as in the validated design (BoAutomatisations):
 * when... then..., grouped, what runs them, how often they ran these 7 days, and their switch
 * (always on for the money, the proofs and the technical tasks). The detail of the chosen one
 * is on the right.
 */
export class OcdLiveAutomations extends Component {
    static template = "ocd_live.Automations";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    selected = signal(null);
    busy = signal(false);

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        onWillStart(() => this.load());
    }

    async load() {
        const data = await this.orm.call("ocd.automation", "get_automations_page", []);
        this.data.set(data);
        if (!this.rows.some((row) => row.id === this.selected())) {
            const first = this.rows.find((row) => row.group !== "technical") || this.rows[0];
            this.selected.set(first ? first.id : null);
        }
    }

    get rows() {
        return (this.data()?.groups || []).flatMap((group) => group.rows);
    }

    get current() {
        return this.rows.find((row) => row.id === this.selected()) || this.rows[0];
    }

    pick(row) {
        this.selected.set(row.id);
    }

    runs(row) {
        return new Intl.NumberFormat("fr-FR").format(row.runs);
    }

    switchLabel(row) {
        return row.active ? _t("Pause: %s", row.name) : _t("Start again: %s", row.name);
    }

    async toggle(row, ev) {
        const value = ev.target.checked;
        this.selected.set(row.id);
        if (row.locked || this.busy()) {
            ev.target.checked = row.active;
            return;
        }
        this.busy.set(true);
        try {
            const updated = await this.orm.call("ocd.automation", "ocd_switch", [row.id, value]);
            const data = this.data();
            this.data.set({
                ...data,
                groups: data.groups.map((group) => ({
                    ...group,
                    rows: group.rows.map((candidate) => (candidate.id === updated.id ? updated : candidate)),
                })),
            });
            this.notification.add(
                updated.active
                    ? _t("%s runs again.", updated.name)
                    : _t("%s is paused: the team does it by hand.", updated.name),
                { type: updated.active ? "success" : "warning" }
            );
        } catch (error) {
            ev.target.checked = row.active;
            throw error;
        } finally {
            this.busy.set(false);
        }
    }
}

registry.category("actions").add("ocd_live.automations", OcdLiveAutomations);
