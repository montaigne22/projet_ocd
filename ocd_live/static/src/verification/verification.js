import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

/**
 * What the team checks, on one board as in the validated design (BoVerification): live links,
 * new products and new vendors, then what was checked today. A refusal sends its reason to
 * the vendor.
 */
export class OcdLiveVerification extends Component {
    static template = "ocd_live.Verification";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    refusing = signal(false);
    reasons = signal({});
    choices = signal({});

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        onWillStart(() => this.load());
    }

    async load() {
        this.data.set(await this.orm.call("ocd.live.verification", "get_verification_data", []));
    }

    open(item) {
        if (item.open_action) {
            this.actionService.doAction(item.open_action);
        } else if (item.open_url) {
            window.open(item.open_url, "_blank", "noopener");
        }
    }

    choiceValue(item, choice) {
        return this.choices()[item.key]?.[choice.name] ?? choice.value;
    }

    setChoice(item, choice, value) {
        const current = this.choices();
        this.choices.set({ ...current, [item.key]: { ...(current[item.key] || {}), [choice.name]: value } });
    }

    async approve(item) {
        const values = {};
        for (const choice of item.choices || []) {
            values[choice.name] = this.choiceValue(item, choice);
        }
        await this.orm.call("ocd.live.verification", "ocd_approve", [item.kind, item.id, values]);
        this.notification.add(_t("Done: the vendor is told."), { type: "success" });
        await this.load();
    }

    toggleRefuse(item) {
        this.refusing.set(this.refusing() === item.key ? false : item.key);
    }

    setReason(item, value) {
        this.reasons.set({ ...this.reasons(), [item.key]: parseInt(value, 10) });
    }

    reasonOf(item) {
        return this.reasons()[item.key] || item.reasons[0]?.id || false;
    }

    async refuse(item) {
        await this.orm.call("ocd.live.verification", "ocd_refuse", [item.kind, item.id, this.reasonOf(item)]);
        this.refusing.set(false);
        this.notification.add(_t("Refused: the reason is sent to the vendor."), { type: "info" });
        await this.load();
    }
}

registry.category("actions").add("ocd_live.verification", OcdLiveVerification);
