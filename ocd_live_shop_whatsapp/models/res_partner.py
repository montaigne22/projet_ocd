from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_send_delivery_link(self, url):
        """Override of `ocd_live_shop` to send the link of the delivery app on WhatsApp (asked
        by the vendor or the courier, or sent by the team when they start)."""
        return self._ocd_whatsapp_send("ocd_live_shop_whatsapp.template_delivery_link", self, requested=True)
