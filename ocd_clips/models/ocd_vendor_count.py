from odoo import fields, models


class OcdVendorCount(models.Model):
    """The clips in the figures of the vendor: the plays on the site (product page, replay) and the
    visits by the short link of each clip (one per phone and per day), record = the clip."""

    _inherit = "ocd.vendor.count"

    kind = fields.Selection(
        selection_add=[("clip_play", "Clip Played"), ("clip_visit", "Visit By A Clip")],
        ondelete={"clip_play": "cascade", "clip_visit": "cascade"},
    )
