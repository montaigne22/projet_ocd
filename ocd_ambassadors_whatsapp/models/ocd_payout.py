from odoo import models


class OcdPayout(models.Model):
    _inherit = "ocd.payout"

    def _ocd_ambassador_paid(self):
        """Override of `ocd_ambassadors`: the ambassador is told their payout left."""
        super()._ocd_ambassador_paid()
        self.env["res.partner"]._ocd_whatsapp_send("ocd_ambassadors_whatsapp.template_ambassador_paid", self)

    def _ocd_ambassador_amount_text(self):
        self.ensure_one()
        return self.env["ocd.live.dashboard"]._ocd_money(self.amount, self.currency_id)
