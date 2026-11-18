from odoo import fields, models

# What a bill (OCD owes the sender) or a credit note (the sender owes OCD) of OCD Express is for
EXPRESS_KINDS = [
    ("collected", "Money collected for the sender"),
    ("fees", "Delivery and collecting"),
    ("return", "Return"),
    ("pickup", "Pick-up"),
    ("claim", "Problem reported by the customer"),
    ("lost", "Lost or damaged by OCD"),
    ("debt_paid", "Paid by the sender"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    ocd_express_kind = fields.Selection(
        selection=EXPRESS_KINDS, string="OCD Express", copy=False, readonly=True, index="btree_not_null",
    )
