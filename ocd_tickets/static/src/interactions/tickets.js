import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

function money(amount, symbol, position) {
    const lang = document.documentElement.lang || "fr";
    const number = new Intl.NumberFormat(lang, { maximumFractionDigits: 0 }).format(amount);
    if (!symbol) {
        return number;
    }
    return position === "before" ? `${symbol}\u00a0${number}` : `${number}\u00a0${symbol}`;
}

/**
 * The kinds of tickets with − and +: the total and the button say what is paid (« Pay 10,000 F »).
 * Without JavaScript, the form works the same with « Pay ».
 */
export class OcdTicketsTotal extends Interaction {
    static selector = ".o_ocd_tk_form";
    dynamicContent = {
        _root: { "t-on-change": this.update, "t-on-input": this.update },
    };

    start() {
        this.update();
    }

    update() {
        let count = 0;
        let total = 0;
        for (const input of this.el.querySelectorAll(".o_ocd_tk_count")) {
            const quantity = Math.max(parseInt(input.value) || 0, 0);
            count += quantity;
            total += quantity * (parseFloat(input.dataset.price) || 0);
        }
        const symbol = this.el.dataset.symbol || "";
        const position = this.el.dataset.position || "after";
        const amount = this.el.querySelector(".o_ocd_tk_total_amount");
        const what = this.el.querySelector(".o_ocd_tk_total_what");
        if (amount) {
            amount.textContent = money(total, symbol, position);
        }
        if (what) {
            what.textContent = count === 1 ? _t("1 ticket") : _t("%s tickets", count);
        }
        const button = this.el.querySelector(".o_ocd_tk_pay");
        if (button) {
            button.textContent = count ? _t("Pay %s", money(total, symbol, position)) : _t("Pay");
        }
        const most = parseInt(this.el.dataset.most) || 0;
        if (most) {
            for (const more of this.el.querySelectorAll(".o_ocd_stepper_more")) {
                more.disabled = count >= most;
            }
        }
    }
}

/** The tickets of an order, one per person: the dots follow the ticket shown. */
export class OcdTicketsDots extends Interaction {
    static selector = ".o_ocd_tk_tickets";

    start() {
        this.track = this.el.querySelector(".o_ocd_tk_track");
        this.dots = [...this.el.querySelectorAll(".o_ocd_tk_dots i")];
        if (this.track && this.dots.length) {
            this.addListener(this.track, "scroll", () => this.sync(), { passive: true });
        }
    }

    sync() {
        const width = this.track.clientWidth || 1;
        const index = Math.round(this.track.scrollLeft / width);
        this.dots.forEach((dot, position) => dot.classList.toggle("o_ocd_on", position === index));
    }
}

/**
 * The entrance: the camera of the phone reads the QR of the tickets (BarcodeDetector), or the
 * controller types the code. Each answer is the one of the server; without the network, the list
 * of the tickets kept in the phone answers, and the entries leave as soon as the network is back.
 */
export class OcdTicketsScanner extends Interaction {
    static selector = ".o_ocd_tk_scanner";
    dynamicContent = {
        ".o_ocd_tk_typed": { "t-on-submit.prevent": this.onTyped },
        ".o_ocd_tk_camera_start": { "t-on-click": this.startCamera },
    };

    setup() {
        this.event = this.el.dataset.event;
        this.listKey = `ocd_tk_list_${this.event}`;
        this.queueKey = `ocd_tk_queue_${this.event}`;
        this.lastText = "";
        this.lastAt = 0;
        this.busy = false;
    }

    start() {
        if ("BarcodeDetector" in window && navigator.mediaDevices?.getUserMedia) {
            this.el.querySelector(".o_ocd_tk_camera_start").hidden = false;
        } else {
            this.el.querySelector(".o_ocd_tk_hint").textContent = _t("Type the code of the ticket below.");
        }
        this.refreshList();
        this.flush();
        this.addListener(window, "online", () => this.flush());
        this.listTimer = setInterval(() => !document.hidden && this.refreshList(), 60000);
        this.showPending();
    }

    destroy() {
        clearInterval(this.listTimer);
        this.stopCamera();
    }

    read(key, fallback) {
        try {
            return JSON.parse(localStorage.getItem(key)) ?? fallback;
        } catch {
            return fallback;
        }
    }

    write(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch {
            // A full or blocked storage: the network still answers
        }
    }

    async refreshList() {
        try {
            const { tickets, counter } = await this.waitFor(rpc(this.el.dataset.listUrl, {}));
            this.write(this.listKey, tickets);
            if (counter) {
                this.el.querySelector(".o_ocd_tk_counter_value").textContent = counter;
            }
        } catch {
            // Without the network: the list kept answers
        }
    }

