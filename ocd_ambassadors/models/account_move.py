from odoo import fields, models

KINDS = [
    ("earning", "Gain of an ambassador"),
    ("taken_back", "Gain taken back"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    ocd_ambassador_kind = fields.Selection(
        selection=KINDS, string="Ambassador", copy=False, readonly=True, index="btree_not_null",
    )
    ocd_ambassador_gain_id = fields.Many2one(
        comodel_name="ocd.ambassador.gain", string="Gain Of An Ambassador", copy=False, readonly=True,
        index="btree_not_null", ondelete="restrict",
    )

    _unique_ocd_ambassador_move = models.UniqueIndex(
        "(ocd_ambassador_gain_id, ocd_ambassador_kind) WHERE ocd_ambassador_gain_id IS NOT NULL",
        "A gain is paid or taken back once.",
    )
