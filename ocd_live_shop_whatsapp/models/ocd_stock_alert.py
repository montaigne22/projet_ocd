from odoo import models


class OcdStockAlert(models.Model):
    _inherit = "ocd.stock.alert"

    def _ocd_send_product_back(self):
        """Override of `ocd_live_shop`: tell the customer on WhatsApp that the product is back
        (they asked for it on the page of the product: "Tell me when it is back")."""
        super()._ocd_send_product_back()
        return self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_product_back", self, requested=True
        )
