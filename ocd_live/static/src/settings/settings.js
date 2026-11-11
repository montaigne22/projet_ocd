import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

/** "08:30" for 8.5 hours. */
export function hoursToText(value) {
    const total = Math.round((Number(value) || 0) * 60);
    const hours = Math.floor(total / 60) % 24;
    const minutes = total % 60;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

/** 8.5 for "08:30"; null when the text is not an hour. */
export function textToHours(text) {
    const match = /^(\d{1,2}):(\d{2})$/.exec((text || "").trim());
    if (!match || Number(match[2]) > 59) {
        return null;
    }
    return Number(match[1]) + Number(match[2]) / 60;
}

/** A number typed by the team ("15 000", "2,5"), or the text as typed when it is none. */
export function parseNumber(text) {
    const clean = String(text ?? "").replace(/[\s  ]/g, "").replace(",", ".");
    return clean !== "" && !isNaN(Number(clean)) ? Number(clean) : text;
}

function sameValue(a, b) {
    return String(a ?? "") === String(b ?? "") || (!a && !b);
}

/**
 * Settings of OCD Live, as in the validated design (BoParametres): the sections on the left,
 * the settings of the section on the right, and a bar that says whether everything is saved.
 * The changes of every section are saved together; leaving with changes asks what to do.
 */
export class OcdLiveSettings extends Component {
    static template = "ocd_live.Settings";
    props = useProps(standardActionServiceProps);
    page = signal(null);
    sectionKey = signal(null);
    draft = signal({});
    errors = signal({});
    message = signal("");
    savedAt = signal("");
    saving = signal(false);

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        useSetupAction({
            beforeLeave: () => this.beforeLeave(),
            beforeUnload: (ev) => this.beforeUnload(ev),
        });
        onWillStart(() => this.load());
    }

    async load() {
        const page = await this.orm.call("ocd.live.settings", "get_settings_page", []);
        this.page.set(page);
        if (!page.sections.some((section) => section.key === this.sectionKey())) {
            this.sectionKey.set(page.sections[0]?.key || null);
        }
    }

    get section() {
        const sections = this.page()?.sections || [];
        return sections.find((section) => section.key === this.sectionKey()) || sections[0];
    }

    get dirty() {
        return Object.keys(this.draft()).length > 0;
    }

    get bar() {
        if (this.message()) {
            return { tone: "red", text: _t("Not saved: %s", this.message()) };
        }
        if (this.dirty) {
            return { tone: "yellow", text: _t("Unsaved changes") };
        }
        if (this.savedAt()) {
            return {
                tone: "green",
                text: _t("Saved at %s. The automations already use the new values.", this.savedAt()),
            };
        }
        return { tone: "none", text: _t("All the settings are saved.") };
    }

    keysOf(item) {
        return [item.key, ...(item.fields || []).map((field) => field.key)];
    }

    sectionState(section) {
        const keys = section.items.flatMap((item) => this.keysOf(item));
        if (keys.some((key) => key in this.errors())) {
            return "error";
        }
        return keys.some((key) => key in this.draft()) ? "dirty" : "";
    }

    pick(section) {
        this.sectionKey.set(section.key);
    }

    // === VALUES === //
    // The draft keeps what the team types (a number stays as typed while typing); it is read
    // as a value to compare with the saved one, and to send when saving.

    normalized(item, raw) {
        if (item.kind === "number" || item.kind === "money") {
            return parseNumber(raw);
        }
        if (item.kind === "time") {
            const hours = textToHours(raw);
            return hours === null ? raw : hours;
        }
        if (item.kind === "text") {
            return String(raw ?? "").trim();
        }
        return raw;
    }

    value(item) {
        const draft = this.draft();
        return item.key in draft ? this.normalized(item, draft[item.key]) : this.page().values[item.key];
    }

    change(item, raw) {
        const draft = { ...this.draft() };
        if (sameValue(this.page().values[item.key], this.normalized(item, raw))) {
            delete draft[item.key];
        } else {
            draft[item.key] = raw;
        }
        const errors = { ...this.errors() };
        delete errors[item.key];
        this.draft.set(draft);
        this.errors.set(errors);
        this.message.set("");
        this.savedAt.set("");
    }

    error(item) {
        return this.errors()[item.key] || "";
    }

    subErrors(item) {
        return (item.fields || []).map((field) => this.error(field)).filter(Boolean);
    }

    warnOff(item) {
        return item.kind === "check" && item.warn_off && !this.value(item);
    }

    text(item) {
        const draft = this.draft();
        if (item.key in draft) {
            return draft[item.key] ?? "";
        }
        const value = this.page().values[item.key];
        if (item.kind === "time") {
            return typeof value === "number" ? hoursToText(value) : "";
        }
        if (item.kind === "money" && typeof value === "number") {
            return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(value);
        }
        return value === false || value === null || value === undefined ? "" : String(value);
    }

    optionIndex(item) {
        const value = this.value(item);
        return item.options.findIndex((option) => sameValue(option.value, value));
    }

    onCheck(ev) {
        const item = this.itemOf(ev);
        if (item) {
            this.change(item, ev.target.checked);
        }
    }

    // The inputs of a group are drawn by a sub-template: their item is found by the key the
    // input carries, never by a variable of the template.
    itemOf(ev) {
        const key = ev.currentTarget?.dataset?.key || ev.target.dataset.key;
        return this.items.find((item) => item.key === key);
    }

    get items() {
        return (this.page()?.sections || []).flatMap((section) =>
            section.items.flatMap((item) => [item, ...(item.fields || [])])
        );
    }

    onInput(ev) {
        const item = this.itemOf(ev);
        if (item) {
            this.change(item, ev.target.value);
        }
    }

    onDate(ev) {
        const item = this.itemOf(ev);
        if (item) {
            this.change(item, ev.target.value || false);
        }
    }

    onSelect(ev) {
        const item = this.itemOf(ev);
        const option = item?.options[Number(ev.target.value)];
        if (item) {
            this.change(item, option ? option.value : false);
        }
    }

    // === SAVE === //

    async save() {
        if (!this.dirty) {
            return true;
        }
        if (this.saving()) {
            return false;
        }
        this.saving.set(true);
        try {
            const values = {};
            for (const [key, raw] of Object.entries(this.draft())) {
                const item = this.items.find((candidate) => candidate.key === key);
                values[key] = item ? this.normalized(item, raw) : raw;
            }
            const result = await this.orm.call("ocd.live.settings", "save_settings_page", [values]);
            if (!result.ok) {
                this.errors.set(result.errors || {});
                this.message.set(result.message || "");
                const first = this.page().sections.find((section) => this.sectionState(section) === "error");
                if (first) {
                    this.sectionKey.set(first.key);
                }
                return false;
            }
            this.page.set(result);
            this.draft.set({});
            this.errors.set({});
            this.message.set("");
            this.savedAt.set(result.saved_at);
            return true;
        } finally {
            this.saving.set(false);
        }
    }

    discard() {
        this.draft.set({});
        this.errors.set({});
        this.message.set("");
    }

    beforeLeave() {
        if (!this.dirty) {
            return true;
        }
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsaved changes"),
                body: _t("Save the changes of the settings before leaving?"),
                confirmLabel: _t("Save"),
                confirm: async () => resolve(await this.save()),
                cancelLabel: _t("Discard"),
                cancel: () => {
                    this.discard();
                    resolve(true);
                },
                dismiss: () => resolve(false),
            });
        });
    }

    beforeUnload(ev) {
        if (this.dirty) {
            ev.preventDefault();
            ev.returnValue = "";
        }
    }

    // === LINKS === //

    openLink(ev) {
        const link = this.itemOf(ev)?.link;
        if (link?.action) {
            this.actionService.doAction(link.action);
        }
    }

    async run(ev) {
        const item = this.itemOf(ev);
        if (!item) {
            return;
        }
        const action = await this.orm.call("ocd.live.settings", "run_settings_action", [item.key]);
        if (action && action !== true) {
            await this.actionService.doAction(action);
        }
        await this.load();
    }
}

registry.category("actions").add("ocd_live.settings", OcdLiveSettings);
