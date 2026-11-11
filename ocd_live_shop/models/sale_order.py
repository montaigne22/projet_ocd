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
    ocd_delivery_line_ids = fields.One2many(
        comodel_name="ocd.order.delivery",
        inverse_name="order_id",
        string="Delivery Of Each Parcel",
        readonly=True,
        copy=False,
    )
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

    # === DELIVERY: ONE PRICE PER PARCEL === #

    def _ocd_delivery_groups(self):
        """The products to deliver, by parcel: {vendor (empty for OCD Live): amount}."""
        self.ensure_one()
        groups = {}
        for line in self.order_line:
            if (
                line.is_delivery
                or line.display_type
                or line.product_id.type != "consu"
                or line.product_uom_qty <= 0
            ):
                continue
            vendor = line.ocd_vendor_id
            groups[vendor] = groups.get(vendor, 0.0) + line.price_total
        return groups

    def _ocd_delivery_quotes(self, partner=None):
        """The delivery of each parcel of the order to `partner` (the delivery address by
        default), as `ocd.delivery.rate._ocd_quote` gives it."""
        self.ensure_one()
        partner = partner if partner is not None else self.partner_shipping_id
        Rate = self.env["ocd.delivery.rate"]
        rates = Rate._ocd_rates(self.company_id)
        date = fields.Date.context_today(self)
        return [
            Rate._ocd_quote(vendor, partner, amount, self.currency_id, self.company_id, date=date, rates=rates)
            for vendor, amount in self._ocd_delivery_groups().items()
        ]

    def _ocd_store_delivery_quotes(self):
        """Keep the delivery of each parcel as it is priced now: the parcels take their exact
        price from it when the order is confirmed."""
        for order in self:
            order.sudo().ocd_delivery_line_ids.unlink()
            if order.carrier_id.delivery_type != "ocd" or not order.order_line.filtered("is_delivery"):
                continue
            quotes = order._ocd_delivery_quotes()
            if any(quote["error"] for quote in quotes):
                continue
            self.env["ocd.order.delivery"].sudo().create([{
                "order_id": order.id,
                "vendor_id": quote["vendor"].id or False,
                "rate_id": quote["rate"].id,
                "operator": quote["operator"],
                "origin_city_id": quote["origin"].id or False,
                "amount": quote["price"],
                "allow_cod": quote["allow_cod"],
                "description": quote["description"] or False,
            } for quote in quotes])

    def set_delivery_line(self, carrier, amount):
        """Override of `delivery`: keep the delivery of each parcel with the price of the order."""
        result = super().set_delivery_line(carrier, amount)
        self._ocd_store_delivery_quotes()
        return result

    def _remove_delivery_line(self):
        result = super()._remove_delivery_line()
        self.sudo().ocd_delivery_line_ids.unlink()
        return result

    def _verify_cart_after_update(self):
        """Override of `website_sale`: the price of the delivery follows the cart, and so does
        the delivery of each parcel."""
        result = super()._verify_cart_after_update()
        if self.carrier_id.delivery_type == "ocd":
            self._ocd_store_delivery_quotes()
        return result

    def _get_delivery_methods(self):
        """Override of `website_sale`: once the delivery of OCD Live is published, it is the only
        one offered (when every parcel can reach the address); another published method would
        price the parcels without their vendors."""
        methods = super()._get_delivery_methods()
        carrier_ocd = self.env.ref("ocd_live_shop.carrier_ocd", raise_if_not_found=False)
        if carrier_ocd and carrier_ocd.sudo().is_published and carrier_ocd.sudo().active:
            return methods.filtered(lambda method: method == carrier_ocd)
        return methods

    def _ocd_cod_allowed(self):
        """Whether the customer may pay at the door: every parcel must allow it."""
        self.ensure_one()
        if self.carrier_id.delivery_type != "ocd":
            return True
        lines = self.ocd_delivery_line_ids
        if lines:
            return all(lines.mapped("allow_cod"))
        quotes = self._ocd_delivery_quotes()
        return bool(quotes) and all(quote["allow_cod"] and not quote["error"] for quote in quotes)

    def _ocd_parcel_delivery(self, vendor):
        """The delivery kept for the parcel of `vendor`, and the share of what the customer paid
        for the delivery that goes to it: its price, scaled when the paid total differs (a
        delivery changed by hand in the back office)."""
        self.ensure_one()
        lines = self.ocd_delivery_line_ids
        line = lines.filtered(lambda l: l.vendor_id == vendor)[:1]
        if not line:
            return line, None
        total = sum(lines.mapped("amount"))
        paid = self._ocd_delivery_fee()
        amount = line.amount
        if total and self.currency_id.compare_amounts(total, paid) != 0:
            amount = amount * paid / total
        return line, self.currency_id.round(amount)

