from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_clips_off = fields.Boolean(
        string="No Clips", copy=False,
        help="The vendor refuses the clips: none is made of their lives, theirs are no longer shown on the site.",
    )
    ocd_clip_ids = fields.One2many(comodel_name="ocd.live.clip", inverse_name="vendor_id", string="Clips")
    ocd_clip_count = fields.Integer(string="Clips Made", compute="_compute_ocd_clip_count")
    # « Send me the clip on WhatsApp »: the clips sent today (a few a day at most, setting)
    ocd_clips_sent_day = fields.Date(string="Day Of The Clips Sent On WhatsApp", copy=False, readonly=True)
    ocd_clips_sent_count = fields.Integer(string="Clips Sent On WhatsApp That Day", copy=False, readonly=True)

    def _compute_ocd_clip_count(self):
        groups = self.env["ocd.live.clip"].sudo()._read_group(
            [("vendor_id", "in", self.ids), ("state", "=", "ready")], ["vendor_id"], ["__count"],
        )
        counts = {vendor.id: count for vendor, count in groups}
        for partner in self:
            partner.ocd_clip_count = counts.get(partner.id, 0)

    def action_ocd_view_clips(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ocd_clips.ocd_live_clip_action")
        action["domain"] = [("vendor_id", "=", self.id)]
        action["context"] = {}
        return action

    def _ocd_card_video_from_clip(self, clip):
        """« Video of my card in the feed »: the clip becomes the short video of the card (already
        vertical, 30 seconds at most, readable by every phone), with its image."""
        self.ensure_one()
        clip = clip.sudo()
        if clip.vendor_id != self or clip.state != "ready" or not clip.video:
            raise UserError(self.env._("This clip is not ready."))
        self.sudo().with_context(ocd_card_video_ready=True).write({
            "ocd_card_video": BinaryBytes(clip.video.content, filename=f"{clip.code}.mp4"),
            "ocd_card_video_name": f"{clip.code}.mp4",
            "ocd_card_video_poster": BinaryBytes(clip.poster.content) if clip.poster else False,
            "ocd_card_video_sound": True,
            "ocd_card_video_upload": False,
            "ocd_card_video_pending": False,
            "ocd_card_video_error": False,
            "ocd_card_media": "video",
        })
        return True
