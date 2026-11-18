from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_cinetpay.controllers.main import CinetpayController

SEND_API_REQUEST = "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request"
FETCH_STATUS = "odoo.addons.payment_cinetpay.models.payment_transaction.PaymentTransaction._cinetpay_fetch_status"
RECORD = "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"


@tagged("post_install", "-at_install")
class TestCinetpay(PaymentHttpCommon):
    """CinetPay (chantier 5): Mobile Money, wallets and cards in the UEMOA and Central Africa."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls._enable_currency("XOF")
        cls.amount = 1503.0
        cls.cinetpay = cls._prepare_provider("cinetpay", update_values={
            "cinetpay_site_id": "105889", "cinetpay_api_key": "api-key", "cinetpay_secret_key": "secret",
        })
        cls.provider = cls.cinetpay
        cls.payment_method_id = cls.cinetpay.payment_method_ids.filtered(lambda pm: pm.code == "mobile_money").id

    def _check(self, status="ACCEPTED", amount="1505", code="00"):
        return {"code": code, "message": "SUCCES", "data": {
            "amount": amount, "currency": "XOF", "status": status, "payment_method": "OMCIV2", "operator_id": "MP2311.1",
        }}

    def test_the_payment_page_of_cinetpay(self):
        self.assertEqual(set(self.cinetpay.payment_method_ids.mapped("code")), {"mobile_money", "wallet", "card"})
        self.assertIn(self.env.ref("base.tg"), self.cinetpay.available_country_ids, "The UEMOA")
        tx = self._create_transaction("redirect")
        response = {"code": "201", "message": "CREATED", "data": {
            "payment_token": "tok-123", "payment_url": "https://checkout.cinetpay.com/payment/tok-123",
        }}
        with patch(SEND_API_REQUEST, return_value=response) as request_mock:
            processing_values = tx._get_processing_values()
        payload = request_mock.call_args.kwargs["json"]
        self.assertEqual((payload["apikey"], payload["site_id"]), ("api-key", "105889"))
        self.assertEqual(payload["transaction_id"], f"Test-Transaction-{tx.id}", "Letters, numbers and dashes only")
        self.assertEqual((payload["amount"], payload["currency"], payload["channels"]), (1505, "XOF", "MOBILE_MONEY"),
                         "A multiple of 5, rounded up")
        self.assertTrue(payload["notify_url"].endswith("/payment/cinetpay/webhook"))
        self.assertTrue(payload["return_url"].endswith("/payment/cinetpay/return"))
        for char in "#/$_&":
            self.assertNotIn(char, payload["description"])
        self.assertIn("https://checkout.cinetpay.com/payment/tok-123", processing_values["redirect_form_html"])
        self.assertEqual(tx.cinetpay_requested_amount, 1505)
        # CinetPay refuses: the transaction says why
        tx2 = self._create_transaction("redirect", reference="R2")
        with patch(SEND_API_REQUEST, return_value={"code": "608", "description": "MINIMUM_REQUIRED_FIELDS"}):
            tx2._get_processing_values()
        self.assertEqual(tx2.state, "error")
        self.assertIn("MINIMUM_REQUIRED_FIELDS", tx2.state_message)

    def test_the_state_is_read_from_cinetpay(self):
        tx = self._create_transaction("redirect")
        tx._cinetpay_amount()
        with patch(SEND_API_REQUEST, return_value=self._check()) as request_mock, patch(RECORD) as record_mock:
            tx._cinetpay_fetch_status()
        self.assertEqual(request_mock.call_args.args[1], "payment/check")
        self.assertEqual(record_mock.call_args.args[0]["status"], "ACCEPTED")
        with patch(SEND_API_REQUEST, return_value=self._check(status="WAITING_CUSTOMER_PAYMENT", code="662")), \
                patch(RECORD) as record_mock:
            tx._cinetpay_fetch_status()
        record_mock.assert_not_called()

    def test_the_payment_is_processed(self):
        self._disable_process_patcher()
        tx = self._create_transaction("redirect")
        tx._cinetpay_amount()
        data = {"reference": tx.reference, "status": "ACCEPTED", "amount": "1505", "currency": "XOF", "operator_id": "MP1"}
        tx.with_context(payment_safe_write=True)._process(data)
        self.assertEqual((tx.state, tx.provider_reference), ("done", "MP1"), "Paid for its own amount")
        refused = self._create_transaction("redirect", reference="R3")
        refused._cinetpay_amount()
        refused.with_context(payment_safe_write=True)._process(dict(data, reference="R3", status="REFUSED"))
        self.assertEqual(refused.state, "error")
        wrong = self._create_transaction("redirect", reference="R4")
        wrong._cinetpay_amount()
        wrong.with_context(payment_safe_write=True)._process(dict(data, reference="R4", amount="100"))
        self.assertEqual(wrong.state, "error", "Another amount is refused")

    @mute_logger("odoo.addons.payment_cinetpay.controllers.main")
    def test_the_notification_and_the_return(self):
        tx = self._create_transaction("redirect")
        transaction_id = tx._cinetpay_id()
        with patch(FETCH_STATUS) as fetch_mock:
            response = self._make_http_post_request(self._build_url(CinetpayController._webhook_url), data={
                "cpm_site_id": "105889", "cpm_trans_id": transaction_id, "cpm_amount": "1505",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(fetch_mock.call_count, 1)
        with patch(FETCH_STATUS) as fetch_mock:
            self._make_http_post_request(self._build_url(CinetpayController._webhook_url), data={
                "cpm_site_id": "999", "cpm_trans_id": transaction_id,
            })
        fetch_mock.assert_not_called()
        with patch(FETCH_STATUS) as fetch_mock:
            response = self._make_http_get_request(self._build_url(CinetpayController._return_url),
                                                   params={"transaction_id": transaction_id})
        self.assertEqual(fetch_mock.call_count, 1)
        self.assertIn("/payment/status", response.url)

    def test_the_payments_waiting_are_checked_again(self):
        tx = self._create_transaction("redirect", state="pending")
        with patch(FETCH_STATUS) as fetch_mock:
            self.env["payment.transaction"]._cron_cinetpay_check_pending()
        self.assertEqual(fetch_mock.call_count, 1)
        self.assertTrue(tx)
