import { Component, onMounted, onWillStart, onWillUnmount, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const REFRESH_SECONDS = 30;

function parseUtc(value) {
    return new Date(value.replace(" ", "T") + "Z").getTime();
}

function clockText(milliseconds) {
    const total = Math.max(0, Math.floor(milliseconds / 1000));
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(Math.floor(total / 3600))}:${pad(Math.floor((total % 3600) / 60))}:${pad(total % 60)}`;
}

/**
 * Live control room of the team, as in the validated design (Regie): the live of now and its
 * figures, the products of the vendor (the one touched is shown at once on the boutique and
 * noted for the replay), the moments of the replay and the replay link after the live.
 */
export class OcdLiveRegie extends Component {
    static template = "ocd_live_shop.Regie";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    clock = signal("00:00:00");
    replay = signal("");

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.bookingId = this.props.action?.params?.booking_id || false;
        onWillStart(() => this.load());
        onMounted(() => {
            this.ticker = setInterval(() => this.tick(), 1000);
            this.refresher = setInterval(() => this.data()?.status === "live" && this.load(), REFRESH_SECONDS * 1000);
        });
        onWillUnmount(() => {
            clearInterval(this.ticker);
            clearInterval(this.refresher);
        });
    }

    async load() {
        const data = await this.orm.call("ocd.live.regie", "get_regie_data", [this.bookingId]);
        this.bookingId = data.booking_id || this.bookingId;
        this.offset = data.now ? parseUtc(data.now) - Date.now() : 0;
        if (!this.data() || this.data().booking_id !== data.booking_id) {
            this.replay.set(data.replay_url || "");
        }
        this.data.set(data);
        this.tick();
    }

    tick() {
        const data = this.data();
        if (!data?.booking_id) {
            return;
        }
        const now = Date.now() + this.offset;
        const start = parseUtc(data.start);
        const end = parseUtc(data.end);
        if (now < start) {
            this.clock.set(clockText(start - now));
        } else {
            this.clock.set(clockText(Math.min(now, end) - start));
        }
    }

    get statusLabel() {
        const status = this.data().status;
        if (status === "live") {
            return _t("Live now");
        }
        return status === "coming" ? _t("Next live") : _t("Ended");
    }

    get clockCaption() {
        const status = this.data().status;
        if (status === "coming") {
            return _t("before the start");
        }
        return status === "live" ? _t("since the start") : _t("of live");
    }

    get openLabel() {
        const platform = this.data().platform;
        return platform ? _t("Open the live on %s", platform) : _t("Open the live");
    }

    async show(product) {
        if (product.shown) {
            return;
        }
        await this.orm.call("ocd.live.regie", "ocd_show_product", [this.bookingId, product.id]);
        await this.load();
    }

    async publish() {
        await this.orm.call("ocd.live.regie", "ocd_publish_replay", [this.bookingId, this.replay()]);
        this.notification.add(_t("Replay published in the boutique of the vendor."), { type: "success" });
        await this.load();
    }

    async hostCalled() {
        await this.orm.call("ocd.live.regie", "host_called", [this.bookingId]);
        await this.load();
    }

    openOrders() {
        this.actionService.doAction(this.data().orders_action);
    }

    openLive() {
        window.open(this.data().live_url, "_blank", "noopener");
    }
}

registry.category("actions").add("ocd_live_shop.regie", OcdLiveRegie);
