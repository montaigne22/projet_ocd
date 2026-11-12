from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import float_round, urls
from odoo.tools.misc import format_amount

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_campay import const
from odoo.addons.payment_campay.controllers.main import CampayController

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    campay_requested_amount = fields.Integer(
        string="Amount Asked To Campay", readonly=True, copy=False,
        help="In CFA francs: the amount of the transaction, or the demo amount of a demo payment.",
    )
    campay_demo = fields.Boolean(string="Demo Payment", readonly=True, copy=False)

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _get_specific_processing_values(self, processing_values):
        """Override of `payment` to give the payment form an access token for the Mobile Money
        routes of this transaction.

        Note: `self.ensure_one()` from `_get_processing_values`
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "campay":
            return res
        return {
            **res,
            "campay_access_token": payment_utils.generate_access_token(
                self.reference, self.amount, self.currency_id.id, env=self.env
            ),
        }

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to redirect card payments to the Campay payment page.

        Note: `self.ensure_one()` from `_get_processing_values`
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "campay":
            return res

        base_url = self.provider_id.get_base_url()
        return_url = urls.urljoin(base_url, CampayController._return_url)
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        payload = {
            "amount": self._campay_amount(),
            "currency": self.currency_id.name,
            "description": self._campay_description(),
            "external_reference": self.reference,
            "redirect_url": return_url,
            "failure_redirect_url": return_url,
            "first_name": first_name,
            "last_name": last_name,
            "email": self.partner_email or "",
            "payment_options": const.PAYMENT_OPTIONS_MAPPING.get(self.payment_method_code, "CARD"),
        }
        phone = self.provider_id._campay_normalize_phone(self.partner_phone)
        if phone:
            payload["from"] = phone
        try:
            response_content = self._send_api_request("POST", "get_payment_link/", json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        link = response_content.get("link")
        if not link:
            self._set_error(self.env._("Campay did not return a payment link."))
            return {}
        if response_content.get("reference"):
            self.provider_reference = response_content["reference"]
        return {
            "api_url": link,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(link),
        }

    def _campay_request_collect(self, phone):
        """Ask Campay to send a Mobile Money payment request to the customer's phone.

        The customer confirms the payment on the phone (USSD prompt or menu of the operator);
        the result arrives later through the webhook or the status checks.

        Note: `self.ensure_one()`

        :param str phone: The phone number typed by the customer.
        :return: The instructions to show to the customer: the USSD code and the operator.
        :rtype: dict
        :raise ValidationError: If the number is invalid or if Campay rejects the request.
        """
        self.ensure_one()
        msisdn = self.provider_id._campay_normalize_phone(phone)
        if not msisdn:
            raise ValidationError(self.env._(
                "Enter a Cameroonian mobile number, e.g. 6 70 00 00 00 (MTN) or 6 90 00 00 00 "
                "(Orange)."
            ))
        response_content = self._send_api_request(
            "POST",
            "collect/",
            json={
                "amount": self._campay_amount(msisdn),
                "currency": self.currency_id.name,
                "from": msisdn,
                "description": self._campay_description(),
                "external_reference": self.reference,
            },
        )
        campay_reference = response_content.get("reference")
        if not campay_reference:
            raise ValidationError(self.env._("Campay did not return a transaction reference."))

        # The Campay reference is needed to check the payment status: keep it even if the
        # request is retried, the customer being asked to pay only once per collect request.
        self.with_context(payment_safe_write=True).write({"provider_reference": campay_reference})
        self.with_context(payment_safe_write=True)._set_pending()
        return {
            "ussd_code": response_content.get("ussd_code", ""),
            "operator": response_content.get("operator", ""),
        }

    def _campay_fetch_status(self):
        """Read the transaction status from Campay and queue it for processing.

        Note: `self.ensure_one()`

        :return: The payment data returned by Campay, or an empty dict if unavailable.
        :rtype: dict
        """
        self.ensure_one()
        if not self.provider_reference:
            return {}
        try:
            payment_data = self._send_api_request("GET", f"transaction/{self.provider_reference}/")
        except ValidationError:
            _logger.warning("Unable to check the status of transaction %s.", self.reference)
            return {}
        if payment_data.get("external_reference") != self.reference:
            _logger.warning(
                "Campay transaction %s does not belong to transaction %s.",
                self.provider_reference,
                self.reference,
            )
            return {}
        if payment_data.get("status") not in const.PAYMENT_STATUS_MAPPING["pending"]:
            self._record(payment_data)
        return payment_data

    @api.model
    def _cron_campay_check_pending(self):
        """Check the status of recent pending Campay transactions, in case a webhook call was
        missed (unreachable server, misconfigured webhook URL...)."""
        since = fields.Datetime.now() - timedelta(minutes=const.PENDING_CHECK_WINDOW_MINUTES)
        transactions = self.search(
            Domain("provider_code", "=", "campay")
            & Domain("state", "=", "pending")
            & Domain("provider_reference", "!=", False)
            & Domain("create_date", ">=", since)
        )
        for transaction in transactions:
            transaction._campay_fetch_status()

    def _campay_amount(self, phone=None):
        """Return the amount asked to Campay, as an integer number of CFA francs: the amount of
        the transaction, or the demo amount while the demo payments are on for the number
        `phone` (the pages show the real amounts). It is kept on the transaction: the amount
        Campay collects is checked against it."""
        self.ensure_one()
        demo = self.provider_id._campay_demo_amount(phone or self.partner_phone)
        amount = demo or int(float_round(self.amount, precision_digits=0))
        if (self.campay_requested_amount, self.campay_demo) != (amount, bool(demo)):
            self.with_context(payment_safe_write=True).write({
                "campay_requested_amount": amount, "campay_demo": bool(demo),
            })
        return amount

    def _campay_description(self):
        description = self.env._(
            "%(company)s order %(reference)s",
            company=self.company_id.name,
            reference=self.reference,
        )
        return description[:255]

    # === BUSINESS METHODS - PROCESSING === #

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "campay":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("external_reference")

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "campay":
            return super()._apply_updates(payment_data)

        if payment_data.get("reference"):
            self.provider_reference = payment_data["reference"]

        status = (payment_data.get("status") or "").upper()
        if status in const.PAYMENT_STATUS_MAPPING["pending"]:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING["error"]:
            self._set_error(self.env._(
                "The payment was declined or cancelled on the phone, or the balance was "
                "insufficient."
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction %s.",
                status,
                self.reference,
            )
            self._set_error(self.env._("Unknown payment status: %s", status))

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data.

        A demo payment collected the demo amount: when Campay collected exactly the amount asked,
        the transaction is paid for its own amount (the order is paid as usual); another amount
        is refused, as for any payment."""
        if self.provider_code != "campay":
            return super()._extract_amount_data(payment_data)
        amount = float(payment_data.get("amount") or 0)
        currency_code = payment_data.get("currency") or self.currency_id.name
        if self.campay_demo and self.campay_requested_amount and amount == self.campay_requested_amount:
            amount = self.amount
        return {"amount": amount, "currency_code": currency_code, "precision_digits": 0}

    def _create_payment(self, **extra_create_values):
        """Override of `account_payment`: a demo payment records the money Campay collected (the
        demo amount), so that the accounts stay right."""
        if self.provider_code == "campay" and self.campay_demo and self.campay_requested_amount:
            extra_create_values.setdefault("amount", self.campay_requested_amount)
        return super()._create_payment(**extra_create_values)

    def _post_process(self):
        """Override of `payment`: a demo payment says it on the documents it paid."""
        super()._post_process()
        for transaction in self.filtered(lambda t: t.provider_code == "campay" and t.campay_demo and t.state == "done"):
            message = self.env._(
                "Demo payment: %(collected)s collected by Campay for %(amount)s.",
                collected=format_amount(self.env, transaction.campay_requested_amount, transaction.currency_id),
                amount=format_amount(self.env, transaction.amount, transaction.currency_id),
            )
            documents = [*transaction.invoice_ids]
            if "sale_order_ids" in transaction._fields:
                documents += [*transaction.sale_order_ids]
            for document in documents:
                document.message_post(body=message)
