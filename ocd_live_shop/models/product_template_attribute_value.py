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
    # A new photo of the colour of a product on sale: checked by the team while the photo of
    # today (or none) stays (chantier 19)
    ocd_image_pending = fields.Image(
        string="New Photo Of The Colour To Check",
        max_width=1920,
        max_height=1920,
        copy=False,
    )
    ocd_image_state = fields.Selection(
        selection=[("to_check", "To check"), ("refused", "Refused")],
        string="Check Of The New Photo",
        copy=False,
    )
