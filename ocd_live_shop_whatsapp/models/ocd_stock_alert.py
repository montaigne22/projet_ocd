from odoo import models

PRODUCT_BACK = "ocd_live_shop_whatsapp.template_product_back"
PRODUCT_BACK_IN_STORE = "ocd_live_shop_whatsapp.template_product_back_in_store"


class OcdStockAlert(models.Model):
    _inherit = "ocd.stock.alert"

    def _ocd_send_product_back(self):
        """Override of `ocd_live_shop`: tell the customer on WhatsApp that the product is back
        (they asked for it on the page of the product: "Tell me when it is back"), and in which
        stores of the vendor (chantier 18) once Meta approved that message; until then, the
        message without the stores."""
        super()._ocd_send_product_back()
        Partner = self.env["res.partner"]
        xmlid = PRODUCT_BACK
        if self._ocd_back_in_stores() and Partner._ocd_template_approved(PRODUCT_BACK_IN_STORE):
            xmlid = PRODUCT_BACK_IN_STORE
        return Partner._ocd_whatsapp_send(xmlid, self, requested=True)
