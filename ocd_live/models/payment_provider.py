from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    def _get_default_payment_method_codes(self):
        """Override of `payment`: the Mobile Money checked by the team offers its own method,
        activated with the provider."""
        codes = super()._get_default_payment_method_codes()
        momo_team = self.env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
        if momo_team and self == momo_team:
            codes = set(codes) | {"mobile_money"}
        return codes
