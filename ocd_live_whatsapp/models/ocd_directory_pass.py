from odoo import models


class OcdDirectoryPass(models.Model):
    _inherit = "ocd.directory.pass"

    def _ocd_send_reminder(self):
        """Override of `ocd_live` to remind the end of the pass on WhatsApp."""
        sent = self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_pass_ending", self)
        if not sent:
            super()._ocd_send_reminder()
