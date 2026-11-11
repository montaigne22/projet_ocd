from odoo import models


class OcdLiveWaitlist(models.Model):
    _inherit = "ocd.live.waitlist"

    def _ocd_send_free_slot(self):
        """Override of `ocd_live`: the contact registered on the waiting list to be told on
        WhatsApp when an hour of the day becomes free."""
        self.ensure_one()
        sent = self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_free_slot", self, requested=True)
        return sent or super()._ocd_send_free_slot()
