from odoo import models

# The answer of the vendor to a piece held, told to the customer (chantier 20)
CUSTOMER_TEMPLATES = {
    "accepted": "ocd_live_shop_whatsapp.template_hold_accepted",
    "refused": "ocd_live_shop_whatsapp.template_hold_refused",
}


class OcdProductHold(models.Model):
    """Hold a piece to try it in a store: the vendor is told on WhatsApp, then the customer gets
    the answer (they asked for it: sent even without the consent to the notifications)."""

    _inherit = "ocd.product.hold"

    def _ocd_notify_vendor(self):
        super()._ocd_notify_vendor()
        for hold in self:
            self.env["res.partner"]._ocd_whatsapp_send("ocd_live_shop_whatsapp.template_hold_requested", hold)

    def _ocd_notify_customer(self, event):
        super()._ocd_notify_customer(event)
        if event in CUSTOMER_TEMPLATES:
            for hold in self:
                self.env["res.partner"]._ocd_whatsapp_send(CUSTOMER_TEMPLATES[event], hold, requested=True)
