from odoo import models


class ResCountry(models.Model):
    _inherit = "res.country"

    def _enforce_city_choice(self):
        """Override of `delivery_cameroon` to let the customers pick a city of Togo from a
        list, as in Cameroon."""
        if self and self.ensure_one() and self.code == "TG":
            return self.enforce_cities and bool(
                self.env["res.city"].sudo().search_count([("country_id", "=", self.id)], limit=1)
            )
        return super()._enforce_city_choice()
