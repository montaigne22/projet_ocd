import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ocd_product_kind = fields.Selection(
        selection=[("live_package", "Live package"), ("directory_pass", "Directory pass")],
        string="OCD Live Product",
        help="Live package: its lives become credits of the vendor once paid. "
        "Directory pass: gives the right to send live links to the directory.",
    )
    ocd_live_count = fields.Integer(string="Lives In The Package", default=1)
    ocd_live_hours = fields.Float(string="Hours Per Live", default=1.5)
    ocd_slot_count = fields.Integer(
        string="Slots Per Live",
        compute="_compute_ocd_slot_count",
        help="Number of consecutive slots taken by one live of this package.",
    )
    ocd_with_announce = fields.Boolean(
        string="Announce Included",
        help="The live is announced with a video on House of Challenge.",
    )
    ocd_validity_days = fields.Integer(
        string="Lives To Place Within (Days)",
        help="The credits of the package expire after this number of days. 0: no limit.",
    )
    ocd_pass_days = fields.Integer(string="Pass Duration (Days)", default=30)
    ocd_badge = fields.Char(
        string="Badge",
        help="Short text shown on the package button of the website, e.g. x1, x2, 4 h.",
    )

    @api.depends("ocd_live_hours", "company_id.ocd_slot_hours")
    @api.depends_context("company")
    def _compute_ocd_slot_count(self):
        for product in self:
            slot_hours = (product.company_id or self.env.company).ocd_slot_hours or 1.5
            product.ocd_slot_count = max(1, math.ceil(round(product.ocd_live_hours / slot_hours, 6)))

    @api.constrains("ocd_product_kind", "ocd_live_count", "ocd_live_hours", "ocd_pass_days")
    def _check_ocd_product(self):
        for product in self:
            if product.ocd_product_kind == "live_package" and (
                product.ocd_live_count < 1 or product.ocd_live_hours <= 0
            ):
                raise ValidationError(
                    self.env._("A live package must contain at least one live of a positive duration.")
                )
            if product.ocd_product_kind == "directory_pass" and product.ocd_pass_days < 1:
                raise ValidationError(self.env._("A directory pass must last at least one day."))
