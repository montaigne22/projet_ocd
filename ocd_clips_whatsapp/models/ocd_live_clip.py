from odoo import models

TEMPLATE = "ocd_clips_whatsapp.template_clip_video"


class OcdLiveClip(models.Model):
    _inherit = "ocd.live.clip"

    def _ocd_whatsapp_ready(self):
        """« Send me the clip on WhatsApp » when its message can leave (approved by Meta, not paused)
        and the vendor has a number."""
        self.ensure_one()
        vendor = self.vendor_id.sudo()
        return bool(vendor.phone) and self.env["res.partner"]._ocd_template_usable(TEMPLATE)

    def _ocd_whatsapp_clip(self):
        """The clip itself in the conversation of OCD Live (ocd_clip_video, the video in its
        header): asked by the vendor, it leaves even without the consent to the notifications."""
        self.ensure_one()
        return self.env["res.partner"]._ocd_whatsapp_send(TEMPLATE, self.sudo(), requested=True)
