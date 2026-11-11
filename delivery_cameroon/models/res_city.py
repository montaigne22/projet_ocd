from odoo import fields, models


class ResCity(models.Model):
    _inherit = "res.city"

    district_ids = fields.One2many(
        comodel_name="res.city.district", inverse_name="city_id", string="Districts"
    )
    district_count = fields.Integer(compute="_compute_district_count")

    def _compute_district_count(self):
        counts = dict(
            self.env["res.city.district"]._read_group(
                [("city_id", "in", self.ids)], ["city_id"], ["__count"]
            )
        )
        for city in self:
            city.district_count = counts.get(city, 0)

    def _get_districts_data(self):
        """Return the districts of the city for the address forms."""
        self.ensure_one()
        return self.env["res.city.district"].sudo().search_read(
            [("city_id", "=", self.id)], ["id", "name"]
        )
