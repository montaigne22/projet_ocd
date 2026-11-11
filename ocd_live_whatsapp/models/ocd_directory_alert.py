from odoo import models


class OcdDirectoryAlert(models.Model):
    _inherit = "ocd.directory.alert"

    def _ocd_send_window_open(self):
        """Override of `ocd_live`: the contact asked to be told on WhatsApp when the checking
        window of the directory opens ("Tell me at 18:00")."""
        self.ensure_one()
        sent = self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_window_open", self, requested=True)
        return sent or super()._ocd_send_window_open()
