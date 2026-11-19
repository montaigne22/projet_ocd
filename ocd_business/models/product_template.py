from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ocd_product_kind = fields.Selection(
        selection_add=[("business", "OCD Business")], ondelete={"business": "set null"},
    )
    ocd_business_days = fields.Integer(
        string="Days Of OCD Business", default=30,
        help="The days of the formula one piece gives, from the end of the current one.",
    )

    @api.constrains("ocd_product_kind", "ocd_business_days")
    def _check_ocd_business_days(self):
        for product in self:
            if product.ocd_product_kind == "business" and product.ocd_business_days < 1:
                raise ValidationError(self.env._("A formula of OCD Business lasts one day at least."))
