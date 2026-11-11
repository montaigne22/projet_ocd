from odoo import api, fields, models


class ResCityDistrict(models.Model):
    _name = "res.city.district"
    _description = "District"
    _order = "city_id, sequence, name"
    _rec_names_search = ["name", "city_id.name"]

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    city_id = fields.Many2one(
        comodel_name="res.city", string="City", required=True, index=True, ondelete="cascade"
    )
    state_id = fields.Many2one(related="city_id.state_id", store=True)
    country_id = fields.Many2one(related="city_id.country_id", store=True)

    _name_city_uniq = models.Constraint(
        "unique(name, city_id)", "This district already exists in this city."
    )

    @api.depends_context("formatted_display_name")
    @api.depends("city_id")
    def _compute_display_name(self):
        for district in self:
            if self.env.context.get("formatted_display_name"):
                district.display_name = f"{district.name} \v--{district.city_id.name}--"
            else:
                district.display_name = district.name
