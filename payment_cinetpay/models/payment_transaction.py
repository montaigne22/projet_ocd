import math
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_cinetpay import const
from odoo.addons.payment_cinetpay.controllers.main import CinetpayController

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    cinetpay_transaction_id = fields.Char(
        string="CinetPay Transaction", readonly=True, copy=False, index="btree_not_null",
        help="The identifier given to CinetPay: the reference with letters, numbers and dashes only.",
    )
    cinetpay_requested_amount = fields.Float(
        string="Amount Asked To CinetPay", readonly=True, copy=False,
        help="The amount of the transaction, rounded up to a multiple of 5 in CFA francs (rule of CinetPay).",
    )

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _cinetpay_id(self):
        """The identifier of the transaction at CinetPay (it refuses #, /, $, _, & and the spaces of some
        references of Odoo): kept on the transaction, the notifications are found by it."""
        self.ensure_one()
        if not self.cinetpay_transaction_id:
            clean = re.sub(r"[^A-Za-z0-9-]+", "-", self.reference or "").strip("-")[:50] or "TX"
            self.with_context(payment_safe_write=True).write({"cinetpay_transaction_id": f"{clean}-{self.id}"})
        return self.cinetpay_transaction_id

    def _cinetpay_amount(self):
        """The amount asked to CinetPay: in CFA francs (and the francs of Guinea and of the Congo), a whole
        number, multiple of 5, rounded up (a few francs at most); kept on the transaction, the amount
        CinetPay collects is checked against it."""
        self.ensure_one()
        amount = self.amount
        if self.currency_id.name in const.MULTIPLE_OF_5_CURRENCIES:
            amount = float(math.ceil(round(amount, 2) / 5) * 5)
        else:
            amount = round(amount, 2)
        if self.cinetpay_requested_amount != amount:
            self.with_context(payment_safe_write=True).write({"cinetpay_requested_amount": amount})
        return int(amount) if amount == int(amount) else amount

    def _cinetpay_description(self):
        """The description of the payment page: letters and numbers only (CinetPay refuses #, /, $, _ and &)."""
        text = self.env._("Order %(reference)s on %(company)s", reference=self.reference, company=self.company_id.name)
        for char in "#/$_&":
            text = text.replace(char, " ")
        return " ".join(text.split())[:250]

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to send the customer to the payment page of CinetPay.

        Note: `self.ensure_one()` from `_get_processing_values`
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "cinetpay":
            return res
        base_url = self.provider_id.get_base_url()
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        payload = {
            **self.provider_id._cinetpay_credentials(),
            "transaction_id": self._cinetpay_id(),
            "amount": self._cinetpay_amount(),
            "currency": self.currency_id.name,
            "description": self._cinetpay_description(),
            "notify_url": urls.urljoin(base_url, CinetpayController._webhook_url),
            "return_url": urls.urljoin(base_url, CinetpayController._return_url),
            "channels": const.CHANNELS_MAPPING.get(self.payment_method_code, "ALL"),
            "lang": "FR" if (self.partner_lang or "").startswith("fr") else "EN",
            "metadata": self.reference,
            "customer_name": (first_name or self.partner_name or "-")[:60],
            "customer_surname": (last_name or first_name or "-")[:60],
            "customer_phone_number": self.partner_phone or "",
            "customer_email": self.partner_email or "",
            "customer_country": self.partner_country_id.code or "",
            "customer_city": self.partner_city or "",
        }
        try:
            response_content = self.provider_id._send_api_request("POST", "payment", json=payload, reference=self.reference)
        except ValidationError as error:
            self._set_error(str(error))
            return {}
        data = response_content.get("data") or {}
        link = data.get("payment_url")
        if str(response_content.get("code")) != "201" or not link:
            self._set_error(self.env._(
                "CinetPay did not open the payment: %s",
                response_content.get("description") or response_content.get("message") or "-",
            ))
            return {}
        if data.get("payment_token"):
            self.provider_reference = data["payment_token"]
        return {"api_url": link, "http_method": "get", "url_params": payment_utils.extract_url_params(link)}

    def _cinetpay_fetch_status(self):
        """Read the state of the payment from CinetPay (verification API) and queue it for processing.

        Note: `self.ensure_one()`

        :return: The payment data, or an empty dict when CinetPay did not answer.
        :rtype: dict
        """
        self.ensure_one()
        try:
            response_content = self.provider_id._send_api_request(
                "POST", "payment/check",
                json={**self.provider_id._cinetpay_credentials(), "transaction_id": self._cinetpay_id()},
                reference=self.reference,
            )
        except ValidationError:
            _logger.warning("Unable to check the status of transaction %s with CinetPay.", self.reference)
            return {}
        data = response_content.get("data") or {}
        payment_data = {
            "reference": self.reference,
            "status": (data.get("status") or "").upper(),
            "amount": data.get("amount"),
            "currency": data.get("currency"),
            "operator_id": data.get("operator_id"),
            "payment_method": data.get("payment_method"),
            "code": str(response_content.get("code") or ""),
            "message": response_content.get("message") or "",
        }
        final = payment_data["status"] in {
            *const.PAYMENT_STATUS_MAPPING["done"], *const.PAYMENT_STATUS_MAPPING["cancel"],
            *const.PAYMENT_STATUS_MAPPING["error"],
        }
        if final:
            self._record(payment_data)
        return payment_data

    @api.model
    def _cron_cinetpay_check_pending(self):
        """Check the payments of CinetPay still waiting, in case a notification was missed."""
        since = fields.Datetime.now() - timedelta(hours=const.PENDING_CHECK_WINDOW_HOURS)
        transactions = self.search(
            Domain("provider_code", "=", "cinetpay")
            & Domain("state", "in", ("draft", "pending"))
            & Domain("create_date", ">=", since)
        )
        for transaction in transactions:
            transaction._cinetpay_fetch_status()

    # === BUSINESS METHODS - PROCESSING === #

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "cinetpay":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("reference")

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction from the state read from CinetPay."""
        if self.provider_code != "cinetpay":
            return super()._apply_updates(payment_data)
        if payment_data.get("operator_id"):
            self.provider_reference = payment_data["operator_id"]
        status = payment_data.get("status") or ""
        if status in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        elif status in const.PAYMENT_STATUS_MAPPING["error"]:
            self._set_error(self.env._(
                "The payment was refused or cancelled, or the balance was insufficient (%s).",
                payment_data.get("message") or status,
            ))
        else:
            self._set_pending()

    def _extract_amount_data(self, payment_data):
        """Override of `payment`: CinetPay collected the amount asked (rounded up to a multiple of 5):
        the transaction is paid for its own amount; another amount is refused, as for any payment."""
        if self.provider_code != "cinetpay":
            return super()._extract_amount_data(payment_data)
        try:
            amount = float(payment_data.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if self.cinetpay_requested_amount and amount == self.cinetpay_requested_amount:
            amount = self.amount
        return {"amount": amount, "currency_code": payment_data.get("currency") or self.currency_id.name,
                "precision_digits": self.currency_id.decimal_places}
