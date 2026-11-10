import { onWillStart, signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";

/**
 * A choice shown as cards, each with its title and what it means, as in the validated design
 * (how the customers buy, who delivers). The model gives the descriptions, translated, with
 * `ocd_choice_descriptions(field_name)`.
 */
export class OcdChoiceCards extends RadioField {
    static template = "ocd_live.ChoiceCards";
    descriptions = signal({});

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            this.descriptions.set(
                await this.orm.call(this.props.record.resModel, "ocd_choice_descriptions", [this.props.name])
            );
        });
    }

    choose(item) {
        if (!this.props.readonly && item[0] !== this.value) {
            this.onChange(item);
        }
    }
}

registry.category("fields").add("ocd_choice_cards", {
    ...radioField,
    component: OcdChoiceCards,
    displayName: _t("Choice cards"),
    supportedTypes: ["selection"],
});
