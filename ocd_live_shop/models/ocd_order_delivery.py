from odoo import fields, models

from .ocd_delivery_rate import OPERATORS


class OcdOrderDelivery(models.Model):
    """The delivery of one parcel of an order (one per vendor), as the customer paid it: the
    rate, who delivers and the price. Written when the delivery of the order is priced, read
    when the parcels are created: each parcel gets its exact price, not a share of the total."""

    _name = "ocd.order.delivery"
    _description = "Delivery Of A Parcel Of An Order"
    _order = "order_id, id"

    order_id = fields.Many2one(
        comodel_name="sale.order", string="Order", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="order_id.company_id")
    currency_id = fields.Many2one(related="order_id.currency_id")
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", help="Empty: the products of OCD Live."
    )
    rate_id = fields.Many2one(comodel_name="ocd.delivery.rate", string="Rate", ondelete="set null")
    operator = fields.Selection(selection=OPERATORS, string="Who Delivers")
    origin_city_id = fields.Many2one(comodel_name="res.city", string="From")
    amount = fields.Monetary(string="Price")
    allow_cod = fields.Boolean(string="Payment At The Door")
    description = fields.Char(string="For The Customer")
