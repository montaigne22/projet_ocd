from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        """Override of `delivery_cameroon` to use the same address in Togo: no street needed,
        a mandatory landmark, and the district when the city has districts."""
        field_names = super()._get_mandatory_address_fields(country_sudo, **kwargs)
        if country_sudo.code != "TG":
            return field_names
        field_names.discard("street")
        field_names.add("delivery_landmark")
        city_id = kwargs.get("city_id")
        if city_id and str(city_id).isdigit():
            city = self.env["res.city"].sudo().browse(int(city_id)).exists()
            if city and city.district_ids:
                field_names.add("district_id")
        return field_names
