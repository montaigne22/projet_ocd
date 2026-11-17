from odoo import models


class OcdBoutiqueAlert(models.Model):
    _inherit = "ocd.boutique.alert"

    def _ocd_send_vendor_back(self):
        """Override of `ocd_live_shop`: tell the customer on WhatsApp that the vendor is back
        from holiday (they asked for it: "Tell me when they are back")."""
        super()._ocd_send_vendor_back()
        return self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_vendor_back", self, requested=True
        )
