from odoo import fields, models


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    ocd_image = fields.Image(
        string="Photo Of The Colour",
        max_width=1920,
        max_height=1920,
        help="Photo of the product in this colour: the product page shows it as soon as the colour "
        "is chosen. Without it, the main photo of the product.",
    )
