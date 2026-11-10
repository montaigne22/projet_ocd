from odoo import fields, models


class OcdListingRefuseReason(models.Model):
    _name = "ocd.listing.refuse.reason"
    _description = "Directory Link Refusal Reason"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    message = fields.Text(
        translate=True,
        help="Sentence sent to the vendor, to explain what to do.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
