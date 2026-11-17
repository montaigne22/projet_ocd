from odoo import fields, models


class ProductImage(models.Model):
    _inherit = "product.image"

    ocd_review_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Approved"), ("refused", "Refused")],
        string="Review",
        default="approved",
        required=True,
        index=True,
        copy=False,
        help="A photo the vendor adds to a product on sale is checked by the team before it shows "
        "(2.6 of the plan of « My products »).",
    )
