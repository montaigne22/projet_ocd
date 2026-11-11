from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("ocd", "OCD Live: one price per parcel")],
        ondelete={"ocd": "set default"},
    )

    @api.depends("delivery_type")
    def _compute_supports_cash_on_delivery(self):
        """Override of `delivery`: the method of OCD Live offers the payment at the door when
        every parcel of the order allows it."""
        super()._compute_supports_cash_on_delivery()
        for carrier in self.filtered(lambda c: c.delivery_type == "ocd"):
            carrier.supports_cash_on_delivery = True

    @api.constrains("delivery_type", "margin", "fixed_margin", "free_over")
    def _check_ocd_no_margin(self):
        for carrier in self.filtered(lambda c: c.delivery_type == "ocd"):
            if carrier.margin or carrier.fixed_margin or carrier.free_over:
                raise ValidationError(self.env._(
                    "The delivery of OCD Live has no margin and no free delivery of its own: set "
                    "them on the rates (free above an amount)."
                ))

    def ocd_rate_shipment(self, order):
        """Price of the delivery of the order: the sum of its parcels (one per vendor), each at
        the rate of its vendor for the address. Fails, with the reason for the customer, when a
        parcel cannot reach the address: the order is never paid for a parcel nobody delivers."""
        self.ensure_one()
        quotes = order._ocd_delivery_quotes()
        errors = [quote["error"] for quote in quotes if quote["error"]]
        if errors:
            return {"success": False, "price": 0.0, "error_message": "\n".join(errors), "warning_message": False}
        return {
            "success": True,
            "price": sum(quote["price"] for quote in quotes),
            "error_message": False,
            "warning_message": False,
        }

    def ocd_send_shipping(self, pickings):
        """The parcels are delivered by the vendors, the OCD couriers or the agencies: nothing
        is sent to a shipping company."""
        return [{"exact_price": picking.ocd_fee_amount, "tracking_number": False} for picking in pickings]

    def ocd_get_tracking_link(self, picking):
        return False

    def ocd_cancel_shipment(self, pickings):
        return True

    def _is_available_for_order(self, order):
        """Override of `delivery`: the method of OCD Live is offered only when every parcel of
        the order can reach the address."""
        if self.delivery_type == "ocd":
            return self._match(order.partner_shipping_id, order) and self.ocd_rate_shipment(order)["success"]
        return super()._is_available_for_order(order)
