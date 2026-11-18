from odoo import models


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    def _ocd_tell_clips_ready(self, clips):
        """Override of `ocd_clips`: « your clips are ready » (ocd_clips_prets) to the vendor, once
        per live; never after STOP."""
        super()._ocd_tell_clips_ready(clips)
        for booking in self.sudo().filtered(lambda booking: not booking.partner_id.whatsapp_opt_out):
            self.env["res.partner"]._ocd_whatsapp_send("ocd_clips_whatsapp.template_clips_ready", booking)

    def _ocd_clips_ready_count(self):
        """The clips of the live ready to share (for the message)."""
        self.ensure_one()
        return len(self.ocd_clip_ids.filtered(lambda clip: clip.state == "ready" and not clip.hidden))

    def _ocd_clips_path(self):
        """The button « See my clips »: the personal link opens « My clips » of this live."""
        self.ensure_one()
        return f"ocd/espace/{self.partner_id._ocd_get_space_token()}/clips?live={self.id}"
