from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

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
