"""The gains of the ambassadors (chantier 11, design Ambassadeurs, « Pour que ça tienne en vrai »).

One gain per parcel of an order brought by an ambassador, written when the order is confirmed
(the rate and the cap of that day), never twice (unique per parcel):

- ordered: the parcel is on its way, nothing is due;
- delivered: delivered with its code, confirmed after the days of the settings;
- held: a return was asked before the confirmation, the team decides;
- confirmed: a bill of the ambassador (a purchase bill, paid with the payouts of the shop);
- cancelled: refused at the door, returned, cancelled: nothing is due;
- taken_back: returned after the confirmation, a credit note takes it from the next payout;
- refused: the order did not count (own purchase, too many orders of a customer, account paused):
  shown to the ambassador with why, never paid.

The money is in the bills and the credit notes, once per gain (unique index on the moves); the
figures of the pages are read from them."""
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

STATES = [
    ("ordered", "On the way"),
    ("delivered", "Delivered"),
    ("held", "Return asked"),
    ("confirmed", "Confirmed"),
    ("cancelled", "No gain"),
    ("taken_back", "Taken back"),
    ("refused", "Did not count"),
]
REASONS = [
    ("own", "Their own purchase"),
    ("limit", "Too many orders of the same customer this month"),
    ("paused", "Account paused"),
    ("closed", "Program or account closed"),
    ("returned", "Refused at the door or returned"),
    ("cancelled", "Cancelled"),
]
# The gains still waiting for their parcel
OPEN_STATES = ("ordered", "delivered", "held")
# The hour of the ambassador from which the gains of the day are told
TELL_HOUR = 19


