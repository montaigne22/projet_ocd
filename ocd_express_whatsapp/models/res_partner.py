from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_express_notify_momo_changed(self, old_number):
        """Override of `ocd_express`: the number of the account of the sender is told (not them?
        they report it before the payout leaves)."""
        super()._ocd_express_notify_momo_changed(old_number)
        self._ocd_whatsapp_send("ocd_express_whatsapp.template_express_number", self, requested=True)
