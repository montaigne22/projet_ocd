from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_payment.models.payment_transaction import (
    PaymentTransaction as AccountPaymentTransaction,
)
from odoo.addons.payment_campay.tests.common import CampayCommon

SEND_API_REQUEST = "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request"


@tagged("post_install", "-at_install")
class TestDemoPayments(CampayCommon):
    """The demo payments: each payment collects the demo amount (25 F CFA by default) instead of
    the amount of the order, the pages keep the real amounts and the order is paid as usual."""

    def _collect(self, phone="6 70 00 00 01", **values):
        """A Mobile Money payment of 15 000 F CFA from `phone`; the first one has the reference
        of the payment data of Campay, the next ones their own."""
        self.collected = getattr(self, "collected", 0) + 1
        if self.collected > 1:
            values.setdefault("reference", f"{self.reference}-{self.collected}")
        tx = self._create_transaction("direct", **values)
        response = {"reference": self.campay_reference, "ussd_code": "*126#", "operator": "MTN"}
        with patch(SEND_API_REQUEST, return_value=response) as request_mock:
            tx._campay_request_collect(phone)
        return tx, request_mock.call_args.kwargs["json"]

    def _demo_on(self, **values):
        self.campay.write({"campay_demo_active": True, **values})

    def test_off_by_default(self):
        tx, payload = self._collect()
        self.assertEqual(payload["amount"], 15000)
        self.assertEqual(tx.campay_requested_amount, 15000)
        self.assertFalse(tx.campay_demo)

    def test_every_payment_collects_the_demo_amount(self):
        self._demo_on()
        tx, payload = self._collect()
        self.assertEqual(payload["amount"], 25)
        self.assertEqual(tx.amount, 15000, "The transaction keeps the real amount.")
        self.assertEqual(tx.campay_requested_amount, 25)
        self.assertTrue(tx.campay_demo)

    def test_demo_amount_is_configurable(self):
        self._demo_on(campay_demo_amount=100)
        _tx, payload = self._collect()
        self.assertEqual(payload["amount"], 100)

    def test_demo_payment_pays_the_transaction(self):
        self._disable_process_patcher()
        self._demo_on()
        tx, _payload = self._collect()
        tx.with_context(payment_safe_write=True)._process(dict(self.payment_data, amount=25))
        self.assertEqual(tx.state, "done")

    def test_demo_payment_refuses_another_amount(self):
        self._disable_process_patcher()
        self._demo_on()
        tx, _payload = self._collect()
        tx.with_context(payment_safe_write=True)._process(dict(self.payment_data, amount=10))
        self.assertEqual(tx.state, "error")

    def test_real_payment_refuses_the_demo_amount(self):
        """The demo amount pays only a transaction asked as a demo payment."""
        self._disable_process_patcher()
        tx, _payload = self._collect()
        tx.with_context(payment_safe_write=True)._process(dict(self.payment_data, amount=25))
        self.assertEqual(tx.state, "error")

    def test_only_the_demo_numbers(self):
        self._demo_on(campay_demo_numbers="670000001, 237 690 00 00 02\n6 50 00 00 03")
        self.assertEqual(
            self.campay._campay_demo_number_list(), {"237670000001", "237690000002", "237650000003"}
        )
        tx, payload = self._collect("670000001")
        self.assertEqual(payload["amount"], 25)
        self.assertTrue(tx.campay_demo)
        tx, payload = self._collect("690000002")
        self.assertEqual(payload["amount"], 25)
        tx, payload = self._collect("670000000")
        self.assertEqual(payload["amount"], 15000, "Another number pays the real price.")
        self.assertFalse(tx.campay_demo)

    def test_stops_after_the_last_day(self):
        yesterday = fields.Date.context_today(self.campay) - timedelta(days=1)
        self._demo_on(campay_demo_end=yesterday)
        self.assertFalse(self.campay._campay_demo_on())
        _tx, payload = self._collect()
        self.assertEqual(payload["amount"], 15000)

    def test_switched_on_without_a_day_until_tonight(self):
        today = fields.Date.context_today(self.campay)
        self._demo_on()
        self.assertEqual(self.campay.campay_demo_end, today)
        # Switched on again with a day already past: until tonight, not off at once
        self.campay.write({"campay_demo_active": False})
        self.campay.write({"campay_demo_end": today - timedelta(days=3)})
        self.campay.write({"campay_demo_active": True})
        self.assertEqual(self.campay.campay_demo_end, today)
        # A day emptied while on: until tonight
        self.campay.write({"campay_demo_end": False})
        self.assertEqual(self.campay.campay_demo_end, today)
        # A later day is kept
        self.campay.write({"campay_demo_end": today + timedelta(days=2)})
        self.assertEqual(self.campay.campay_demo_end, today + timedelta(days=2))

    def test_card_payment_link_asks_the_demo_amount(self):
        self._demo_on()
        card = self.campay.payment_method_ids.filtered(lambda pm: pm.code == "card")
        tx = self._create_transaction("redirect", payment_method_id=card.id)
        response = {"link": "https://www.campay.net/pay/abc?lang=fr", "reference": self.campay_reference}
        with patch(SEND_API_REQUEST, return_value=response) as request_mock:
            tx._get_processing_values()
        self.assertEqual(request_mock.call_args.kwargs["json"]["amount"], 25)
        self.assertTrue(tx.campay_demo)

    def test_accounts_record_the_money_received(self):
        """The payment of the accounts is the money Campay collected, not the price."""
        self._demo_on()
        tx, _payload = self._collect()
        with patch.object(AccountPaymentTransaction, "_create_payment", autospec=True) as create_mock:
            tx._create_payment()
        self.assertEqual(create_mock.call_args.kwargs["amount"], 25)

        self.campay.write({"campay_demo_active": False})
        tx, _payload = self._collect()
        with patch.object(AccountPaymentTransaction, "_create_payment", autospec=True) as create_mock:
            tx._create_payment()
        self.assertNotIn("amount", create_mock.call_args.kwargs)
