import { Component, onWillStart, signal, useProps } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const BOOKINGS = "ocd_live.ocd_live_booking_action";

/**
 * Planning of the week for the team, as in the validated design (BoReservations): the hours of
 * the studio in rows, the days in columns, the detail of the chosen slot beside them, with
 * what the team does from there (host, payment checked, release, move, cancel and credit,
 * offer a free slot to the waiting list).
 */
export class OcdLivePlanning extends Component {
    static template = "ocd_live.Planning";
    props = useProps(standardActionServiceProps);
    data = signal(null);
    selected = signal(false);
    moving = signal(false);
    offered = signal({});

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        onWillStart(() => this.load());
    }

    async load(weekStart = this.data()?.week_start) {
        const data = await this.orm.call("ocd.live.planning", "get_planning_data", [weekStart || false]);
        this.data.set(data);
        if (!this.selected() || !data.details[this.selected()]) {
            this.selected.set(data.default_key);
        }
    }

    get detail() {
        const key = this.selected();
        return key ? this.data().details[key] : null;
    }

    cellLabel(cell, day) {
        const label = cell.sub ? `${cell.label} · ${cell.sub}` : cell.label;
        return _t("%(day)s %(hour)s: %(label)s", { day: day.label, hour: cell.key.split("|")[1], label });
    }

    async pick(cell) {
        const moving = this.moving();
        if (moving) {
            const detail = this.data().details[cell.key];
            if (cell.kind !== "free" || !detail || detail.past) {
                this.notification.add(_t("Choose a free slot to come, or cancel the move."), { type: "warning" });
                return;
            }
            await this.orm.call("ocd.live.booking", "action_ocd_team_move", [[moving], detail.start]);
            this.moving.set(false);
            this.selected.set(cell.key);
            this.notification.add(_t("The live is moved. The vendor keeps the same package."), { type: "success" });
            await this.load();
            return;
        }
        this.selected.set(cell.key);
    }

    async setHost(ev) {
        const hostId = parseInt(ev.target.value, 10) || false;
        await this.orm.write("ocd.live.booking", [this.detail.booking_id], { animatrice_id: hostId });
        await this.load();
    }

    async release() {
        await this.orm.call("ocd.live.booking", "action_cancel", [[this.detail.booking_id]]);
        this.notification.add(_t("The slot is free again: the waiting list is told."), { type: "success" });
        await this.load();
    }

    async markPaid() {
        await this.orm.call("ocd.live.booking", "action_ocd_mark_paid", [[this.detail.booking_id]]);
        this.notification.add(_t("Payment confirmed: the live is booked and the vendor receives the ticket."), {
            type: "success",
        });
        await this.load();
    }

    async offer() {
        const key = this.selected();
        const count = await this.orm.call("ocd.live.planning", "ocd_offer_free_slot", [this.detail.start]);
        this.offered.set({ ...this.offered(), [key]: true });
        this.notification.add(
            count ? _t("Sent to the waiting list of the day.") : _t("Nobody waits for this day."),
            { type: count ? "success" : "info" }
        );
        await this.load();
    }

    cancelAndCredit() {
        const bookingId = this.detail.booking_id;
        this.dialog.add(ConfirmationDialog, {
            title: _t("Cancel and credit"),
            body: _t("The live is cancelled and goes back to the lives the vendor can place. Continue?"),
            confirmLabel: _t("Cancel and credit"),
            confirm: async () => {
                await this.orm.call("ocd.live.booking", "action_cancel", [[bookingId]]);
                this.notification.add(_t("Cancelled: the live is back in the package of the vendor."), {
                    type: "success",
                });
                await this.load();
            },
            cancel: () => {},
        });
    }

    startMove() {
        this.moving.set(this.detail.booking_id);
    }

    openBooking() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ocd.live.booking",
            res_id: this.detail.booking_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newBooking() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ocd.live.booking",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRegie() {
        this.actionService.doAction(this.data().regie_action);
    }

    switchView(viewType) {
        this.actionService.doAction(BOOKINGS, { viewType });
    }
}

registry.category("actions").add("ocd_live.planning", OcdLivePlanning);
