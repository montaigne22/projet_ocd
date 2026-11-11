import time

from odoo.tests import tagged

from odoo.addons.payment_campay.tests.common import CampayCommon, make_jwt


@tagged("post_install", "-at_install")
class TestPaymentProvider(CampayCommon):

    def test_supported_currencies_and_methods(self):
        self.assertEqual(self.campay._get_supported_currencies().mapped("name"), ["XAF"])
        self.assertEqual(
            set(self.campay.payment_method_ids.mapped("code")), {"mobile_money", "card"}
        )

    def test_phone_normalization(self):
        normalize = self.campay._campay_normalize_phone
        self.assertEqual(normalize("6 70 00 00 00"), "237670000000")
        self.assertEqual(normalize("+237 690 00 00 00"), "237690000000")
        self.assertEqual(normalize("00237655000000"), "237655000000")
        self.assertEqual(normalize("237670000000"), "237670000000")
        self.assertEqual(normalize("2 33 42 00 00"), "")  # landline
        self.assertEqual(normalize("+33 6 12 34 56 78"), "")
        self.assertEqual(normalize(""), "")

    def test_webhook_signature_is_verified(self):
        verify = self.campay._campay_verify_webhook_signature
        self.assertTrue(verify(self._valid_signature()))
        self.assertFalse(verify(make_jwt("other-key", {"source": "campay"})))
        self.assertFalse(verify(make_jwt("webhook-key", {"source": "other"})))
        self.assertFalse(
            verify(make_jwt("webhook-key", {"source": "campay", "exp": int(time.time()) - 10}))
        )
        self.assertFalse(verify(make_jwt("webhook-key", {"source": "campay"}, alg="none")))
        self.assertFalse(verify("not-a-jwt"))
        self.assertFalse(verify(""))

    def test_test_and_live_urls(self):
        self.campay.is_live = False
        self.assertTrue(self.campay._build_request_url("collect/").startswith("https://demo.campay.net/api/"))
        self.campay.is_live = True
        self.assertTrue(self.campay._build_request_url("collect/").startswith("https://www.campay.net/api/"))
