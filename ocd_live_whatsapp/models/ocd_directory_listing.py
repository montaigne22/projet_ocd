from odoo import models

EVENT_TEMPLATES = {
    "queued": "ocd_live_whatsapp.template_link_received",
    "published": "ocd_live_whatsapp.template_link_online",
    "refused": "ocd_live_whatsapp.template_link_refused",
}


class OcdDirectoryListing(models.Model):
    _inherit = "ocd.directory.listing"

    def _ocd_notify_vendor(self, event):
        """Override of `ocd_live` to tell the vendor on WhatsApp: link received (and when it is
        checked), online, or refused with the reason."""
        super()._ocd_notify_vendor(event)
        if event in EVENT_TEMPLATES:
            self.env["res.partner"]._ocd_whatsapp_send(EVENT_TEMPLATES[event], self)