class OcdAmbassadorGain(models.Model):
    _name = "ocd.ambassador.gain"
    _description = "Gain Of An Ambassador"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"
    _check_company_auto = True

    ambassador_id = fields.Many2one(
        comodel_name="res.partner", string="Ambassador", required=True, index=True, ondelete="restrict",
    )
    order_id = fields.Many2one(comodel_name="sale.order", string="Order", required=True, index=True, ondelete="restrict")
    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Parcel", required=True, index=True, ondelete="restrict",
    )
    company_id = fields.Many2one(comodel_name="res.company", required=True, index=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    rate = fields.Float(string="Rate (%)", readonly=True, help="The rate of the day of the order.")
    amount = fields.Monetary(string="Gain", readonly=True, help="In the currency of OCD, at most the cap of the day.")
    state = fields.Selection(selection=STATES, required=True, default="ordered", index=True, tracking=True)
    reason = fields.Selection(selection=REASONS, string="Why", tracking=True)
    bad_outcome = fields.Boolean(
        string="Refused Or Returned", compute="_compute_bad_outcome", store=True, index="btree_not_null",
        help="Counts in the rate of returns of the ambassador.",
    )
    delivered_at = fields.Datetime(string="Delivered At", readonly=True, index="btree_not_null")
    confirm_on = fields.Date(string="Confirmed On", readonly=True, help="The day the gain is confirmed, if kept.")
    confirmed_at = fields.Datetime(string="Confirmed At", readonly=True)
    return_asked = fields.Boolean(string="Return Asked", readonly=True, tracking=True, index="btree_not_null")
    told = fields.Boolean(string="Told To The Ambassador", readonly=True, copy=False)
    bill_id = fields.Many2one(comodel_name="account.move", string="Bill", readonly=True, copy=False)
    refund_id = fields.Many2one(comodel_name="account.move", string="Credit Note", readonly=True, copy=False)
    products_label = fields.Char(string="Articles", readonly=True)
    customer_label = fields.Char(
        string="Customer", readonly=True, help="The first name, the initial and the district: never the number.",
    )

    _unique_parcel = models.UniqueIndex("(picking_id)", "A parcel gives one gain at most.")

    @api.depends("state", "reason")
    def _compute_bad_outcome(self):
        for gain in self:
            gain.bad_outcome = gain.state == "taken_back" or (gain.state == "cancelled" and gain.reason == "returned")

    @api.depends("order_id.name", "picking_id.name")
    def _compute_display_name(self):
        for gain in self:
            gain.display_name = " · ".join(part for part in (gain.order_id.name, gain.picking_id.name) if part)

    # === WRITTEN WITH THE ORDER === #

    @api.model
    def _ocd_labels(self, order, parcel):
        """(articles, customer) shown to the ambassador: « Robe en wax, Pagne wax », « Estelle N.
        · Akwa »."""
        lines = parcel.move_ids.sale_line_id.filtered(lambda line: not line.is_delivery and not line.display_type)
        names = []
        for line in lines:
            name = line.product_id.product_tmpl_id.name
            if name and name not in names:
                names.append(name)
        products = ", ".join(names[:3]) + ("…" if len(names) > 3 else "")
        customer = order.partner_shipping_id or order.partner_id
        words = (customer.name or "").split()
        first = f"{words[0]} {words[1][:1]}." if len(words) > 1 else (words[0] if words else "")
        district = customer.district_id.name if "district_id" in customer._fields else ""
        return products[:250], " · ".join(part for part in (first, district) if part)[:120]

    @api.model
    def _ocd_amount(self, order, parcel, ambassador):
        """The gain of `parcel` in the currency of OCD: the rate of the order on each article (not
        the delivery), never more than the commission of OCD on the article, nothing on the
        articles of the ambassador's own boutique nor on a vendor in direct contact; at most the
        cap of the order."""
        company = order.company_id
        rate = order.ocd_ambassador_rate
        total = 0.0
        for move in parcel.move_ids.filtered(lambda m: m.state != "cancel"):
            line = move.sale_line_id
            if not line or line.is_delivery or line.display_type:
                continue
            template = line.product_id.product_tmpl_id
            if template.ocd_vendor_id and not line.ocd_vendor_id:
                continue  # a vendor in direct contact: the sale does not go through OCD
            if line.ocd_vendor_id and ambassador._ocd_ambassador_same_person(line.ocd_vendor_id):
                continue  # their own products
            share = move.product_uom_qty / line.product_uom_qty if line.product_uom_qty else 1.0
            base = line.price_total * min(share, 1.0)
            part = base * rate / 100.0
            if line.ocd_vendor_id:
                part = min(part, base * line.ocd_commission_rate / 100.0)
            total += part
        currency = order.currency_id or company.currency_id
        amount = currency._convert(total, company.currency_id, company, order.date_order or fields.Datetime.now())
        cap = order.ocd_ambassador_cap
        if cap and company.currency_id.compare_amounts(amount, cap) > 0:
            amount = cap
        return company.currency_id.round(max(amount, 0.0))

    @api.model
    def _ocd_create_for(self, orders):
        """The gains of the parcels of `orders` brought by an ambassador, once per parcel."""
        gains = self.browse()
        for order in orders.sudo().filtered("ocd_ambassador_id"):
            ambassador = order.ocd_ambassador_id
            refused = order.ocd_ambassador_reason
            existing = self.sudo().search([("order_id", "=", order.id)]).picking_id
            for parcel in order.picking_ids.filtered(lambda p: p.ocd_is_parcel and p not in existing):
                products, customer = self._ocd_labels(order, parcel)
                values = {
                    "ambassador_id": ambassador.id,
                    "order_id": order.id,
                    "picking_id": parcel.id,
                    "company_id": order.company_id.id,
                    "products_label": products,
                    "customer_label": customer,
                }
                if refused:
                    values.update({"state": "refused", "reason": refused, "amount": 0.0, "rate": 0.0})
                else:
                    amount = self._ocd_amount(order, parcel, ambassador)
                    if order.company_id.currency_id.is_zero(amount):
                        continue  # nothing to earn on this parcel (own products, direct contact)
                    values.update({"amount": amount, "rate": order.ocd_ambassador_rate})
                    if parcel.ocd_stage == "delivered":
                        values.update(self._ocd_delivered_values(parcel))
                gains |= self.sudo().create(values)
        return gains

    @api.model
    def _ocd_delivered_values(self, parcel):
        company = parcel.company_id
        moment = parcel.ocd_delivered_at or fields.Datetime.now()
        local = pytz.utc.localize(moment).astimezone(company._ocd_tz()).date()
        return {
            "state": "delivered",
            "delivered_at": moment,
            "confirm_on": local + timedelta(days=max(company.ocd_ambassador_confirm_days, 0)),
        }

    # === THE PARCEL MOVES ON === #

    @api.model
    def _ocd_parcels_delivered(self, parcels):
        """Delivered with the code: confirmed after the days of the settings, if kept."""
        for gain in self.sudo().search([("picking_id", "in", parcels.ids), ("state", "=", "ordered")]):
            gain.write(self._ocd_delivered_values(gain.picking_id))
            if gain.order_id.ocd_return_requested_at:
                gain.write({"state": "held", "return_asked": True})

    @api.model
    def _ocd_parcels_failed(self, parcels, stage):
        """Refused at the door, returned or cancelled before its delivery: nothing is due. A refusal
        counts in the rate of returns of the ambassador."""
        gains = self.sudo().search([("picking_id", "in", parcels.ids), ("state", "in", OPEN_STATES)])
        if not gains:
            return
        gains.write({"state": "cancelled", "reason": "returned" if stage == "returned" else "cancelled"})
        gains.ambassador_id._ocd_ambassador_check_returns()

    @api.model
    def _ocd_return_asked(self, orders):
        """The customer asks for a return: a gain not confirmed waits for the team; a confirmed one
        is shown to the team, who takes it back once the return is made."""
        gains = self.sudo().search([("order_id", "in", orders.ids), ("state", "in", ("delivered", "confirmed"))])
        gains.filtered(lambda g: g.state == "delivered").write({"state": "held", "return_asked": True})
        gains.filtered(lambda g: g.state == "confirmed").write({"return_asked": True})

    # === CONFIRMED: THE BILL === #

    def _ocd_move(self, kind, amount, label):
        """A purchase bill (the gain) or a credit note (taken back) of the ambassador, once per
        gain and kind (a unique index of the database stops a second one)."""
        self.ensure_one()
        company = self.company_id
        product = self.env.ref("ocd_ambassadors.product_ambassador_gain" if kind == "earning"
                               else "ocd_ambassadors.product_ambassador_taken_back").product_variant_id
        move = self.env["account.move"].sudo().create({
            "move_type": "in_invoice" if kind == "earning" else "in_refund",
            "partner_id": self.ambassador_id.id,
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "invoice_date": fields.Date.context_today(self),
            "ref": self.picking_id.name,
            "invoice_origin": self.order_id.name,
            "ocd_picking_id": self.picking_id.id,
            "ocd_ambassador_kind": kind,
            "ocd_ambassador_gain_id": self.id,
            "invoice_line_ids": [fields.Command.create({
                "product_id": product.id, "name": label, "quantity": 1, "price_unit": amount,
                "tax_ids": [fields.Command.clear()],
            })],
        })
        move.action_post()
        return move

    def _ocd_confirm(self):
        """The gains kept the days of the settings after the delivery: a bill each, paid with the
        next payout of the ambassador."""
        for gain in self.sudo().filtered(lambda g: g.state == "delivered" and not g.bill_id):
            label = self.env._("Gain on %(parcel)s (%(products)s)", parcel=gain.picking_id.name,
                               products=gain.products_label or "-")
            bill = gain._ocd_move("earning", gain.amount, label)
            gain.write({"state": "confirmed", "bill_id": bill.id, "confirmed_at": fields.Datetime.now()})
        return True

    def _ocd_take_back(self):
        """Returned after the confirmation: a credit note takes the gain from the next payout (a
        balance below zero is never paid, it waits for the next gains)."""
        for gain in self.sudo().filtered(lambda g: g.state == "confirmed" and not g.refund_id):
            label = self.env._("Return of %(parcel)s (%(products)s)", parcel=gain.picking_id.name,
                               products=gain.products_label or "-")
            refund = gain._ocd_move("taken_back", gain.amount, label)
            gain.write({"state": "taken_back", "refund_id": refund.id, "return_asked": False})
        self.ambassador_id._ocd_ambassador_check_returns()
        return True

    # === THE TEAM DECIDES ON A RETURN === #

    def _ocd_check_team(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live decides on the gains of the ambassadors."))

    def action_ocd_return_done(self):
        """The return is made: nothing is due (taken back when it was confirmed)."""
        self._ocd_check_team()
        for gain in self.sudo():
            if gain.state in ("held", "delivered"):
                gain.write({"state": "cancelled", "reason": "returned", "return_asked": False})
            elif gain.state == "confirmed":
                gain._ocd_take_back()
            else:
                raise UserError(self.env._("The gain %s is already decided.", gain.display_name))
        self.ambassador_id._ocd_ambassador_check_returns()
        return True

    def action_ocd_return_refused(self):
        """No return in the end: the gain goes on (confirmed on its day)."""
        self._ocd_check_team()
        for gain in self.sudo():
            if gain.state == "held":
                gain.write({"state": "delivered", "return_asked": False})
            elif gain.state == "confirmed":
                gain.write({"return_asked": False})
        return True

    # === EVERY HOUR === #

    @api.model
    def _cron_ocd_ambassadors(self):
        """The gains whose day came are confirmed (a bill each); in the evening, each ambassador is
        told once the parcels delivered since the last message."""
        today = self.env.company._ocd_local_today()
        due = self.sudo().search([("state", "=", "delivered"), ("confirm_on", "<=", today), ("bill_id", "=", False)])
        for gain in due:
            with self.env.cr.savepoint():
                gain._ocd_confirm()
        self._ocd_tell_delivered()
        self.env["res.partner"]._cron_ocd_ambassadors_forget()

    @api.model
    def _ocd_tell_delivered(self, now=None):
        """At the hour of each ambassador, from 19:00, once a day: the parcels delivered since the
        last message (never one message per parcel)."""
        now = now or fields.Datetime.now()
        gains = self.sudo().search([("told", "=", False), ("delivered_at", "!=", False),
                                    ("state", "in", ("delivered", "held", "confirmed"))])
        for ambassador, ambassador_gains in gains.grouped("ambassador_id").items():
            local = pytz.utc.localize(now).astimezone(pytz.timezone(ambassador._ocd_tz_name() or "UTC"))
            if local.hour < TELL_HOUR or ambassador.ocd_ambassador_told_on == local.date():
                continue
            if ambassador.ocd_ambassador_state not in ("active", "to_check", "paused", "closed"):
                continue
            if ambassador._ocd_ambassador_tell_delivered(ambassador_gains):
                ambassador_gains.write({"told": True})
                ambassador.ocd_ambassador_told_on = local.date()

    # === FOR THE PAGES === #

    def _ocd_local_day(self, moment, ambassador):
        local = pytz.utc.localize(moment).astimezone(pytz.timezone(ambassador._ocd_tz_name() or "UTC"))
        return local.date()

    @api.model
    def _ocd_day_start_utc(self, day, tz_name):
        local = pytz.timezone(tz_name or "UTC").localize(datetime.combine(day, time()))
        return local.astimezone(pytz.utc).replace(tzinfo=None)
