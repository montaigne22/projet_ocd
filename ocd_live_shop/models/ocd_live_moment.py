from odoo import api, fields, models


class OcdLiveMoment(models.Model):
    """A product shown during a live, with the minute of the video where it appears."""

    _name = "ocd.live.moment"
    _description = "Moment Of A Live"
    _order = "booking_id, offset_seconds, id"

    booking_id = fields.Many2one(
        comodel_name="ocd.live.booking", string="Live", required=True, index=True, ondelete="cascade"
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Product", required=True, index=True, ondelete="cascade"
    )
    offset_seconds = fields.Integer(string="Second Of The Video", required=True, default=0)
    offset_label = fields.Char(string="Minute", compute="_compute_offset_label")

    @api.depends("offset_seconds")
    def _compute_offset_label(self):
        for moment in self:
            minutes, seconds = divmod(max(moment.offset_seconds, 0), 60)
            moment.offset_label = f"{minutes:02d}:{seconds:02d}"
