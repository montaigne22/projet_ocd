from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

from .stock_picking import OPEN_STAGES

# Columns of the dispatch, as in the design: steps of the parcel grouped
COLUMNS = [
    ("prep", ("to_prepare",)),
    ("ready", ("ready", "picked")),
    ("route", ("on_the_way", "at_relay")),
    ("done", ("delivered",)),
    ("problem", ("problem",)),
]
# The cards of a column, for each kind of courier (OCD, vendor): the alerts first, then the oldest.
# Beyond, the column gives its true count and opens the list of its parcels: hundreds of cards
# help nobody and slow the screen down.
CARDS_PER_COLUMN = 40


class OcdLiveDispatch(models.AbstractModel):
    """Dispatch of the parcels of the day, as in the validated design (BoDispatch): the parcels
    by step, who delivers each of them, the money to collect, and beside them the OCD couriers
    and the vendors who deliver."""

    _name = "ocd.live.dispatch"
    _description = "OCD Live Dispatch"

    @api.model
    def _ocd_parcels_domain(self, column=None):
        """The parcels of the dispatch (of one column): open, or delivered today."""
        start, _end = self.env["ocd.live.dashboard"]._ocd_day_bounds()
        domain = [("ocd_is_parcel", "=", True), ("company_id", "=", self.env.company.id)]
        stages = dict(COLUMNS).get(column)
        if column == "done":
            return domain + [("ocd_stage", "=", "delivered"), ("ocd_delivered_at", ">=", start)]
        if stages:
            return domain + [("ocd_stage", "in", stages)]
        return domain + ["|", ("ocd_stage", "in", OPEN_STAGES), "&", ("ocd_stage", "=", "delivered"),
                         ("ocd_delivered_at", ">=", start)]

    @api.model
    def _ocd_column_labels(self):
        return {
            "prep": self.env._("To prepare"),
            "ready": self.env._("Ready"),
            "route": self.env._("On the way"),
            "done": self.env._("Delivered today"),
            "problem": self.env._("Problem"),
        }

    @api.model
    def _ocd_by(self, parcel):
        """Who delivers the parcel: « vendor » or « ocd »."""
        return "vendor" if parcel._ocd_vendor_delivers() or parcel.ocd_delivery_mode == "vendor" else "ocd"

    @api.model
    def get_dispatch_data(self):
        company = self.env.company
        parcels = self.env["stock.picking"].search(self._ocd_parcels_domain(), order="create_date")
        # Each column, for each kind of courier: its count, and the cards of its first parcels
        groups = {}
        for parcel in parcels:
            groups.setdefault((self._ocd_column(parcel), self._ocd_by(parcel)), []).append(parcel)
        shown = set()
        for group in groups.values():
            group.sort(key=lambda parcel: not (parcel.ocd_is_late or parcel.ocd_stage == "problem" or parcel.ocd_code_locked))
            shown.update(parcel.id for parcel in group[:CARDS_PER_COLUMN])
        # A new recordset: the amounts computed for the cards shown only, not for every parcel
        cards = [self._ocd_card(parcel) for parcel in self.env["stock.picking"].browse(
            [parcel.id for parcel in parcels if parcel.id in shown]
        )]
        cards.sort(key=lambda card: not card["alert"])
        labels = self._ocd_column_labels()
        late = sum(1 for parcel in parcels if parcel.ocd_is_late)
        problems = sum(1 for parcel in parcels if parcel.ocd_stage == "problem")
        alerts = []
        if late:
            alerts.append(self.env._("%s late", late))
        if problems:
            alerts.append(self.env._("%s problems", problems) if problems > 1 else self.env._("1 problem"))
        now = company._ocd_to_local(fields.Datetime.now())
        couriers = self.env["res.partner"].search([("ocd_is_courier", "=", True)])
        def count(column=None, by=None):
            return sum(len(group) for (key, kind), group in groups.items()
                       if (column is None or key == column) and (by is None or kind == by))

        return {
            "columns": [{
                "key": key,
                "label": labels[key],
                "counts": {"all": count(key), "ocd": count(key, "ocd"), "vendor": count(key, "vendor")},
            } for key, _stages in COLUMNS],
            "cards": cards,
            "counts": {"all": len(parcels), "ocd": count(by="ocd"), "vendor": count(by="vendor")},
            "alert": " · ".join(alerts),
            "subtitle": self.env._("Grouped by step · %s", now.strftime("%H:%M")),
            "couriers": [self._ocd_courier_row(courier, parcels) for courier in couriers],
            "vendors": self._ocd_vendor_rows(parcels),
            "courier_options": [
                {"id": courier.id, "name": courier.name}
                for courier in couriers.filtered("ocd_courier_available")
            ],
            "cash_action": self.env["ir.actions.actions"]._for_xml_id("ocd_live_shop.ocd_live_couriers_action"),
        }

    # === CARDS === #

    @api.model
    def _ocd_column(self, parcel):
        return next(key for key, stages in COLUMNS if parcel.ocd_stage in stages)

    @api.model
    def ocd_column_action(self, column, by="all"):
        """The list of the parcels of a column (those of a kind of courier), when it has more
        parcels than cards."""
        labels = self._ocd_column_labels()
        if column not in labels:
            raise UserError(self.env._("This step of the dispatch does not exist."))
        domain = self._ocd_parcels_domain(column)
        if by in ("ocd", "vendor"):
            parcels = self.env["stock.picking"].search(domain)
            domain = [("id", "in", [parcel.id for parcel in parcels if self._ocd_by(parcel) == by])]
        action = self.env["ocd.live.dashboard"]._ocd_action(
            "ocd_live_shop.stock_picking_action_ocd_dispatch", domain, self.env._("Dispatch · %s", labels[column]),
        )
        action["context"] = {"create": False}
        return action

    @api.model
    def _ocd_card(self, parcel):
        company = parcel.company_id
        column = self._ocd_column(parcel)
        by = self._ocd_by(parcel)
        late = parcel.ocd_is_late
        if column == "done":
            tag, tone = self.env._("Delivered"), "green"
        elif column == "problem":
            tag, tone = self.env._("To call back"), "red"
        elif parcel.ocd_code_locked:
            tag, tone = self.env._("Locked"), "red"
        elif late:
            tag, tone = self.env._("Late"), "red"
        elif not parcel.ocd_courier_id:
            tag, tone = self.env._("No courier"), "yellow"
        else:
            deadline = parcel.create_date + timedelta(hours=self._ocd_prep_hours(parcel))
            tag = self.env._("Before %s", company._ocd_to_local(deadline).strftime("%H:%M")) if column == "prep" else ""
            tone = "grey"
        place = " · ".join(part for part in (parcel.ocd_district_id.name, parcel.ocd_landmark) if part)
        items = ", ".join(
            f"{move.product_id.name} × {int(move.product_uom_qty)}" if move.product_uom_qty > 1 else move.product_id.name
            for move in parcel.move_ids.filtered(lambda move: move.state != "cancel")
        )
        who = parcel.ocd_courier_id
        return {
            "id": parcel.id,
            "ref": parcel.name,
            "column": column,
            "tag": tag,
            "tone": tone,
            "client": parcel.partner_id.name,
            "place": place or parcel.partner_id.city or "",
            "items": items,
            "vendor": parcel.ocd_vendor_id.name or "",
            "by": by,
            "who": who.name or "",
            "who_label": who.name or self.env._("No courier"),
            "by_label": self.env._("Delivered by the vendor") if by == "vendor" else self.env._("OCD courier"),
            "initials": "".join(word[:1] for word in (who.name or "?").split()[:2]).upper(),
            "money": self._ocd_money_text(parcel),
            "money_tone": self._ocd_money_tone(parcel),
            "note": self._ocd_note(parcel, column),
            "late": late,
            "alert": late or column == "problem" or parcel.ocd_code_locked,
            "can_assign": by == "ocd" and column in ("prep", "ready"),
            "can_switch": by == "vendor" and column in ("prep", "ready", "problem"),
            "can_retry": column == "problem",
        }

    @api.model
    def _ocd_prep_hours(self, parcel):
        vendor = parcel.ocd_vendor_id
        return vendor._ocd_prep_hours() if vendor else parcel.company_id.ocd_prep_hours

    @api.model
    def _ocd_money_text(self, parcel):
        currency = parcel.ocd_currency_id or parcel.company_id.currency_id
        if parcel.ocd_cod_state == "to_collect":
            return self.env._("To collect %s", format_amount(self.env, parcel.ocd_cod_amount, currency))
        if parcel.ocd_cod_state in ("collected", "remitted"):
            methods = dict(parcel._fields["ocd_cod_method"]._description_selection(self.env))
            return self.env._(
                "%(amount)s · %(method)s",
                amount=format_amount(self.env, parcel.ocd_cod_collected_amount, currency),
                method=(methods.get(parcel.ocd_cod_method) or "").lower(),
            )
        return self.env._("Paid online")

    @api.model
    def _ocd_money_tone(self, parcel):
        if parcel.ocd_cod_state == "to_collect":
            return "yellow"
        return "grey" if parcel.ocd_cod_state in ("collected", "remitted") else "green"

    @api.model
    def _ocd_note(self, parcel, column):
        company = parcel.company_id

        def hour(value):
            return company._ocd_to_local(value).strftime("%H:%M") if value else ""

        if column == "problem":
            reasons = dict(parcel._fields["ocd_problem_reason"]._description_selection(self.env))
            text = reasons.get(parcel.ocd_problem_reason) or self.env._("Problem")
            return f"{text} · {parcel.ocd_problem_note}" if parcel.ocd_problem_note else text
        if column == "done":
            if parcel.ocd_forced_by_id:
                return self.env._("%s · validated without the code", hour(parcel.ocd_delivered_at))
            return self.env._("%s · code checked", hour(parcel.ocd_delivered_at))
        if column == "route":
            return self.env._("Left at %s · code sent", hour(parcel.ocd_left_at))
        if parcel.ocd_code_locked:
            return self.env._("Locked after too many wrong codes: call the customer")
        if parcel.ocd_stage == "picked":
            return self.env._("Picked up at %s", hour(parcel.ocd_picked_at))
        if parcel.ocd_is_late:
            return self.env._("Not ready, vendor reminded at %s", hour(parcel.ocd_reminded_at))
        if not parcel.ocd_courier_id:
            return self.env._("No courier: choose one")
        if column == "ready":
            if parcel._ocd_vendor_delivers():
                return self.env._("Ready since %s", hour(parcel.ocd_ready_at))
            return self.env._("%s picks it up at the vendor", parcel.ocd_courier_id.name.split()[0])
        deadline = parcel.create_date + timedelta(hours=self._ocd_prep_hours(parcel))
        return self.env._("To prepare before %s", hour(deadline))

    # === SIDE PANEL === #

    @api.model
    def _ocd_courier_row(self, courier, parcels):
        mine = parcels.filtered(lambda parcel: parcel.ocd_courier_id == courier)
        delivered = len(mine.filtered(lambda parcel: parcel.ocd_stage == "delivered"))
        problems = len(mine.filtered(lambda parcel: parcel.ocd_stage == "problem"))
        out = mine.filtered(lambda parcel: parcel.ocd_stage in ("picked", "on_the_way"))
        if out:
            status, tone = self.env._("On a round"), "green"
        elif courier.ocd_courier_available:
            status, tone = self.env._("Available"), "grey"
        else:
            status, tone = self.env._("Off duty"), "grey"
        summary = self.env._("%(count)s parcels · %(delivered)s delivered", count=len(mine), delivered=delivered)
        if problems == 1:
            summary = self.env._("%(summary)s · 1 problem", summary=summary)
        elif problems:
            summary = self.env._("%(summary)s · %(problems)s problems", summary=summary, problems=problems)
        cash = courier.ocd_cash_on_hand
        return {
            "id": courier.id,
            "name": courier.name,
            "initials": "".join(word[:1] for word in courier.name.split()[:2]).upper(),
            "status": status,
            "tone": tone,
            "summary": summary,
            "cash": self.env._("Cash: %s to hand over", self.env["ocd.live.dashboard"]._ocd_money(cash)),
            "has_cash": cash > 0,
        }

    @api.model
    def _ocd_vendor_rows(self, parcels):
        rows = []
        delivering = parcels.filtered(lambda parcel: parcel._ocd_vendor_delivers())
        for vendor in delivering.ocd_vendor_id:
            mine = delivering.filtered(lambda parcel: parcel.ocd_vendor_id == vendor)
            late = any(mine.mapped("ocd_is_late"))
            if late:
                state = self.env._("late")
            elif mine.filtered(lambda parcel: parcel.ocd_stage == "on_the_way"):
                state = self.env._("on the way")
            elif mine.filtered(lambda parcel: parcel.ocd_stage == "delivered"):
                state = self.env._("delivered")
            else:
                state = self.env._("to prepare or ready")
            rows.append({
                "id": vendor.id,
                "name": vendor.name,
                "initials": "".join(word[:1] for word in vendor.name.split()[:2]).upper(),
                "summary": self.env._("%(count)s parcels · %(state)s", count=len(mine), state=state),
                "late": late,
            })
        return rows

    # === ACTIONS === #

    @api.model
    def _ocd_parcel(self, picking_id):
        parcel = self.env["stock.picking"].browse(picking_id).exists()
        if not parcel or not parcel.ocd_is_parcel:
            raise UserError(self.env._("This parcel no longer exists."))
        return parcel

    @api.model
    def ocd_assign(self, picking_id, courier_id):
        parcel = self._ocd_parcel(picking_id)
        courier = self.env["res.partner"].browse(courier_id).exists()
        if courier and not courier.ocd_is_courier:
            raise UserError(self.env._("%s is not an OCD courier.", courier.name))
        parcel._ocd_assign_courier(courier)
        return True

    @api.model
    def ocd_switch_to_ocd(self, picking_id):
        return self._ocd_parcel(picking_id).action_ocd_switch_to_ocd()

    @api.model
    def ocd_retry(self, picking_id):
        return self._ocd_parcel(picking_id).action_ocd_retry()
