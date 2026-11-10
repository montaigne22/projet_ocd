from odoo import fields, models


class OcdLiveCategory(models.Model):
    _name = "ocd.live.category"
    _description = "Live Category"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer()
    vendor_count = fields.Integer(compute="_compute_vendor_count")

    def _compute_vendor_count(self):
        counts = {
            category.id: count
            for category, count in self.env["res.partner"]._read_group(
                [("ocd_category_id", "in", self.ids), ("ocd_is_vendor", "=", True)],
                ["ocd_category_id"],
                ["__count"],
            )
        }
        for category in self:
            category.vendor_count = counts.get(category.id, 0)
