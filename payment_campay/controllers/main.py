import pprint
import re

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_campay import const

_logger = get_payment_logger(__name__, {"signature", "token", "password"})


class CampayController(http.Controller):
    _return_url = "/payment/campay/return"
    _webhook_url = "/payment/campay/webhook"
    _collect_url = "/payment/campay/collect"
    _status_url = "/payment/campay/status"

    @http.route(_collect_url, type="jsonrpc", auth="public")
    def campay_collect(self, reference, access_token, phone):
        """Send the Mobile Money payment request to the customer's phone.

        :param str reference: The reference of the transaction.
        :param str access_token: The access token given to the payment form for this transaction.
        :param str phone: The phone number typed by the customer.
        :return: The instructions to show to the customer.
        :rtype: dict
        """
        tx_sudo = self._get_transaction(reference, access_token)
        if tx_sudo.state != "draft":
            raise ValidationError(request.env._("This payment has already been requested."))
        return tx_sudo._campay_request_collect(phone)

    @http.route(_status_url, type="jsonrpc", auth="public")
    def campay_status(self, reference, access_token):
        """Check the payment status with Campay while the customer confirms on the phone.

        A final status (paid, failed) is queued for processing, as with the webhook; the payment
        form then sends the customer to the status page of Odoo, which processes it in another
        request (/payment/process). It is never processed in this request: the processing runs
        with its own cursor, which waits for the locks that this request holds on the
        transaction until the request ends, and the request would never end.

        :param str reference: The reference of the transaction.
        :param str access_token: The access token given to the payment form for this transaction.
        :return: The state of the transaction, and whether its final status was received.
        :rtype: dict
        """
        tx_sudo = self._get_transaction(reference, access_token)
        received = bool(tx_sudo.payment_data_ids)
        if not received and tx_sudo.state in ("draft", "pending"):
            payment_data = tx_sudo._campay_fetch_status()
            received = bool(payment_data) and (
                payment_data.get("status") not in const.PAYMENT_STATUS_MAPPING["pending"]
            )
        return {
            "state": tx_sudo.state,
            "received": received,
            "state_message": tx_sudo.state_message or "",
        }

    @http.route(_return_url, type="http", methods=["GET"], auth="public")
    def campay_return_from_checkout(self, **data):
        """Process the return of the customer from the Campay payment page.

        The parameters of the URL are only used to find the transaction: its status is read from
        the Campay API.
        """
        _logger.info("Handling redirection from Campay with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            request.env["payment.transaction"].sudo()._search_by_reference("campay", data)
        )
        if tx_sudo:
            if not tx_sudo.provider_reference and self._is_campay_reference(data.get("reference")):
                tx_sudo.with_context(payment_safe_write=True).write(
                    {"provider_reference": data["reference"]}
                )
            tx_sudo._campay_fetch_status()
        return request.redirect("/payment/status")

    @http.route(_webhook_url, type="http", methods=["GET", "POST"], auth="public", csrf=False)
    def campay_webhook(self, **data):
        """Process the notification sent by Campay when a payment ends.

        Campay calls the webhook with the transaction data in the URL and signs the call with a
        JWT built with the webhook key. As a genuine signature does not prove which transaction the
        call is about, the status, the amount and the reference are read from the Campay API.

        :return: An empty response to acknowledge the notification.
        """
        _logger.info("Notification received from Campay with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            request.env["payment.transaction"].sudo()._search_by_reference("campay", data)
        )
        if tx_sudo:
            if not tx_sudo.provider_id._campay_verify_webhook_signature(data.get("signature")):
                _logger.warning("Received a Campay notification with an invalid signature.")
                raise Forbidden
            if not tx_sudo.provider_reference and self._is_campay_reference(data.get("reference")):
                tx_sudo.with_context(payment_safe_write=True).write(
                    {"provider_reference": data["reference"]}
                )
            tx_sudo._campay_fetch_status()
        return request.make_response("")

    @staticmethod
    def _get_transaction(reference, access_token):
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            .search([("reference", "=", reference), ("provider_code", "=", "campay")], limit=1)
        )
        if not tx_sudo or not payment_utils.check_access_token(
            access_token, tx_sudo.reference, tx_sudo.amount, tx_sudo.currency_id.id
        ):
            raise Forbidden
        return tx_sudo

    @staticmethod
    def _is_campay_reference(reference):
        return bool(reference and re.fullmatch(r"[A-Za-z0-9-]{1,64}", reference))
