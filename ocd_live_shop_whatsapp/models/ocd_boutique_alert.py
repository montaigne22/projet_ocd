from odoo import models


class OcdBoutiqueAlert(models.Model):
    _inherit = "ocd.boutique.alert"

    def _ocd_send_live_started(self, booking):
        """Override of `ocd_live_shop`: tell the visitor on WhatsApp that the vendor is live
        (they asked for it on the boutique: "Tell me on WhatsApp")."""
        super()._ocd_send_live_started(booking)
        return self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_vendor_live", self, requested=True
        )
