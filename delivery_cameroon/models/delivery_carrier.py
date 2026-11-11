from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    city_ids = fields.Many2many(
        comodel_name="res.city",
        relation="delivery_carrier_res_city_rel",
        string="Cities",
        help="Only offer this delivery method for addresses in these cities.",
    )
    district_ids = fields.Many2many(
        comodel_name="res.city.district",
        relation="delivery_carrier_res_city_district_rel",
        string="Districts",
        help="Only offer this delivery method for addresses in these districts.",
    )
    excluded_city_ids = fields.Many2many(
        comodel_name="res.city",
        relation="delivery_carrier_excluded_res_city_rel",
        string="Excluded Cities",
        help="Never offer this delivery method for addresses in these cities.",
    )
    excluded_country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="delivery_carrier_excluded_res_country_rel",
        string="Excluded Countries",
        help="Never offer this delivery method for addresses in these countries.",
    )

    def _match_address(self, partner):
        """Override of `delivery` to restrict delivery methods by city and district."""
        if not super()._match_address(partner):
            return False
        if self.excluded_country_ids and partner.country_id in self.excluded_country_ids:
            return False
        if self.city_ids and partner.city_id not in self.city_ids:
            return False
        if self.excluded_city_ids and partner.city_id in self.excluded_city_ids:
            return False
        if self.district_ids and partner.district_id not in self.district_ids:
            return False
        return True
