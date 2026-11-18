from odoo import fields, models
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_cinetpay import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("cinetpay", "CinetPay")], ondelete={"cinetpay": "set default"})
    cinetpay_site_id = fields.Char(
        string="CinetPay Site ID",
        help="The identifier of the site, in « Integration » of the dashboard of CinetPay.",
        required_if_provider="cinetpay",
        copy=False,
    )
    cinetpay_api_key = fields.Char(
        string="CinetPay API Key",
        required_if_provider="cinetpay",
        copy=False,
        groups="base.group_system",
    )
    cinetpay_secret_key = fields.Char(
        string="CinetPay Secret Key",
        help="The secret key of the site (signature of the notifications); the state of a payment is read "
        "from CinetPay anyway.",
        copy=False,
        groups="base.group_system",
    )

    # === BUSINESS METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "cinetpay":
            supported_currencies = supported_currencies.filtered(lambda c: c.name in const.SUPPORTED_CURRENCIES)
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "cinetpay":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _cinetpay_credentials(self):
        """The keys of the requests: the API key and the site."""
        self.ensure_one()
        return {"apikey": self.sudo().cinetpay_api_key or "", "site_id": self.cinetpay_site_id or ""}

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "cinetpay":
            return super()._build_request_url(endpoint, **kwargs)
        return url_join(const.API_URL, endpoint)

    def _build_request_headers(self, method, endpoint, payload, **kwargs):
        """Override of `payment`: JSON, the keys travel in the body."""
        if self.code != "cinetpay":
            return super()._build_request_headers(method, endpoint, payload, **kwargs)
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "cinetpay":
            return super()._parse_response_error(response)
        try:
            content = response.json()
        except ValueError:
            return response.text
        if isinstance(content, dict):
            return content.get("description") or content.get("message") or str(content)
        return str(content)

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != "cinetpay":
            return super()._parse_response_content(response, **kwargs)
        return response.json()
