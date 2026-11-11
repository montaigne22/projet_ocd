from odoo import models


class ResCountry(models.Model):
    _inherit = "res.country"

    def _enforce_city_choice(self):
        """Override of `portal` to let customers pick a Cameroonian city from a list."""
        if not self:
            return False
        self.ensure_one()
        if self.code == "CM":
            return self.enforce_cities and bool(
                self.env["res.city"].sudo().search_count([("country_id", "=", self.id)], limit=1)
            )
        return super()._enforce_city_choice()
