import { useVoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { Component, onMounted, onPatched, onWillStart, onWillUnmount, signal, useProps } from "@odoo/owl";
import { FileModel } from "@web/core/file_viewer/file_model";
import { rpc } from "@web/core/network/rpc";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { WhatsAppAttachment } from "@whatsapp_cloud/whatsapp_attachment";

const POLL_MS = 20000;
// The conversations shown at first, and added by « Show more » (LIST_LIMIT of the server)
const LIST_STEP = 80;
const SEARCH_DELAY_MS = 300;
// WhatsApp takes files of 100 MB at most (documents; less for photos and videos: sent as documents)
const MAX_FILE_BYTES = 100 * 1024 * 1024;
// A voice message of the team: 5 minutes at most
const VOICE_MAX_SECONDS = 300;

/**
 * WhatsApp conversations of the team, as in the validated design (BoWhatsApp): the list (all,
 * or waiting for an answer), the conversation with its automatic messages, answers and internal
 * notes, and the contact on the right. New messages come by the bus (and every 20 seconds while
 * the page is shown). Out of the 24-hour window, only an approved template can go. The files are
 * shown like in WhatsApp (sounds played, videos and images in place, documents opened); with the
 * WhatsApp calls, the calls are lines of the conversation (call back, listen to the recording) and
 * the customer is called from here. The list is searched by name or number and shows more on
 * demand; the agent takes a conversation, marks it resolved, sends photos, documents and voice
 * messages. On a phone or a tablet, the contact (and the calls) is a tab next to the conversation.
 */
export class OcdWhatsappInbox extends Component {
    static template = "ocd_live_whatsapp.Inbox";
    static components = { WhatsAppAttachment };
    props = useProps(standardActionServiceProps);
    data = signal(null);
    filter = signal("all");
    search = signal("");
    limit = signal(LIST_STEP);
    draft = signal("");
    busy = signal(false);
    templateKey = signal("");
    // files uploaded for the next message: [{ id, name, mimetype, voice, token }]
    files = signal([]);
    uploading = signal(0);
    // on a phone or a tablet: the conversation or the contact
    tab = signal("thread");
    // on a phone: the list, or the conversation (one at a time, like in WhatsApp)
    pane = signal("list");
    // on a phone: the button sends an internal note instead of a message to the contact
    noteMode = signal(false);
    messagesRef = signal.ref();
    inputRef = signal.ref();
    fileInputRef = signal.ref();
    rootRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.bus = useService("bus_service");
        this.fileViewer = useFileViewer();
        this.voice = useVoiceRecorder(
            { maxDuration: VOICE_MAX_SECONDS, onRecordReady: (file) => this.uploadFile(file, { voice: true }) },
            { rootRef: this.rootRef }
        );
        this.lastShown = null;
        this.onBusMessage = (payload) => {
            const ids = (this.data()?.conversations || []).map((conversation) => conversation.id);
            if (!payload?.id || ids.includes(payload.id) || !ids.length) {
                this.scheduleRefresh();
            }
        };
        onWillStart(() => this.load(this.props.action?.context?.active_id));
        onMounted(() => {
            // the bubbles of the chat windows of Odoo would cover the conversation (phone, tablet)
            document.body.classList.add("o_ocd_inbox_open");
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
            document.body.classList.remove("o_ocd_inbox_open");
            this.bus.unsubscribe("discuss.channel/new_message", this.onBusMessage);
            clearInterval(this.timer);
            clearTimeout(this.refreshTimeout);
            clearTimeout(this.searchTimeout);
        });
    }

    /** What the list shows: the search, the filter and how many conversations. */
    get listOptions() {
        return { search: this.search(), filter: this.filter(), limit: this.limit() };
    }

    async load(channelId) {
        this.show(await this.orm.call("ocd.whatsapp.inbox", "get_inbox", [channelId || null, this.listOptions]));
    }

    /** The page as given by the server (after loading it, or after an action). */
    show(data) {
        this.data.set(data);
        this.pickDefaultTemplate();
    }

    scheduleRefresh() {
        clearTimeout(this.refreshTimeout);
        this.refreshTimeout = setTimeout(() => this.refresh(), 300);
    }

    /** Load the page again; `force` also while an action runs (a new search or filter). */
    async refresh(force = false) {
        if (this.busy() && !force) {
            return;
        }
        await this.load(this.current?.id);
    }

    /** Run an action of the inbox on the conversation shown: the page comes back with it. */
    async act(method, args = [], kwargs = {}) {
        if (this.busy()) {
            return false;
        }
        this.busy.set(true);
        try {
            this.show(
                await this.orm.call("ocd.whatsapp.inbox", method, [this.current.id, ...args], {
                    ...kwargs,
                    options: this.listOptions,
                })
            );
            return true;
        } finally {
            this.busy.set(false);
        }
    }

    // === LIST === //

    get current() {
        return this.data()?.current || null;
    }

    get conversations() {
        return this.data()?.conversations || [];
    }

    get chips() {
        const counts = this.data().counts || {};
        return [
            { key: "all", label: _t("All · %s", counts.all ?? 0) },
            { key: "waiting", label: _t("Waiting · %s", counts.waiting ?? 0) },
            { key: "mine", label: _t("Mine · %s", counts.mine ?? 0) },
        ];
    }

    get emptyText() {
        if (this.search()) {
            return _t("No conversation for « %s ».", this.search());
        }
        return {
            waiting: _t("Nobody waits for an answer."),
            mine: _t("You have not taken any conversation."),
        }[this.filter()] || _t("No WhatsApp conversation yet.");
    }

    setFilter(key) {
        if (this.filter() === key) {
            return;
        }
        this.filter.set(key);
        this.limit.set(LIST_STEP);
        this.refresh(true);
    }

    /** The list follows what the agent types (a name, a number), once they pause. */
    onSearch(ev) {
        this.search.set(ev.target.value);
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.limit.set(LIST_STEP);
            this.refresh(true);
        }, SEARCH_DELAY_MS);
    }

    clearSearch() {
        this.search.set("");
        this.limit.set(LIST_STEP);
        this.refresh(true);
    }

    showMore() {
        this.limit.set(this.limit() + LIST_STEP);
        this.refresh(true);
    }

    async open(conversation) {
        this.tab.set("thread");
        this.pane.set("thread");
        if (this.current?.id === conversation.id) {
            return;
        }
        this.draft.set("");
        this.noteMode.set(false);
        this.dropFiles();
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

    /** On a phone: back to the list. */
    back() {
        this.pane.set("list");
        this.tab.set("thread");
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
            this.atEnd = true;
        }
    }

    /** Whether the agent reads the end of the conversation (then it follows the new lines). */
    onMessagesScroll() {
        const el = this.messagesRef();
        if (el) {
            this.atEnd = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }
    }

    /** A photo or a video of the conversation loaded: its height pushes the end down. */
    onMediaLoaded() {
        const el = this.messagesRef();
        if (el && this.atEnd) {
            el.scrollTop = el.scrollHeight;
        }
    }

    get draftPlaceholder() {
        return this.noteMode() ? _t("Internal note for the team (not sent)…") : _t("Write a message…");
    }

    get sendLabel() {
        return _t("Send to the contact");
    }

    get noteLabel() {
        return _t("Save the internal note");
    }

    useQuick(quick) {
        this.draft.set(quick.text);
        this.inputRef()?.focus();
    }

    onDraft(ev) {
        this.draft.set(ev.target.value);
    }

    /** Enter sends (a note when the 24-hour window is closed), Shift+Enter goes to the line. */
    onKeydown(ev, note = false) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.post(note);
        }
    }

    /** Whether there is something to send: a text or files, all uploaded, no recording running. */
    get canPost() {
        return (
            !this.busy() &&
            !this.uploading() &&
            !this.voice.recording &&
            Boolean(this.draft().trim() || this.files().length)
        );
    }

    async post(note) {
        if (!this.canPost) {
            return;
        }
        const text = this.draft().trim();
        const done = await this.act("ocd_post", [text, note], {
            attachment_ids: this.files().map((file) => file.id),
        });
        if (done) {
            this.draft.set("");
            this.files.set([]);
            this.noteMode.set(false);
        }
    }

    // === TAKE, RESOLVE === //

    take() {
        return this.act("ocd_take");
    }

    async resolve() {
        if (await this.act("ocd_resolve")) {
            this.notification.add(_t("Conversation resolved: a new message of the contact opens it again."), {
                type: "success",
            });
        }
    }

    reopen() {
        return this.act("ocd_reopen");
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
        if (await this.act("ocd_send_template", [template.template_id, template.res_model, template.res_id])) {
            this.notification.add(_t("Template sent."), { type: "success" });
        }
    }

    // === FILES TO SEND === //

    chooseFiles() {
        this.fileInputRef()?.click();
    }

    async onFilesChosen(ev) {
        const chosen = [...(ev.target.files || [])];
        ev.target.value = "";
        for (const file of chosen) {
            await this.uploadFile(file);
        }
    }

    /** Upload a file for the next message (a photo, a document, a recorded voice message): it
     * leaves with the message, or alone. */
    async uploadFile(file, { voice = false } = {}) {
        if (!file?.size || !this.current) {
            return;
        }
        if (file.size > MAX_FILE_BYTES) {
            this.notification.add(_t("%s is too heavy: WhatsApp takes files of 100 MB at most.", file.name), {
                type: "danger",
            });
            return;
        }
        const formData = new FormData();
        formData.append("csrf_token", odoo.csrf_token);
        formData.append("ufile", file);
        formData.append("thread_id", this.current.id);
        formData.append("thread_model", "discuss.channel");
        formData.append("is_pending", "true");
        if (voice) {
            formData.append("voice", "true");
        }
        this.uploading.set(this.uploading() + 1);
        try {
            const response = await fetch("/mail/attachment/upload", { method: "POST", body: formData });
            const result = response.ok ? await response.json() : { error: response.statusText };
            if (result.error || !result.data?.attachment_id) {
                throw new Error(result.error || _t("The file was not received."));
            }
            const stored = (result.data.store_data?.["ir.attachment"] || []).find(
                (row) => row.id === result.data.attachment_id
            );
            this.files.set([
                ...this.files(),
                {
                    id: result.data.attachment_id,
                    name: voice ? _t("Voice message") : file.name,
                    mimetype: file.type,
                    voice,
                    token: stored?.ownership_token,
                },
            ]);
        } catch (error) {
            this.notification.add(_t("%(name)s was not added: %(error)s", { name: file.name, error: error.message }), {
                type: "danger",
            });
        } finally {
            this.uploading.set(this.uploading() - 1);
        }
    }

    fileIcon(file) {
        if (file.voice || file.mimetype?.startsWith("audio/")) {
            return "mic";
        }
        if (file.mimetype?.startsWith("image/")) {
            return "image";
        }
        if (file.mimetype?.startsWith("video/")) {
            return "movie";
        }
        return "description";
    }

    removeFile(file) {
        this.files.set(this.files().filter((row) => row.id !== file.id));
        this.deleteFiles([file]);
    }

    /** The files not sent are dropped (another conversation is opened). */
    dropFiles() {
        const files = this.files();
        if (files.length) {
            this.files.set([]);
            this.deleteFiles(files);
        }
    }

    deleteFiles(files) {
        const tokens = Object.fromEntries(files.map((file) => [file.id, file.token || null]));
        rpc("/mail/attachment/delete", { access_token_by_attachment_id: tokens }).catch(() => {});
    }

    toggleVoice() {
        return this.voice.onClick();
    }

    get voiceTitle() {
        return this.voice.recording
            ? _t("Stop: the voice message is added to the message")
            : _t("Record a voice message");
    }

    // === FILES OF THE CONVERSATION === //

    /** A file in the viewer of Odoo (a PDF, an image...), with the other files of its message. */
    openFile(file, files) {
        const models = files.map((row) =>
            Object.assign(new FileModel(), {
                id: row.id,
                name: row.name,
                mimetype: row.mimetype,
                checksum: row.checksum,
                raw_access_token: row.access_token,
            })
        );
        this.fileViewer.open(models[files.indexOf(file)], models);
    }

    // === CALLS (with the WhatsApp calls) === //

    /** Call the customer through WhatsApp: the phone of the top bar places the call; Odoo says
     * why when it cannot (permission of the customer, limits of Meta, budget). */
    async callCustomer() {
        if (this.busy()) {
            return;
        }
        this.busy.set(true);
        try {
            const action = await this.orm.call("discuss.channel", "whatsapp_action_call", [[this.current.id]]);
            if (action && typeof action === "object") {
                await this.actionService.doAction(action);
            }
        } finally {
            this.busy.set(false);
        }
    }

    /** Ask the customer whether the company may call them (within 24 hours of their message). */
    async askToCall() {
        if (this.busy()) {
            return;
        }
        this.busy.set(true);
        try {
            await this.orm.call("discuss.channel", "whatsapp_action_call_permission_request", [[this.current.id]]);
        } finally {
            this.busy.set(false);
        }
        await this.refresh(true);
    }

    async listenRecording(call) {
        const action = await this.orm.call("whatsapp.call", "action_listen_recording", [[call.id]]);
        if (action) {
            await this.actionService.doAction(action);
        }
    }

    callIcon(call) {
        if (call.missed) {
            return "phone_missed";
        }
        return call.inbound ? "phone_in_talk" : "phone";
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
