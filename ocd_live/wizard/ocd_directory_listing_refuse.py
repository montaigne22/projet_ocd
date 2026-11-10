from odoo import fields, models


class OcdDirectoryListingRefuse(models.TransientModel):
    _name = "ocd.directory.listing.refuse"
    _description = "Refuse Directory Links"

    listing_ids = fields.Many2many(comodel_name="ocd.directory.listing", string="Links", required=True)
    reason_id = fields.Many2one(
        comodel_name="ocd.listing.refuse.reason",
        string="Reason",
        required=True,
        domain=[("applies_to", "=", "link")],
    )
    note = fields.Text(string="Note To The Vendor")

    def action_refuse(self):
        self.ensure_one()
        self.listing_ids._ocd_refuse(self.reason_id, self.note)
        return {"type": "ir.actions.act_window_close"}
