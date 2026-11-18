from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    ocd_express_debt_partner_id = fields.Many2one(
        comodel_name="res.partner", string="OCD Express: Paid By The Sender", copy=False, readonly=True,
        index="btree_not_null",
    )
    ocd_express_debt_move_id = fields.Many2one(comodel_name="account.move", copy=False, readonly=True)

    def _post_process(self):
        """Override of `payment`: what a sender of OCD Express owed is paid once the provider
        confirms the payment."""
        super()._post_process()
        for transaction in self.filtered(
            lambda t: t.ocd_express_debt_partner_id and t.state == "done" and not t.ocd_express_debt_move_id
        ):
            move = transaction.ocd_express_debt_partner_id.sudo().with_user(transaction.env.ref("base.user_root")) \
                .action_ocd_express_debt_paid(transaction.amount, transaction.provider_reference or transaction.reference)
            transaction.ocd_express_debt_move_id = move
