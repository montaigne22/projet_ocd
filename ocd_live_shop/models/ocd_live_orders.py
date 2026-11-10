from datetime import timedelta

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

from odoo.addons.ocd_live.tools import day_text

from .stock_picking import OPEN_STAGES

FILTERS = ("all", "todo", "issue", "cod")


class OcdLiveOrders(models.AbstractModel):
    """Orders of the shop, as in the validated design (BoCommandes): the orders of the week
    grouped by day, with their payment and their delivery, and the detail of the chosen order
    beside them (lines, share of each vendor, parcels, what to do, history)."""

    _name = "ocd.live.orders"
    _description = "OCD Live Shop Orders"

    @api.model
    def _ocd_orders(self, since):
        return self.env["sale.order"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("state", "in", ("sale", "cancel")),
                ("date_order", ">=", since),
                ("picking_ids.ocd_is_parcel", "=", True),
            ],
            order="date_order desc",
        )

    @api.model
    def get_orders_data(self):
        company = self.env.company
        today = company._ocd_local_today()
        monday = today - timedelta(days=today.weekday())
        since, _end = self.env["ocd.live.dashboard"]._ocd_day_bounds(monday)
        orders = self._ocd_orders(since)
        rows = [self._ocd_row(order) for order in orders]
        groups = []
        for row in rows:
            if not groups or groups[-1]["key"] != row["day"]:
                groups.append({"key": row["day"], "label": row["day_label"], "rows": []})
            groups[-1]["rows"].append(row)
        return {
            "facet": self.env._("Since %s", day_text(self.env, monday, "EEE d MMM")),
            "groups": groups,
            "currency_id": company.currency_id.id,
            "selected": rows[0]["id"] if rows else False,
        }

    # === ROWS === #

    @api.model
    def _ocd_parcels(self, order):
        return order.picking_ids.filtered("ocd_is_parcel")

    @api.model
    def _ocd_row(self, order):
        company = order.company_id
        local = company._ocd_to_local(order.date_order)
        parcels = self._ocd_parcels(order)
        vendors = parcels.ocd_vendor_id
        vendor_text = vendors[:1].name or ""
        if len(vendors) > 1:
            vendor_text = self.env._("%(vendor)s + %(count)s", vendor=vendor_text, count=len(vendors) - 1)
        status, tone, sub = self._ocd_delivery_status(order, parcels)
        payment, payment_tone = self._ocd_payment_tag(order, parcels)
        open_parcels = parcels.filtered(lambda parcel: parcel.ocd_stage in OPEN_STAGES)
        return {
            "id": order.id,
            "ref": order.name,
            "day": local.date().isoformat(),
            "day_label": day_text(self.env, local.date(), "EEEE d MMMM", capital=True),
            "time": local.strftime("%H:%M"),
            "client": order.partner_id.name,
            "place": order.partner_shipping_id.district_id.name or order.partner_shipping_id.city or "",
            "vendor": vendor_text,
            "total": format_amount(self.env, order.amount_total, order.currency_id),
            "amount": order.currency_id._convert(order.amount_total, company.currency_id, company, order.date_order),
            "payment": payment,
            "payment_tone": payment_tone,
            "status": status,
            "status_tone": tone,
            "status_sub": sub,
            "todo": bool(open_parcels),
            "issue": any(parcel.ocd_is_late or parcel.ocd_stage == "problem" for parcel in parcels),
            "cod": any(parcel.ocd_cod_state != "none" for parcel in parcels),
        }

    @api.model
    def _ocd_payment_tag(self, order, parcels):
        if order.state == "cancel":
            return self.env._("Cancelled"), "grey"
        if any(parcel.ocd_cod_state == "to_collect" for parcel in parcels):
            return self.env._("At the door"), "yellow"
        if any(parcel.ocd_cod_state in ("collected", "remitted") for parcel in parcels):
            return self.env._("Paid at the door"), "grey"
        # sudo: only the provider of the payment is read
        done = order.sudo().transaction_ids.filtered(lambda tx: tx.state == "done")[:1]
        return (done.provider_id.name if done else self.env._("Paid online")), "green"

    @api.model
    def _ocd_delivery_status(self, order, parcels):
        if order.state == "cancel":
            return self.env._("Cancelled"), "grey", ""
        if not parcels:
            return self.env._("No parcel"), "grey", ""
        delivered = parcels.filtered(lambda parcel: parcel.ocd_stage == "delivered")
        if any(parcel.ocd_stage == "problem" for parcel in parcels):
            return self.env._("Problem"), "red", self.env._("%(done)s of %(count)s delivered", done=len(delivered), count=len(parcels))
        if any(parcel.ocd_is_late for parcel in parcels):
            return self.env._("Late"), "red", self.env._("%(done)s of %(count)s delivered", done=len(delivered), count=len(parcels))
        if len(delivered) == len(parcels.filtered(lambda parcel: parcel.ocd_stage not in ("cancelled", "returned"))):
            return self.env._("Delivered"), "green", ""
        stages = dict(parcels._fields["ocd_stage"]._description_selection(self.env))
        steps = ", ".join(sorted({stages[parcel.ocd_stage].lower() for parcel in parcels if parcel.ocd_stage in OPEN_STAGES}))
        return self.env._("In progress"), "yellow", steps

    # === DETAIL === #

    @api.model
    def get_order_detail(self, order_id):
        order = self.env["sale.order"].browse(order_id).exists()
        if not order:
            raise UserError(self.env._("This order no longer exists."))
        company = order.company_id
        parcels = self._ocd_parcels(order)
        local = company._ocd_to_local(order.date_order)
        status, tone, _sub = self._ocd_delivery_status(order, parcels)
        currency = order.currency_id
        lines = []
        fee = 0.0
        for line in order.order_line.filtered(lambda line: not line.display_type):
            if line.is_delivery:
                fee += line.price_total
                continue
            name = line.product_id.name
            if line.product_uom_qty > 1:
                name = f"{name} × {int(line.product_uom_qty)}"
            vendor = line.ocd_vendor_id or line.product_id.product_tmpl_id.ocd_vendor_id
            vendor_text = vendor.name or ""
            if line.ocd_vendor_id:
                vendor_text = self.env._(
                    "%(vendor)s · share %(amount)s", vendor=vendor.name,
                    amount=format_amount(self.env, line.ocd_vendor_share, currency),
                )
            lines.append({"id": line.id, "name": name, "vendor": vendor_text, "price": format_amount(self.env, line.price_total, currency)})
        dispatch = self.env["ocd.live.dispatch"]
        cards = [dispatch._ocd_card(parcel) for parcel in parcels]
        stages = dict(parcels._fields["ocd_stage"]._description_selection(self.env))
        phone = "".join(char for char in (order.partner_id.phone or "") if char.isdigit())
        first_name = (order.partner_id.name or "").split()[0] if order.partner_id.name else ""
        return {
            "id": order.id,
            "ref": order.name,
            "state": status,
            "state_tone": tone,
            "when": self.env._(
                "%(day)s at %(hour)s · shop of OCD",
                day=day_text(self.env, local.date(), "EEEE d MMM", capital=True),
                hour=local.strftime("%H:%M"),
            ),
            "client": order.partner_id.name,
            "phone": order.partner_id.phone or "",
            "place": " · ".join(
                part for part in (order.partner_shipping_id.district_id.name, order.partner_shipping_id.delivery_landmark) if part
            ),
            "lines": lines,
            "fee": format_amount(self.env, fee, currency) if fee else "",
            "total": format_amount(self.env, order.amount_total, currency),
            "payment": self._ocd_payment_text(order, parcels),
            "payment_tone": self._ocd_payment_tag(order, parcels)[1],
            "parcels": [
                {
                    "id": card["id"],
                    "ref": card["ref"],
                    "stage": stages.get(parcel.ocd_stage, ""),
                    "tone": card["tone"] if card["tag"] else "grey",
                    "route": f"{parcel.ocd_vendor_id.name or ''} → {card['who_label']}",
                    "note": card["note"],
                    "alert": card["alert"],
                    "can_switch": card["can_switch"],
                    "can_retry": card["can_retry"],
                }
                for parcel, card in zip(parcels, cards)
            ],
            "whatsapp_url": f"https://wa.me/{phone}" if phone else "",
            "whatsapp_label": self.env._("Write to %s on WhatsApp", first_name) if first_name else "",
            "todo": any(card["column"] not in ("done",) for card in cards),
            "history": self._ocd_history(order, parcels),
        }

    @api.model
    def _ocd_payment_text(self, order, parcels):
        currency = order.currency_id
        total = format_amount(self.env, order.amount_total, currency)
        if order.state == "cancel":
            return self.env._("Order cancelled.")
        to_collect = parcels.filtered(lambda parcel: parcel.ocd_cod_state == "to_collect")
        if to_collect:
            return self.env._("To collect at the door: %s.", format_amount(
                self.env, sum(to_collect.mapped("ocd_cod_amount")), currency))
        collected = parcels.filtered(lambda parcel: parcel.ocd_cod_state in ("collected", "remitted"))
        if collected:
            return self.env._("Paid at the door: %s.", format_amount(
                self.env, sum(collected.mapped("ocd_cod_collected_amount")), currency))
        done = order.sudo().transaction_ids.filtered(lambda tx: tx.state == "done")[:1]
        if done:
            return self.env._("Paid online with %(provider)s: %(total)s.", provider=done.provider_id.name, total=total)
        return self.env._("Paid: %s.", total)

    @api.model
    def _ocd_history(self, order, parcels):
        company = order.company_id
        events = [(order.date_order, self.env._("Order received"))]
        for parcel in parcels:
            for field, text in (
                ("ocd_ready_at", self.env._("%s ready")),
                ("ocd_picked_at", self.env._("%s picked up")),
                ("ocd_left_at", self.env._("%s left, code sent to the customer")),
                ("ocd_delivered_at", self.env._("%s delivered")),
            ):
                if parcel[field]:
                    events.append((parcel[field], text % parcel.name))
        events.sort(key=lambda event: event[0])
        return [
            {"time": company._ocd_to_local(moment).strftime("%H:%M"), "text": text}
            for moment, text in events
        ]
