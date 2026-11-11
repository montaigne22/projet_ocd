import { Component, onMounted, onPatched, onWillStart, onWillUnmount, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const POLL_MS = 20000;

/**
 * WhatsApp conversations of the team, as in the validated design (BoWhatsApp): the list (all,
 * or waiting for an answer), the conversation with its automatic messages, answers and internal
 * notes, and the contact on the right. New messages come by the bus (and every 20 seconds while
 * the page is shown). Out of the 24-hour window, only an approved template can go.
 */
export class OcdWhatsappInbox extends Component {
    static template = "ocd_live_whatsapp.Inbox";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    filter = signal("all");
    draft = signal("");
    busy = signal(false);
    templateKey = signal("");
    messagesRef = signal.ref();
    inputRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.bus = useService("bus_service");
        this.lastShown = null;
        this.onBusMessage = (payload) => {
            const ids = (this.data()?.conversations || []).map((conversation) => conversation.id);
            if (!payload?.id || ids.includes(payload.id) || !ids.length) {
                this.scheduleRefresh();
            }
        };
        onWillStart(() => this.load(this.props.action?.context?.active_id));
        onMounted(() => {
            this.bus.subscribe("discuss.channel/new_message", this.onBusMessage);
            this.timer = setInterval(() => {
                if (document.visibilityState === "visible") {
                    this.refresh();
                }
            }, POLL_MS);
            this.scrollToEnd();
        });
        onPatched(() => this.scrollToEnd());
        onWillUnmount(() => {
            this.bus.unsubscribe("discuss.channel/new_message", this.onBusMessage);
            clearInterval(this.timer);
            clearTimeout(this.refreshTimeout);
        });
    }

    async load(channelId) {
        this.data.set(await this.orm.call("ocd.whatsapp.inbox", "get_inbox", [channelId || null]));
        this.pickDefaultTemplate();
    }

    scheduleRefresh() {
        clearTimeout(this.refreshTimeout);
        this.refreshTimeout = setTimeout(() => this.refresh(), 300);
    }

    async refresh() {
        if (this.busy()) {
            return;
        }
        await this.load(this.current?.id);
    }

    // === LIST === //

    get current() {
        return this.data()?.current || null;
    }

    get conversations() {
        const all = this.data()?.conversations || [];
        return this.filter() === "waiting" ? all.filter((conversation) => conversation.waiting) : all;
    }

    get chips() {
        const data = this.data();
        return [
            { key: "all", label: _t("All · %s", data.conversations.length) },
            { key: "waiting", label: _t("Waiting · %s", data.waiting) },
        ];
    }

    async open(conversation) {
        if (this.current?.id === conversation.id) {
            return;
        }
        this.draft.set("");
        const current = await this.orm.call("ocd.whatsapp.inbox", "get_conversation", [conversation.id]);
        this.data.set({ ...this.data(), current });
        this.pickDefaultTemplate();
    }

    openTeamChannel(row) {
        if (row.action) {
            this.actionService.doAction(row.action);
        } else if (row.id) {
            this.actionService.doAction({
                type: "ir.actions.client",
                tag: "mail.action_discuss",
                params: { active_id: `discuss.channel_${row.id}` },
            });
        }
    }

    // === CONVERSATION === //

    scrollToEnd() {
        const el = this.messagesRef();
        const current = this.current;
        if (!el || !current) {
            return;
        }
        const last = current.messages.at(-1)?.id || 0;
        const shown = `${current.id}-${last}`;
        if (shown !== this.lastShown) {
            this.lastShown = shown;
            el.scrollTop = el.scrollHeight;
        }
    }

    useQuick(quick) {
        this.draft.set(quick.text);
        this.inputRef()?.focus();
    }

    onDraft(ev) {
        this.draft.set(ev.target.value);
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.post(false);
        }
    }

    async post(note) {
        const text = this.draft().trim();
        if (!text || this.busy()) {
            return;
        }
        this.busy.set(true);
        try {
            this.data.set(await this.orm.call("ocd.whatsapp.inbox", "ocd_post", [this.current.id, text, note]));
            this.draft.set("");
        } finally {
            this.busy.set(false);
        }
    }

    get template() {
        return (this.current?.templates || []).find((template) => template.key === this.templateKey());
    }

    pickDefaultTemplate() {
        const templates = this.current?.templates || [];
        if (!templates.some((template) => template.key === this.templateKey())) {
            this.templateKey.set(templates[0]?.key || "");
        }
    }

    onTemplate(ev) {
        this.templateKey.set(ev.target.value);
    }

    async sendTemplate() {
        const template = this.template;
        if (!template || this.busy()) {
            return;
        }
        this.busy.set(true);
        try {
            this.data.set(
                await this.orm.call("ocd.whatsapp.inbox", "ocd_send_template", [
                    this.current.id,
                    template.template_id,
                    template.res_model,
                    template.res_id,
                ])
            );
            this.notification.add(_t("Template sent."), { type: "success" });
        } finally {
            this.busy.set(false);
        }
    }

    // === CONTACT === //

    run(action) {
        if (action) {
            this.actionService.doAction(action);
        }
    }

    openDiscuss() {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "mail.action_discuss",
            params: { active_id: `discuss.channel_${this.current.id}` },
        });
    }
}

registry.category("actions").add("ocd_live_whatsapp.inbox", OcdWhatsappInbox);
