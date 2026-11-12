import base64
import binascii
import hashlib
import hmac
import json
import re
import time

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_campay import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("campay", "Campay")], ondelete={"campay": "set default"}
    )
    campay_app_username = fields.Char(
        string="Campay App Username",
        help="The username of the application, in the API Access Keys of the Campay dashboard.",
        required_if_provider="campay",
        copy=False,
    )
    campay_app_password = fields.Char(
        string="Campay App Password",
        required_if_provider="campay",
        copy=False,
        groups="base.group_system",
    )
    campay_webhook_key = fields.Char(
        string="Campay Webhook Key",
        help="The key Campay uses to sign the webhook calls, in the Webhook settings of the "
        "Campay dashboard.",
        required_if_provider="campay",
        copy=False,
        groups="base.group_system",
    )

    # Demo payments: every payment collects a small amount, the pages show the real ones
    campay_demo_active = fields.Boolean(
        string="Demo Payments",
        copy=False,
        help="Every payment collects the demo amount instead of the amount of the order: the pages show the "
        "real amounts and the order is paid as usual. Until the last day below, then off by itself.",
    )
    campay_demo_amount = fields.Integer(string="Demo Amount", default=25, help="In CFA francs.")
    campay_demo_end = fields.Date(string="Last Day Of The Demo Payments", copy=False)
    campay_demo_numbers = fields.Text(
        string="Demo Numbers",
        copy=False,
        help="Only the payments from these numbers collect the demo amount (separated by commas or one per "
        "line, e.g. 670000001); the others pay the real price. Empty: every payment.",
    )

    # === BUSINESS METHODS === #

    def _campay_demo_on(self):
        """Whether the demo payments are on today (they stop by themselves after the last day)."""
        self.ensure_one()
        return bool(
            self.code == "campay"
            and self.campay_demo_active
            and self.campay_demo_amount > 0
            and (not self.campay_demo_end or self.campay_demo_end >= fields.Date.context_today(self))
        )

    def _campay_demo_amount(self, phone=None):
        """The amount a payment from `phone` collects while the demo payments are on, else 0:
        every payment, or the ones of the demo numbers only when they are given."""
        self.ensure_one()
        if not self._campay_demo_on():
            return 0
        numbers = self._campay_demo_number_list()
        if numbers and self._campay_normalize_phone(phone) not in numbers:
            return 0
        return self.campay_demo_amount

    def _campay_demo_number_list(self):
        """The demo numbers, in the format of Campay (237 followed by 9 digits)."""
        self.ensure_one()
        numbers = re.split(r"[,;\n]+", self.campay_demo_numbers or "")
        return {normalized for normalized in map(self._campay_normalize_phone, numbers) if normalized}

    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        providers._campay_demo_until_tonight()
        return providers

    def write(self, vals):
        """Demo payments switched on without a last day, or with a day already past: until
        tonight (never on by oversight)."""
        if vals.get("campay_demo_active") and "campay_demo_end" not in vals:
            today = fields.Date.context_today(self)
            for provider in self.filtered(lambda p: p.campay_demo_end and p.campay_demo_end < today):
                super(PaymentProvider, provider).write({"campay_demo_end": today})
        res = super().write(vals)
        if {"campay_demo_active", "campay_demo_end"} & set(vals):
            self._campay_demo_until_tonight()
        return res

    def _campay_demo_until_tonight(self):
        today = fields.Date.context_today(self)
        for provider in self.filtered(lambda p: p.campay_demo_active and not p.campay_demo_end):
            super(PaymentProvider, provider).write({"campay_demo_end": today})

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "campay":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "campay":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _campay_verify_webhook_signature(self, signature):
        """Check that a webhook call was signed by Campay with the webhook key.

        Campay signs its webhook calls with a JWT (HS256) whose payload states the source
        (`campay`) and an expiry date.

        Note: `self.ensure_one()`

        :param str signature: The `signature` parameter of the webhook call.
        :return: Whether the signature is authentic and still valid.
        :rtype: bool
        """
        self.ensure_one()
        key = self.sudo().campay_webhook_key
        if not signature or not key:
            return False
        try:
            header_b64, payload_b64, signature_b64 = signature.split(".")
            header = json.loads(_b64url_decode(header_b64))
            payload = json.loads(_b64url_decode(payload_b64))
            received_digest = _b64url_decode(signature_b64)
        except (ValueError, TypeError, binascii.Error):
            return False
        if header.get("alg") != "HS256":
            return False
        expected_digest = hmac.new(
            key.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(received_digest, expected_digest):
            return False
        if str(payload.get("source", "")).lower() != "campay":
            return False
        expiry = payload.get("exp")
        return not (isinstance(expiry, (int, float)) and expiry < time.time())

    @staticmethod
    def _campay_normalize_phone(phone):
        """Return the phone number in the format expected by Campay (237 followed by 9 digits).

        :param str phone: The phone number typed by the customer.
        :return: The normalized number, or an empty string if it is not a Cameroonian mobile.
        :rtype: str
        """
        digits = re.sub(r"\D", "", phone or "")
        if digits.startswith("00"):
            digits = digits[2:]
        if len(digits) == 9:
            digits = const.CAMEROON_PHONE_CODE + digits
        if re.fullmatch(r"2376\d{8}", digits):
            return digits
        return ""

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "campay":
            return super()._build_request_url(endpoint, **kwargs)
        return url_join(const.API_URLS["live" if self.is_live else "test"], endpoint)

    def _build_request_headers(self, method, endpoint, payload, **kwargs):
        """Override of `payment` to authenticate the requests with a Campay access token."""
        if self.code != "campay":
            return super()._build_request_headers(method, endpoint, payload, **kwargs)
        headers = {"Content-Type": "application/json"}
        if not kwargs.get("campay_no_auth"):
            headers["Authorization"] = f"Token {self._campay_get_access_token()}"
        return headers

    def _campay_get_access_token(self):
        """Request a temporary access token from Campay with the application credentials.

        :return: The access token.
        :rtype: str
        :raise ValidationError: If Campay rejects the credentials.
        """
        self.ensure_one()
        response_content = self._send_api_request(
            "POST",
            "token/",
            json={
                "username": self.campay_app_username,
                "password": self.sudo().campay_app_password,
            },
            campay_no_auth=True,
        )
        token = response_content.get("token")
        if not token:
            raise ValidationError(self.env._("Campay did not return an access token."))
        return token

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != "campay":
            return super()._parse_response_error(response)
        content = response.json()
        if isinstance(content, dict):
            message = content.get("message") or content.get("detail")
            if not message and content.get("non_field_errors"):
                message = " ".join(content["non_field_errors"])
            return message or str(content)
        return str(content)

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != "campay":
            return super()._parse_response_content(response, **kwargs)
        return response.json()


def _b64url_decode(value):
    """Decode a base64url string without padding, as used in JWTs."""
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
