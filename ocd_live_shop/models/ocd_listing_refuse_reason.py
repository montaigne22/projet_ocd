from odoo import fields, models


class OcdListingRefuseReason(models.Model):
    _inherit = "ocd.listing.refuse.reason"

    applies_to = fields.Selection(selection_add=[("store", "Stores")], ondelete={"store": "cascade"})
