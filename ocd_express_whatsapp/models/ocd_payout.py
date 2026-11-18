from odoo import models


class OcdPayout(models.Model):
    _inherit = "ocd.payout"

    def _ocd_express_notify_paid(self):
        """Override of `ocd_express`: the sender is told their money left."""
        super()._ocd_express_notify_paid()
        self.env["res.partner"]._ocd_whatsapp_send("ocd_express_whatsapp.template_express_paid", self)

    def _ocd_amount_text(self):
        self.ensure_one()
        return self.env["ocd.express.pickup"]._ocd_money(self.amount, self.currency_id)
