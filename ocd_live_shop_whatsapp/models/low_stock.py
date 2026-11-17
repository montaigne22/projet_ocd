from odoo import models


class ProductProduct(models.Model):
    """Low stock alert (chantier 21): the vendor is told on WhatsApp how many pieces of a colour
    and a size are left, with the template of the plan (ocd_stock_bas, on the product)."""

    _inherit = "product.product"

    def _ocd_low_stock_notify(self, pieces):
        super()._ocd_low_stock_notify(pieces)
        for variant in self:
            self.env["res.partner"]._ocd_whatsapp_send(
                "ocd_live_shop_whatsapp.template_stock_low", variant.product_tmpl_id,
                ocd_low_qty=pieces, ocd_low_name=variant.display_name,
            )
