from unittest.mock import MagicMock

from odoo.tests import TransactionCase

REQUEST = "odoo.addons.whatsapp_cloud.models.whatsapp_account.requests.request"


def mock_response(payload, status=200):
    """Answer of the Graph API, as returned by ``requests.request``."""
    response = MagicMock()
    response.ok = status < 400
    response.status_code = status
    response.reason = "OK" if status < 400 else "Bad Request"
    response.json.return_value = payload
    return response


class WhatsAppCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["res.lang"]._activate_lang("en_US")
        cls.cameroon = cls.env.ref("base.cm")
        cls.account = cls.env["whatsapp.account"].create({
            "name": "My Shop",
            "phone_number_id": "1110001",
            "waba_id": "2220002",
            "access_token": "test-token",
            "app_secret": "test-secret",
            "verify_token": "test-verify-token",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Awa Ngono",
            "phone": "6 70 00 00 00",
            "country_id": cls.cameroon.id,
            "whatsapp_opt_in": True,
            "lang": "en_US",
        })
        cls.template = cls.env["whatsapp.template"].create({
            "name": "Welcome",
            "template_name": "welcome",
            "lang_code": "fr",
            "model_id": cls.env["ir.model"]._get_id("res.partner"),
            "account_id": cls.account.id,
            "body": "Bonjour {{1}}, votre numéro est {{2}}.",
        })
        first, second = cls.template.variable_ids
        first.value = "{{ object.name }}"
        second.value = "{{ object.phone }}"
