from odoo import api, models


class OcdLiveRegie(models.AbstractModel):
    """The control room at the end of the live: « Send the video of the live » beside « Publish the
    replay », with where its clips stand."""

    _inherit = "ocd.live.regie"

    @api.model
    def get_regie_data(self, booking_id=False):
        data = super().get_regie_data(booking_id)
        booking = self.env["ocd.live.booking"].browse(data.get("booking_id") or [])
        if not booking or booking.partner_id.ocd_clips_off or booking.state not in ("confirmed", "done"):
            data["clips"] = False
            return data
        data["clips"] = {
            "line": booking._ocd_clips_line(),
            "action": booking.action_ocd_open_clips(),
            "sent": bool(booking.ocd_recording_ids.filtered(lambda part: part.state != "deleted")),
        }
        return data