    async startCamera() {
        try {
            this.detector = new window.BarcodeDetector({ formats: ["qr_code"] });
            this.stream = await this.waitFor(navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" }, audio: false,
            }));
        } catch {
            this.el.querySelector(".o_ocd_tk_hint").textContent = _t(
                "The camera did not open: allow it in the browser, or type the code below."
            );
            return;
        }
        const video = this.el.querySelector(".o_ocd_tk_video");
        video.srcObject = this.stream;
        video.hidden = false;
        await video.play();
        this.el.querySelector(".o_ocd_tk_camera_start").hidden = true;
        this.scanTimer = setInterval(() => this.detect(video), 350);
    }

    stopCamera() {
        clearInterval(this.scanTimer);
        this.stream?.getTracks().forEach((track) => track.stop());
    }

    async detect(video) {
        if (this.busy || document.hidden || video.readyState < 2) {
            return;
        }
        try {
            const codes = await this.detector.detect(video);
            const text = codes[0]?.rawValue;
            // The same QR held in front of the camera is read once every few seconds
            if (text && !(text === this.lastText && Date.now() - this.lastAt < 4000)) {
                this.lastText = text;
                this.lastAt = Date.now();
                await this.check(text);
            }
        } catch {
            // A frame not readable: the next one
        }
    }

    async onTyped(ev) {
        const input = ev.currentTarget.querySelector("input[name='code']");
        const text = input.value.trim();
        if (text) {
            await this.check(text);
            input.value = "";
        }
    }

    async check(text) {
        this.busy = true;
        try {
            const result = await this.waitFor(rpc(this.el.dataset.scanUrl, { text }));
            if (result.kind === "login") {
                window.location.reload();
                return;
            }
            this.show(result);
            this.markEntered(text, result.kind);
        } catch {
            this.show(this.checkOffline(text));
        } finally {
            this.busy = false;
        }
    }

    find(text) {
        const tickets = this.read(this.listKey, []);
        const raw = text.toUpperCase().replace(/[^A-Z0-9]/g, "");
        return tickets.find((ticket) => (
            text.includes(ticket.qr) || ticket.code.replace(/-/g, "") === raw
        ));
    }

    markEntered(text, kind) {
        if (kind !== "ok") {
            return;
        }
        const tickets = this.read(this.listKey, []);
        const ticket = this.find(text);
        if (ticket) {
            ticket.entered = true;
            this.write(this.listKey, tickets.map((row) => (row.code === ticket.code ? ticket : row)));
        }
    }

    checkOffline(text) {
        const tickets = this.read(this.listKey, []);
        const ticket = this.find(text);
        if (!ticket) {
            return {
                kind: "unknown",
                title: _t("Unknown ticket"),
                lines: [_t("Not in the list of the phone: refuse, or check again with the network.")],
            };
        }
        if (ticket.entered) {
            return { kind: "already", title: _t("Already entered"), lines: [_t("Do not let in.")] };
        }
        ticket.entered = true;
        this.write(this.listKey, tickets.map((row) => (row.code === ticket.code ? ticket : row)));
        const queue = this.read(this.queueKey, []);
        queue.push({ text, at: Date.now() / 1000 });
        this.write(this.queueKey, queue);
        this.showPending();
        return {
            kind: "ok",
            title: _t("Entry OK"),
            lines: [ticket.label, _t("Without the network: noted in the phone.")],
        };
    }

    async flush() {
        const queue = this.read(this.queueKey, []);
        if (!queue.length || !navigator.onLine) {
            return;
        }
        const left = [];
        for (const entry of queue) {
            try {
                await this.waitFor(rpc(this.el.dataset.scanUrl, entry));
            } catch {
                left.push(entry);
            }
        }
        this.write(this.queueKey, left);
        this.showPending();
        if (!left.length) {
            this.refreshList();
        }
    }

    showPending() {
        const pending = this.el.querySelector(".o_ocd_tk_pending");
        const count = this.read(this.queueKey, []).length;
        pending.hidden = !count;
        pending.textContent = count === 1
            ? _t("1 entry noted without the network, sent when it is back.")
            : _t("%s entries noted without the network, sent when it is back.", count);
    }

    show(result) {
        const box = this.el.querySelector(".o_ocd_tk_result");
        box.className = `o_ocd_tk_result o_ocd_tk_result_${result.kind}`;
        box.querySelector(".o_ocd_tk_result_title").textContent = result.title;
        const lines = box.querySelector(".o_ocd_tk_result_lines");
        lines.replaceChildren(...(result.lines || []).map((line) => {
            const span = document.createElement("span");
            span.textContent = line;
            return span;
        }));
        box.hidden = false;
        if (result.counter) {
            this.el.querySelector(".o_ocd_tk_counter_value").textContent = result.counter;
        }
        navigator.vibrate?.(result.kind === "ok" ? 80 : [200, 80, 200]);
    }
}

registry
    .category("public.interactions")
    .add("ocd_tickets.total", OcdTicketsTotal)
    .add("ocd_tickets.dots", OcdTicketsDots)
    .add("ocd_tickets.scanner", OcdTicketsScanner);
