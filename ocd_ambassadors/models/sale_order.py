"""The orders brought by an ambassador (chantier 11, design Ambassadeurs, « Le lien, compté
proprement »).

The personal link of an ambassador (/a/<code>) is kept in the session of the phone: the last link
opened counts, for the days of the settings. The cart remembers it; when the order is confirmed,
the ambassador is written on it with the rate and the cap of that day, or why it does not count
(their own purchase, too many orders of the same customer this month, account paused or closed),
and never changes after. The gains of its parcels follow (ocd.ambassador.gain)."""
from datetime import datetime, timedelta

import pytz

from odoo import fields, models
from odoo.http import request

from .ocd_ambassador_gain import REASONS
from .res_partner import same_number

SESSION_KEY = "ocd_ambassador"


def session_link(now=None):
    """(ambassador id, datetime of the link) kept on this phone, or (0, None)."""
    if not request:
        return 0, None
    value = request.session.get(SESSION_KEY) or {}
    try:
        partner_id = int(value.get("id") or 0)
        moment = datetime.fromisoformat(value.get("at") or "")
    except (TypeError, ValueError, AttributeError):
        return 0, None
    return partner_id, moment


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_ambassador_id = fields.Many2one(
        comodel_name="res.partner", string="Ambassador", copy=False, index="btree_not_null", readonly=True,
        help="The last link of an ambassador opened on this phone before the order.",
    )
    ocd_ambassador_at = fields.Datetime(string="Link Opened At", copy=False, readonly=True)
    ocd_ambassador_rate = fields.Float(string="Ambassador Rate (%)", copy=False, readonly=True)
    ocd_ambassador_cap = fields.Float(string="Ambassador Cap Per Parcel", copy=False, readonly=True)
    ocd_ambassador_reason = fields.Selection(
        selection=REASONS[:4], string="Why It Did Not Count", copy=False, readonly=True,
    )
    ocd_ambassador_gain_ids = fields.One2many(
        comodel_name="ocd.ambassador.gain", inverse_name="order_id", string="Gains Of The Ambassador",
    )

    # === THE CART === #

    def _ocd_note_ambassador(self, partner_id, moment):
        """The cart remembers the last link opened (a newer link replaces an older one)."""
        for order in self.filtered(lambda o: o.state == "draft"):
            if not partner_id or (order.ocd_ambassador_at and order.ocd_ambassador_at >= moment):
                continue
            order.sudo().write({"ocd_ambassador_id": partner_id, "ocd_ambassador_at": moment})

    def _verify_cart_after_update(self):
        super()._verify_cart_after_update()
        partner_id, moment = session_link()
        if partner_id and moment:
            self._ocd_note_ambassador(partner_id, moment)

    # === CONFIRMED === #

    def _action_confirm(self):
        result = super()._action_confirm()
        self._ocd_ambassador_attribute()
        return result

    def _ocd_ambassador_attribute(self):
        """Write the ambassador on the confirmed order with the rules of the day, or why it does
        not count; then the gains of its parcels."""
        for order in self.sudo().filtered(lambda o: o.ocd_ambassador_id and not o.ocd_ambassador_gain_ids):
            company = order.company_id
            ambassador = order.ocd_ambassador_id
            moment = order.date_order or fields.Datetime.now()
            days = max(company.ocd_ambassador_link_days, 0)
            if not order.ocd_ambassador_at or moment - order.ocd_ambassador_at > timedelta(days=days):
                # The link is too old: the order is the customer's own
                order.write({"ocd_ambassador_id": False, "ocd_ambassador_at": False})
                continue
            reason = order._ocd_ambassador_refusal(ambassador)
            if reason is None:
                order.write({"ocd_ambassador_id": False, "ocd_ambassador_at": False})
                continue
            if reason:
                order.write({"ocd_ambassador_reason": reason, "ocd_ambassador_rate": 0.0, "ocd_ambassador_cap": 0.0})
            else:
                order.write({
                    "ocd_ambassador_rate": company.ocd_ambassador_rate,
                    "ocd_ambassador_cap": company.ocd_ambassador_cap,
                })
            self.env["ocd.ambassador.gain"]._ocd_create_for(order)

    def _ocd_ambassador_refusal(self, ambassador):
        """Why the order does not count for `ambassador` (a reason), False when it counts, None
        when the ambassador is not one any more (account never opened)."""
        self.ensure_one()
        company = self.company_id
        state = ambassador.ocd_ambassador_state
        if state in ("new", "requested", False):
            return None
        if state == "closed" or company.ocd_ambassador_open == "closed":
            return "closed"
        if state == "paused":
            return "paused"
        if ambassador._ocd_ambassador_same_person(self.partner_id) or (
                self.partner_shipping_id and ambassador._ocd_ambassador_same_person(self.partner_shipping_id)):
            return "own"
        if company.ocd_ambassador_rate <= 0:
            return "closed"
        limit = company.ocd_ambassador_customer_month
        if limit and self._ocd_ambassador_customer_orders(ambassador) >= limit:
            return "limit"
        return False

    def _ocd_ambassador_customer_orders(self, ambassador):
        """The orders of the same customer (the contact or the number) that counted for
        `ambassador` this month, at the hour of OCD."""
        self.ensure_one()
        company = self.company_id
        tz = company._ocd_tz()
        local = pytz.utc.localize(self.date_order or fields.Datetime.now()).astimezone(tz)
        start = tz.localize(datetime(local.year, local.month, 1)).astimezone(pytz.utc).replace(tzinfo=None)
        orders = self.sudo().search([
            ("ocd_ambassador_id", "=", ambassador.id), ("ocd_ambassador_rate", ">", 0),
            ("date_order", ">=", start), ("id", "!=", self.id), ("state", "=", "sale"),
        ])
        customer = self.partner_id
        numbers = [number for number in (customer.phone, self.partner_shipping_id.phone) if number]
        return len(orders.filtered(lambda order: order.partner_id == customer or any(
            same_number(number, theirs) for number in numbers
            for theirs in (order.partner_id.phone, order.partner_shipping_id.phone) if theirs
        )))

    # === RETURN ASKED === #

    def _ocd_request_return(self):
        result = super()._ocd_request_return()
        self.env["ocd.ambassador.gain"]._ocd_return_asked(self)
        return result
