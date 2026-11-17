from odoo import models


class ProductProduct(models.Model):
    """Low stock alert (chantier 21): the vendor is told on WhatsApp how many pieces are left."""

    _inherit = "product.product"

    def _ocd_low_stock_notify(self, pieces):
        super()._ocd_low_stock_notify(pieces)
        for variant in self:
            self.env["res.partner"]._ocd_whatsapp_send(
                "ocd_live_shop_whatsapp.template_low_stock", variant, ocd_low_qty=pieces,
            )
