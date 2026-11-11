import base64
import hashlib
import hmac
import json
import time

from odoo.addons.payment.tests.common import PaymentCommon


def make_jwt(key, payload, alg="HS256"):
    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    signing_input = f"{b64({'alg': alg, 'typ': 'JWT'})}.{b64(payload)}"
    digest = hmac.new(key.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(digest).rstrip(b'=').decode()}"


class CampayCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_xaf = cls._enable_currency("XAF")
        cls.currency = cls.currency_xaf
        cls.amount = 15000.0
        cls.campay = cls._prepare_provider(
            "campay",
            update_values={
                "campay_app_username": "app-user",
                "campay_app_password": "app-password",
                "campay_webhook_key": "webhook-key",
            },
        )
        cls.provider = cls.campay
        cls.payment_method_id = cls.campay.payment_method_ids.filtered(
            lambda pm: pm.code == "mobile_money"
        ).id
        cls.campay_reference = "bcedde9b-62a7-4421-96ac-2e6179552a1a"
        cls.payment_data = {
            "reference": cls.campay_reference,
            "external_reference": cls.reference,
            "status": "SUCCESSFUL",
            "amount": 15000,
            "currency": "XAF",
            "operator": "MTN",
            "code": "CP201027T00005",
            "operator_reference": "1880106956",
        }

    def _valid_signature(self, **payload):
        return make_jwt("webhook-key", {"source": "campay", "exp": int(time.time()) + 300, **payload})
