from odoo import models


class OcdDirectoryListing(models.Model):
    _inherit = "ocd.directory.listing"

    def _ocd_notify_vendor(self, event):
        """Override of `ocd_live` to tell the vendor on WhatsApp."""
        super()._ocd_notify_vendor(event)
        xmlid = (
            "ocd_live_whatsapp.template_link_online"
            if event == "published"
            else "ocd_live_whatsapp.template_link_refused"
        )
        self.env["res.partner"]._ocd_whatsapp_send(xmlid, self)
