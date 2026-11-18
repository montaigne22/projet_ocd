import pprint
import re

from odoo import http
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_cinetpay import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)

REFERENCE_RE = re.compile(r"[A-Za-z0-9-]{1,64}")


class CinetpayController(http.Controller):
    _return_url = "/payment/cinetpay/return"
    _webhook_url = "/payment/cinetpay/webhook"

    @staticmethod
    def _transaction(transaction_id):
        """The transaction of the identifier given to CinetPay."""
        if not transaction_id or not REFERENCE_RE.fullmatch(str(transaction_id)):
            return request.env["payment.transaction"].sudo()
        return request.env["payment.transaction"].sudo().search(
            [("cinetpay_transaction_id", "=", transaction_id), ("provider_code", "=", "cinetpay")], limit=1
        )

    @http.route(_return_url, type="http", methods=["GET", "POST"], auth="public", csrf=False, save_session=False)
    def cinetpay_return(self, **data):
        """The customer comes back from the payment page of CinetPay. The parameters only give the
        transaction: its state is read from CinetPay."""
        _logger.info("Handling redirection from CinetPay with data:\n%s", pprint.pformat(data))
        tx_sudo = self._transaction(data.get("transaction_id") or data.get("cpm_trans_id"))
        if tx_sudo:
            tx_sudo._cinetpay_fetch_status()
        return request.redirect("/payment/status")

    @http.route(_webhook_url, type="http", methods=["GET", "POST"], auth="public", csrf=False)
    def cinetpay_webhook(self, **data):
        """The notification of CinetPay when a payment changes. It is not trusted as it is: the state,
        the amount and the currency are read from the verification API of CinetPay.

        :return: An empty answer, 200, as CinetPay expects.
        """
        _logger.info("Notification received from CinetPay with data:\n%s", pprint.pformat(data))
        tx_sudo = self._transaction(data.get("cpm_trans_id") or data.get("transaction_id"))
        if tx_sudo and data.get("cpm_site_id", tx_sudo.provider_id.cinetpay_site_id) == tx_sudo.provider_id.cinetpay_site_id:
            tx_sudo._cinetpay_fetch_status()
        return request.make_response("OK")
