from odoo import fields, models


class OcdVendorCount(models.Model):
    """The visits by the links of an ambassador: one per phone and per day, counted on the
    ambassador (their contact), the product of the link in `res_id`."""

    _inherit = "ocd.vendor.count"

    kind = fields.Selection(
        selection_add=[("ambassador_visit", "Visit By An Ambassador")],
        ondelete={"ambassador_visit": "cascade"},
    )
