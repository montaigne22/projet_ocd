from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

from odoo.addons.ocd_live.tools import day_text, hour_text

STATUSES = ("round", "available", "rest")


class OcdLiveCouriers(models.AbstractModel):
    """Couriers and cash, as in the validated design (BoLivreurs): a card per OCD courier with
    the status of the day, the zones, the parcels and the cash on hand, then the cash of the
    evening to count for each courier."""

    _name = "ocd.live.couriers"
    _description = "OCD Live Couriers And Cash"

    @api.model
    def get_couriers_data(self):
        company = self.env.company
        couriers = self.env["res.partner"].search([("ocd_is_courier", "=", True)], order="name")
        start, _end = self.env["ocd.live.dashboard"]._ocd_day_bounds()
        Picking = self.env["stock.picking"]
        since = fields.Datetime.now() - timedelta(days=30)
        kinds = dict(couriers._fields["ocd_courier_kind"]._description_selection(self.env))
        cards, cash_rows = [], []
        for courier in couriers:
            today = Picking.search([
                ("ocd_courier_id", "=", courier.id),
                "|", ("ocd_stage", "in", ("ready", "picked", "on_the_way", "problem")),
                "&", ("ocd_stage", "=", "delivered"), ("ocd_delivered_at", ">=", start),
            ])
            out = today.filtered(lambda parcel: parcel.ocd_stage in ("picked", "on_the_way"))
            delivered_today = today.filtered(lambda parcel: parcel.ocd_stage == "delivered")
            month = Picking.search([
                ("ocd_courier_id", "=", courier.id),
                ("ocd_stage", "=", "delivered"),
                ("ocd_delivered_at", ">=", since),
            ])
            failed = Picking.search_count([
                ("ocd_courier_id", "=", courier.id),
                ("ocd_failed_attempts", ">", 0),
                ("create_date", ">=", since),
            ])
            on_time = f"{round((len(month) / (len(month) + failed)) * 100)} %" if month or failed else "—"
            status = "round" if out else ("available" if courier.ocd_courier_available else "rest")
            cash = courier.ocd_cash_on_hand
            cards.append({
                "id": courier.id,
                "name": courier.name,
                "initials": "".join(word[:1] for word in courier.name.split()[:2]).upper(),
                "kind": kinds.get(courier.ocd_courier_kind, ""),
                "status": status,
                "phone": courier.phone or "",
                "zones": courier.ocd_courier_zone_ids.mapped("name"),
                "today": self.env._(
                    "%(count)s parcels · %(done)s delivered", count=len(today), done=len(delivered_today)
                ),
                "on_time": on_time,
                "cash": cash,
                "cash_label": self.env._("Cash on hand: %s", format_amount(self.env, cash, company.currency_id))
                if cash else self.env._("No cash on hand"),
            })
            cash_rows.append(self._ocd_cash_row(courier, start))
        return {
            "cards": cards,
            "statuses": [
                {"key": "round", "label": self.env._("On a round")},
                {"key": "available", "label": self.env._("Available")},
                {"key": "rest", "label": self.env._("Rest")},
            ],
            "cash_title": self.env._("Cash of the couriers · %s", day_text(self.env, company._ocd_local_today(), "EEE d MMM")),
            "cash_hint": self.env._(
                "Cash handed over every evening before %s.", hour_text(company.ocd_cash_deadline)
            ),
            "cash_rows": cash_rows,
            "currency_id": company.currency_id.id,
            "remittances_action": self.env["ir.actions.actions"]._for_xml_id("ocd_live_shop.ocd_cash_remittance_action"),
        }

    @api.model
    def _ocd_cash_row(self, courier, start):
        """Money collected at the door today by `courier`, and the cash to hand over."""
        Picking = self.env["stock.picking"]
        collected = Picking.search([
            ("ocd_cod_collected_by_id", "=", courier.id),
            ("ocd_cod_collected_at", ">=", start),
        ])
        cash_today = sum(collected.filtered(lambda parcel: parcel.ocd_cod_method == "cash").mapped("ocd_cod_collected_amount"))
        momo_today = sum(collected.filtered(lambda parcel: parcel.ocd_cod_method != "cash").mapped("ocd_cod_collected_amount"))
        due = courier.ocd_cash_on_hand
        counted = self.env["ocd.cash.remittance"].search(
            [("courier_id", "=", courier.id), ("state", "=", "done"), ("date", ">=", start)],
            order="date desc",
            limit=1,
        )
        if due:
            state = ""
        elif counted:
            state = self.env._("Handed over at the cash desk")
            if not counted.currency_id.is_zero(counted.difference):
                state = self.env._("Difference reported to the manager")
        else:
            state = self.env._("Nothing to hand over")
        return {
            "id": courier.id,
            "name": courier.name,
            "cash": cash_today,
            "momo": momo_today,
            "due": due,
            "received": counted.amount_received if counted and not due else 0.0,
            "difference": counted.difference if counted and not due else 0.0,
            "state": state,
        }

    @api.model
    def ocd_set_status(self, courier_id, status):
        if status not in STATUSES:
            raise UserError(self.env._("Unknown status: %s", status))
        courier = self.env["res.partner"].browse(courier_id).exists()
        if not courier or not courier.ocd_is_courier:
            raise UserError(self.env._("This courier no longer exists."))
        courier.ocd_courier_available = status != "rest"
        return True

    @api.model
    def ocd_save_remittance(self, courier_id, amount):
        """Save the cash handed over by a courier this evening."""
        courier = self.env["res.partner"].browse(courier_id).exists()
        if not courier or not courier.ocd_is_courier:
            raise UserError(self.env._("This courier no longer exists."))
        remittance = self.env["ocd.cash.remittance"]._ocd_open_for(courier)
        remittance.amount_received = float(amount or 0.0)
        remittance.action_done()
        return remittance.difference
