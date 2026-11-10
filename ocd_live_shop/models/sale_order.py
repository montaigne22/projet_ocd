from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_rating = fields.Integer(
        string="Rating Of The Customer", copy=False, readonly=True,
        help="From 1 to 5, given by the customer on the tracking page once delivered.",
    )
    ocd_return_requested_at = fields.Datetime(string="Return Asked At", copy=False, readonly=True)
    ocd_parcel_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_ocd_parcel_ids",
        string="Parcels",
    )

    def _compute_ocd_parcel_ids(self):
        for order in self:
            order.ocd_parcel_ids = order.picking_ids.filtered("ocd_is_parcel")

    def _ocd_delivery_fee(self):
        """Return the delivery fee paid by the customer for the whole order."""
        self.ensure_one()
        return sum(self.order_line.filtered(lambda l: l._is_delivery()).mapped("price_total"))

    def _ocd_is_paid_online(self):
        """Whether the customer already paid the whole order online."""
        self.ensure_one()
        return self.currency_id.compare_amounts(self.amount_paid, self.amount_total) >= 0

    # === TRACKING PAGE OF THE CUSTOMER === #

    def _ocd_rate(self, stars):
        """The customer rates the order, from 1 to 5, once a parcel is delivered."""
        self.ensure_one()
        if not 1 <= stars <= 5:
            raise UserError(self.env._("Choose from 1 to 5."))
        if not self.ocd_parcel_ids.filtered(lambda p: p.ocd_stage == "delivered"):
            raise UserError(self.env._("The order is not delivered yet."))
        self.sudo().ocd_rating = stars
        self.sudo().message_post(body=self.env._("The customer rated the order %s / 5.", stars))

    def _ocd_can_request_return(self):
        """A return can be asked during the days of the settings after the last delivery."""
        self.ensure_one()
        days = self.company_id.ocd_return_days
        delivered = self.ocd_parcel_ids.filtered(lambda p: p.ocd_stage == "delivered" and p.ocd_delivered_at)
        if not days or not delivered or self.ocd_return_requested_at:
            return False
        last = max(delivered.mapped("ocd_delivered_at"))
        return fields.Datetime.now() <= last + timedelta(days=days)

    def _ocd_request_return(self):
        """The customer asks for a return: the team gets an activity on the order and organises
        the pick-up (a courier, a code), as for a delivery."""
        self.ensure_one()
        if not self._ocd_can_request_return():
            raise UserError(self.env._("A return can no longer be asked for this order."))
        order = self.sudo()
        order.ocd_return_requested_at = fields.Datetime.now()
        body = self.env._("The customer asks for a return of the order %s.", self.name)
        order.message_post(body=body)
        user = self.company_id.ocd_live_responsible_id or self.env.ref("base.user_admin", raise_if_not_found=False)
        order.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=self.env._("Return asked by the customer"),
            note=body,
            user_id=user.id if user else self.env.uid,
        )
        channel = self.company_id.ocd_deliveries_channel_id
        if channel:
            channel.sudo().message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_comment")
        return True

