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
