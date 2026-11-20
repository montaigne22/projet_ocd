import { Component, onWillUnmount, proxy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/** The phone in the top bar: take the calls or not, and the state of the connection. */
export class WhatsappSoftphoneSystray extends Component {
    static template = "whatsapp_cloud_call.SoftphoneSystray";
    static components = { Dropdown };

    setup() {
        this.softphone = useService("whatsapp_softphone");
    }

    get statusText() {
        const phone = this.softphone;
        if (!phone.available) {
            return _t("You do not take the calls");
        }
        return {
            off: _t("Not connected"),
            connecting: _t("Connecting to the call server..."),
            ready: _t("You take the calls"),
            error: phone.message || _t("The call server does not answer"),
        }[phone.status];
    }

    get dotClass() {
        const phone = this.softphone;
        if (!phone.available) {
            return "bg-secondary";
        }
        return { ready: "bg-success", connecting: "bg-warning", error: "bg-danger", off: "bg-secondary" }[
            phone.status
        ];
    }

    toggle() {
        this.softphone.setAvailable(!this.softphone.available);
    }
}

/** The call that rings or goes on: who calls, answer, decline, mute, hang up. */
export class WhatsappSoftphonePanel extends Component {
    static template = "whatsapp_cloud_call.SoftphonePanel";

    setup() {
        this.softphone = useService("whatsapp_softphone");
        this.clock = proxy({ now: Date.now() });
        const timer = browser.setInterval(() => {
            this.clock.now = Date.now();
        }, 1000);
        onWillUnmount(() => browser.clearInterval(timer));
    }

    get call() {
        return this.softphone.incoming || this.softphone.active;
    }

    get duration() {
        const active = this.softphone.active;
        if (!active) {
            return "";
        }
        const seconds = Math.max(0, Math.floor((this.clock.now - active.startedAt) / 1000));
        const minutes = Math.floor(seconds / 60);
        return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
    }

    dismissMessage() {
        this.softphone.message = "";
    }
}

registry.category("systray").add(
    "whatsapp_cloud_call.Softphone",
    { Component: WhatsappSoftphoneSystray },
    { sequence: 104 }
);
registry.category("main_components").add("whatsapp_cloud_call.SoftphonePanel", {
    Component: WhatsappSoftphonePanel,
});
