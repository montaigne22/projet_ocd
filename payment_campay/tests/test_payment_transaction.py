from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_campay.tests.common import CampayCommon

SEND_API_REQUEST = "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request"


@tagged("post_install", "-at_install")
class TestPaymentTransaction(CampayCommon):

    def test_collect_sets_reference_and_pending(self):
        tx = self._create_transaction("direct")
        response = {"reference": self.campay_reference, "ussd_code": "*126#", "operator": "MTN"}
        with patch(SEND_API_REQUEST, return_value=response) as request_mock:
            instructions = tx._campay_request_collect("6 70 00 00 00")
        payload = request_mock.call_args.kwargs["json"]
        self.assertEqual(payload["from"], "237670000000")
        self.assertEqual(payload["amount"], 15000)
        self.assertEqual(payload["currency"], "XAF")
        self.assertEqual(payload["external_reference"], tx.reference)
        self.assertEqual(tx.provider_reference, self.campay_reference)
        self.assertEqual(tx.state, "pending")
        self.assertEqual(instructions, {"ussd_code": "*126#", "operator": "MTN"})

    def test_collect_rejects_invalid_numbers(self):
        tx = self._create_transaction("direct")
        with patch(SEND_API_REQUEST) as request_mock, self.assertRaises(ValidationError):
            tx._campay_request_collect("12345")
        request_mock.assert_not_called()

    def test_successful_payment_is_processed(self):
        self._disable_process_patcher()
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._process(self.payment_data)
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, self.campay_reference)

    def test_failed_payment_is_processed(self):
        self._disable_process_patcher()
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._process(dict(self.payment_data, status="FAILED"))
        self.assertEqual(tx.state, "error")

    def test_amount_mismatch_is_rejected(self):
        self._disable_process_patcher()
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._process(dict(self.payment_data, amount=100))
        self.assertEqual(tx.state, "error")

    def test_fetch_status_records_final_status_only(self):
        tx = self._create_transaction("direct", provider_reference=self.campay_reference)
        with (
            patch(SEND_API_REQUEST, return_value=self.payment_data),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._record") as record_mock,
        ):
            tx._campay_fetch_status()
        record_mock.assert_called_once_with(self.payment_data)

        with (
            patch(SEND_API_REQUEST, return_value=dict(self.payment_data, status="PENDING")),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._record") as record_mock,
        ):
            tx._campay_fetch_status()
        record_mock.assert_not_called()

    def test_fetch_status_ignores_other_transactions(self):
        tx = self._create_transaction("direct", provider_reference=self.campay_reference)
        with (
            patch(SEND_API_REQUEST, return_value=dict(self.payment_data, external_reference="OTHER")),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._record") as record_mock,
        ):
            self.assertEqual(tx._campay_fetch_status(), {})
        record_mock.assert_not_called()

    def test_card_payment_redirects_to_campay(self):
        card = self.campay.payment_method_ids.filtered(lambda pm: pm.code == "card")
        tx = self._create_transaction("redirect", payment_method_id=card.id)
        response = {"link": "https://www.campay.net/pay/abc?lang=fr", "reference": self.campay_reference}
        with patch(SEND_API_REQUEST, return_value=response) as request_mock:
            processing_values = tx._get_processing_values()
        payload = request_mock.call_args.kwargs["json"]
        self.assertEqual(payload["payment_options"], "CARD")
        self.assertTrue(payload["redirect_url"].endswith("/payment/campay/return"))
        self.assertIn("https://www.campay.net/pay/abc", processing_values["redirect_form_html"])
        self.assertEqual(tx.provider_reference, self.campay_reference)
        self.assertTrue(processing_values["campay_access_token"])
