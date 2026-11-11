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
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Colour Shown",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="The colour or the size shown during the live: the replay opens the product on it.",
    )
    offset_seconds = fields.Integer(string="Second Of The Video", required=True, default=0)
    offset_label = fields.Char(string="Minute", compute="_compute_offset_label")

    @api.depends("offset_seconds")
    def _compute_offset_label(self):
        for moment in self:
            moment.offset_label = self._ocd_time_label(moment.offset_seconds)

    @api.model
    def _ocd_time_label(self, seconds):
        """A moment of the video: "04:00", "1:05:30" after one hour."""
        hours, rest = divmod(max(int(seconds or 0), 0), 3600)
        minutes, seconds = divmod(rest, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    def _ocd_variant_query(self):
        """ "?v=12,15": the colour and the size shown, for the link of the product."""
        self.ensure_one()
        values = self.product_id.product_template_attribute_value_ids.ids if self.product_id else []
        return "?v=" + ",".join(str(value) for value in sorted(values)) if values else ""
