from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_clip_max_seconds = fields.Integer(
        string="Clip: Length At Most", default=30,
        help="Seconds at most of a clip of a product (a WhatsApp status takes 60 seconds, a clip of 30 is shared most).",
    )
    ocd_clip_before_seconds = fields.Integer(
        string="Clip: Before The Moment", default=3,
        help="Seconds kept before the moment noted by the control room: the time to present the product.",
    )
    ocd_clip_min_seconds = fields.Integer(
        string="Clip: Length At Least", default=12,
        help="Shorter (the next product shown too soon), no clip rather than a confused one.",
    )
    ocd_clip_keep_days = fields.Integer(
        string="Video Of A Live: Kept", default=7,
        help="Days the video of a live stays on the server to make its clips again; the clips stay.",
    )
    ocd_clip_keep_removed_months = fields.Integer(
        string="Clip Of A Product Taken Off Sale: Kept", default=3,
        help="Months after which the clips of a product no longer on sale are deleted.",
    )
    ocd_clip_quality = fields.Selection(
        selection=[("720", "720 × 1280"), ("1080", "1080 × 1920")],
        string="Clip: Quality", default="720", required=True,
        help="720 × 1280: about 6 MB for 30 seconds, quick on mobile data. 1080 × 1920: sharper, twice as heavy.",
    )
    ocd_clip_link_base = fields.Char(
        string="Address Of The Short Links",
        help="The address written in the clips before /p/K7Q2AB (e.g. https://ocdlive.com). Empty: the address of the site.",
    )
    ocd_clip_whatsapp_per_day = fields.Integer(
        string="Clips Sent On WhatsApp Per Day", default=10,
        help="« Send me the clip on WhatsApp »: per vendor and per day, at most.",
    )

    @api.constrains("ocd_clip_max_seconds", "ocd_clip_min_seconds", "ocd_clip_before_seconds")
    def _check_ocd_clip_seconds(self):
        for company in self:
            if not 5 <= company.ocd_clip_min_seconds <= company.ocd_clip_max_seconds <= 60:
                raise ValidationError(self.env._("A clip lasts between 5 and 60 seconds, at least shorter than at most."))
            if not 0 <= company.ocd_clip_before_seconds <= 15:
                raise ValidationError(self.env._("A clip starts between 0 and 15 seconds before the moment."))
