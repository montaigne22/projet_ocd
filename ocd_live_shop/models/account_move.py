from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ocd_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="OCD Parcel",
        copy=False,
        index="btree_not_null",
        readonly=True,
    )
    ocd_payout_id = fields.Many2one(
        comodel_name="ocd.payout",
        string="Payout",
        copy=False,
        index="btree_not_null",
        readonly=True,
    )
