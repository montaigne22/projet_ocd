from odoo import api, models

# The providers that take the Mobile Money by themselves (the customer confirms on the phone).
AUTOMATIC_MOBILE_MONEY = ("campay", "cinetpay", "flutterwave")


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

    @api.model
    def _find_available_providers(self, company_id, partner_id, amount, *, currency_id=None, **kwargs):
        """Override of `payment`: the Mobile Money checked by the team steps aside where a provider
        takes the Mobile Money by itself (CinetPay, Flutterwave, CamPay) for this country and this
        currency, once that provider is live. In test mode, both are offered."""
        providers = super()._find_available_providers(
            company_id, partner_id, amount, currency_id=currency_id, **kwargs
        )
        momo_team = self.env.ref("ocd_live.payment_provider_momo_team", raise_if_not_found=False)
        if momo_team and momo_team in providers:
            country = self.env["res.partner"].browse(partner_id).country_id
            currency = self.env["res.currency"].browse(currency_id)
            if any(provider._ocd_takes_mobile_money(country, currency) for provider in providers - momo_team):
                providers -= momo_team
        return providers

    def _ocd_takes_mobile_money(self, country, currency):
        """Whether this provider takes the Mobile Money by itself, for real, in this country and
        this currency."""
        self.ensure_one()
        if not self.is_live or self.code not in AUTOMATIC_MOBILE_MONEY:
            return False
        return any(
            method.active
            and method.code == "mobile_money"
            and (not country or not method.supported_country_ids or country in method.supported_country_ids)
            and (not currency or not method.supported_currency_ids or currency in method.supported_currency_ids)
            for method in self.payment_method_ids
        )
