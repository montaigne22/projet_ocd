from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    district_id = fields.Many2one(
        comodel_name="res.city.district",
        string="District",
        domain="[('city_id', '=?', city_id)]",
        index="btree_not_null",
    )
    district_name = fields.Char(related="district_id.name", string="District Name")
    delivery_landmark = fields.Char(
        string="Delivery Landmark",
        help="A well-known place near the address, used by couriers to find it "
        "(e.g. opposite the pharmacy, behind the market).",
    )

    # === ADDRESS HELPERS === #

    @api.model
    def _address_fields(self):
        """Override of `base` to sync the district and the landmark like the other address
        fields."""
        return super()._address_fields() + ["district_id", "delivery_landmark"]

    @api.model
    def _formatting_address_fields(self):
        """Override of `base` to format addresses with the district name, not its record."""
        fields_list = [f for f in super()._formatting_address_fields() if f != "district_id"]
        return fields_list + ["district_name"]

    def _get_frontend_writable_fields(self):
        """Override of `portal` to let customers set their district and landmark."""
        return super()._get_frontend_writable_fields() | {"district_id", "delivery_landmark"}

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        """Override of `portal` to adapt the mandatory fields to Cameroonian addresses.

        Streets often have no name in Cameroon: couriers rely on the district and on a
        landmark instead. The district is only required when the chosen city has districts.
        """
        field_names = super()._get_mandatory_address_fields(country_sudo, **kwargs)
        if country_sudo.code != "CM":
            return field_names
        field_names.discard("street")
        field_names.add("delivery_landmark")
        city_id = kwargs.get("city_id")
        if city_id and str(city_id).isdigit():
            city = self.env["res.city"].sudo().browse(int(city_id)).exists()
            if city and city.district_ids:
                field_names.add("district_id")
        return field_names

    # === ONCHANGE / CRUD === #

    @api.onchange("city_id")
    def _onchange_city_id_district(self):
        if self.district_id and self.district_id.city_id != self.city_id:
            self.district_id = False

    @api.onchange("district_id")
    def _onchange_district_id(self):
        if self.district_id and self.district_id.city_id != self.city_id:
            self.city_id = self.district_id.city_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._complete_address_from_district(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._complete_address_from_district(vals)
        return super().write(vals)

    @api.model
    def _complete_address_from_district(self, vals):
        """Fill the city and region from the district or city, as the frontend form only posts
        the most precise level the customer chose."""
        if vals.get("district_id"):
            district = self.env["res.city.district"].sudo().browse(vals["district_id"])
            vals.setdefault("city_id", district.city_id.id)
        if vals.get("city_id"):
            city = self.env["res.city"].sudo().browse(vals["city_id"])
            if not vals.get("city"):
                vals["city"] = city.name
            if not vals.get("state_id") and city.state_id:
                vals["state_id"] = city.state_id.id
