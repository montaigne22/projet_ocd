from unittest.mock import patch

from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_campay.controllers.main import CampayController
from odoo.addons.payment_campay.tests.common import CampayCommon

FETCH_STATUS = (
    "odoo.addons.payment_campay.models.payment_transaction.PaymentTransaction._campay_fetch_status"
)


@tagged("post_install", "-at_install")
class TestProcessingFlows(CampayCommon, PaymentHttpCommon):

    def _webhook_params(self, signature):
        return {
            "status": "SUCCESSFUL",
            "reference": self.campay_reference,
            "external_reference": self.reference,
            "amount": "15000",
            "currency": "XAF",
            "signature": signature,
            "endpoint": "collect",
        }

    @mute_logger("odoo.addons.payment_campay.controllers.main")
    def test_webhook_with_valid_signature_checks_status(self):
        tx = self._create_transaction("direct")
        url = self._build_url(CampayController._webhook_url)
        with patch(FETCH_STATUS) as fetch_mock:
            response = self._make_http_get_request(url, params=self._webhook_params(self._valid_signature()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(fetch_mock.call_count, 1)
        self.assertEqual(tx.provider_reference, self.campay_reference)

    @mute_logger("odoo.addons.payment_campay.controllers.main", "odoo.http")
    def test_webhook_with_invalid_signature_is_rejected(self):
        self._create_transaction("direct")
        url = self._build_url(CampayController._webhook_url)
        with patch(FETCH_STATUS) as fetch_mock:
            response = self._make_http_get_request(url, params=self._webhook_params("forged.jwt.value"))
        self.assertEqual(response.status_code, 403)
        fetch_mock.assert_not_called()

    @mute_logger("odoo.addons.payment_campay.controllers.main")
    def test_return_from_card_page_checks_status(self):
        self._create_transaction("redirect")
        url = self._build_url(CampayController._return_url)
        with patch(FETCH_STATUS) as fetch_mock:
            self._make_http_get_request(url, params={
                "reference": self.campay_reference, "external_reference": self.reference,
            })
        self.assertEqual(fetch_mock.call_count, 1)

    @mute_logger("odoo.http")
    def test_mobile_money_routes_require_the_access_token(self):
        tx = self._create_transaction("direct")
        url = self._build_url(CampayController._status_url)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(url, {"reference": tx.reference, "access_token": "wrong"})

        token = payment_utils.generate_access_token(
            tx.reference, tx.amount, tx.currency_id.id, env=self.env
        )
        with patch(FETCH_STATUS, return_value={}):
            result = self.make_jsonrpc_request(url, {"reference": tx.reference, "access_token": token})
        self.assertEqual(result["state"], "draft")

    def test_status_route_queues_the_result_for_the_status_page(self):
        """While the customer confirms on the phone, the page asks the status: the result of
        Campay (paid) is queued for processing and the page is told to go on; it is processed
        by the status page of Odoo, in another request. Processing it in this request would wait
        for its own locks on the transaction, and the request would never end."""
        tx = self._create_transaction("direct", provider_reference=self.campay_reference)
        tx.with_context(payment_safe_write=True)._set_pending()
        url = self._build_url(CampayController._status_url)
        token = payment_utils.generate_access_token(tx.reference, tx.amount, tx.currency_id.id, env=self.env)
        params = {"reference": tx.reference, "access_token": token}
        Transaction = self.registry["payment.transaction"]
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                   return_value=dict(self.payment_data, status="PENDING")), \
                patch.object(Transaction, "_run_processing") as processing:
            result = self.make_jsonrpc_request(url, params)
        self.assertEqual(result, {"state": "pending", "received": False, "state_message": ""})
        self.assertFalse(tx.payment_data_ids)
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                   return_value=self.payment_data) as request_mock, \
                patch.object(Transaction, "_run_processing") as processing:
            result = self.make_jsonrpc_request(url, params)
            self.assertTrue(result["received"], "The result of Campay is received: the page goes on")
            self.assertEqual(result["state"], "pending", "Not processed yet")
            self.assertEqual(len(tx.payment_data_ids), 1)
            # Asked again before the status page: Campay is not called a second time
            result = self.make_jsonrpc_request(url, params)
            self.assertTrue(result["received"])
            self.assertEqual(request_mock.call_count, 1)
            self.assertEqual(len(tx.payment_data_ids), 1)
        processing.assert_not_called()
