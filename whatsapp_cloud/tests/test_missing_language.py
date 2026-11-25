import json
from unittest.mock import patch

from odoo.tests import tagged

from .common import REQUEST, WhatsAppCommon, mock_response

MISSING = {"error": {
    "message": "(#132001) Template name does not exist in the translation",
    "code": 132001,
    "error_data": {"details": "template name (welcome) does not exist in en"},
}}
SENT = {"messages": [{"id": "wamid.SENT"}]}


@tagged("post_install", "-at_install")
class TestMissingLanguage(WhatsAppCommon):
    """A language of a template that Meta does not know (error 132001): the message leaves at
    once in the main language of the template, the version is no longer chosen, and the account
    lists the versions to create at Meta."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Lang = cls.env["res.lang"]
        Lang._activate_lang("fr_FR")
        Lang._activate_lang("en_US")
        cls.account.company_id.partner_id.lang = "fr_FR"
        cls.manager = cls.env["res.users"].create({
            "name": "Manager Carine", "login": "wa_manager_lang", "lang": "en_US",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id,
                                  cls.env.ref("whatsapp_cloud.group_whatsapp_manager").id])],
        })
        cls.account.escalation_user_ids = cls.manager
        cls.english = cls.template.copy({
            "name": "Welcome (English)", "lang_code": "en", "body": "Hello {{1}}, your number {{2}} is registered.",
        })

    def payloads(self, request):
        return [call.kwargs["json"] for call in request.call_args_list]

    def test_sent_at_once_in_the_main_language(self):
        message = self.template._send(self.partner)
        self.assertEqual(message.template_id, self.english)
        with patch(REQUEST, side_effect=[mock_response(MISSING, status=404), mock_response(SENT)]) as request:
            message._send()
        refused, sent = self.payloads(request)
        self.assertEqual(refused["template"]["language"], {"code": "en"})
        # the same message, in French, with the same values
        self.assertEqual(sent["template"]["name"], "welcome")
        self.assertEqual(sent["template"]["language"], {"code": "fr"})
        self.assertEqual(sent["template"]["components"], refused["template"]["components"])
        self.assertEqual(message.state, "sent")
        self.assertEqual(message.wa_message_id, "wamid.SENT")
        self.assertEqual(message.template_id, self.template)
        self.assertEqual(message.replaced_template_id, self.english)
        self.assertEqual(message.body, "Bonjour Awa Ngono, votre numéro 6 70 00 00 00 est enregistré.")
        self.assertFalse(message.error)
        self.assertIn("Sent in French: the version in English does not exist at Meta", self.partner.message_ids[0].body)
        # the version is missing at Meta: no longer chosen, listed on the account, managers told
        self.assertEqual(self.english.status, "missing")
        self.assertIn("does not exist in en", self.english.rejected_reason)
        self.assertEqual(self.account.missing_template_ids, self.english)
        self.assertEqual(self.account.missing_template_count, 1)
        alert = self.account.message_ids[0]
        self.assertIn("the version in English does not exist at Meta", alert.body)
        self.assertIn("leave in French", alert.body)
        self.assertIn(self.manager.partner_id, alert.partner_ids)
        self.assertEqual(self.template._send(self.partner).template_id, self.template)
        # told once only
        self.english._mark_missing_at_meta(self.account, "again")
        self.assertEqual(self.account.message_ids[0], alert)

    def test_queued_message_switches_without_asking_meta(self):
        """Messages queued before the version was found missing (a whole batch): each one
        takes the main language before being sent, without a refusal of Meta for each."""
        message = self.template._send(self.partner)
        self.english.status = "missing"
        with patch(REQUEST, return_value=mock_response(SENT)) as request:
            message._send()
        (sent,) = self.payloads(request)
        self.assertEqual(sent["template"]["language"], {"code": "fr"})
        self.assertEqual((message.state, message.template_id), ("sent", self.template))

    def test_variant_of_the_same_language_first(self):
        """Another variant of the language of the customer before the main language; each
        version unknown at Meta is marked, the message goes on to the next one."""
        american = self.english.copy({"name": "Welcome (US)", "lang_code": "en_US"})
        message = self.template._send(self.partner)
        self.assertEqual(message.template_id, american)
        answers = [mock_response(MISSING, status=404), mock_response(MISSING, status=404), mock_response(SENT)]
        with patch(REQUEST, side_effect=answers) as request:
            message._send()
        languages = [payload["template"]["language"]["code"] for payload in self.payloads(request)]
        self.assertEqual(languages, ["en_US", "en", "fr"])
        self.assertEqual((message.state, message.template_id), ("sent", self.template))
        self.assertEqual(message.replaced_template_id, american)
        self.assertEqual((american | self.english).mapped("status"), ["missing", "missing"])

    def test_approved_version_first(self):
        self.english.status = "missing"
        spanish = self.template.copy({"name": "Bienvenida", "lang_code": "es"})
        spanish.status = "approved"
        self.assertEqual(self.english._get_fallback_version(self.account), self.template)
        self.template.status = "pending"
        self.assertEqual(self.english._get_fallback_version(self.account), spanish)

    def test_no_other_language(self):
        self.english.unlink()
        self.partner.lang = "fr_FR"
        message = self.template._send(self.partner)
        with patch(REQUEST, return_value=mock_response(MISSING, status=404)):
            message._send()
        self.assertEqual(message.state, "failed")
        self.assertEqual(message.error_code, 132001)
        self.assertIn("no other language of it can take this message", message.error)
        self.assertIn("Health tab", message.error_help)
        self.assertEqual(self.template.status, "missing")
        # the next messages are not sent at all, and say why
        later = self.template._send(self.partner)
        self.assertEqual(later.state, "skipped")
        self.assertIn("does not exist at Meta", later.error)

    def test_other_variables_not_mixed(self):
        """A version that does not take the same variables cannot replace the missing one."""
        self.template.body = "Bonjour {{1}}."
        self.template.variable_ids[1:].unlink()
        message = self.template._send(self.partner)
        with patch(REQUEST, return_value=mock_response(MISSING, status=404)) as request:
            message._send()
        self.assertEqual(request.call_count, 1)
        self.assertEqual(message.state, "failed")

    def test_named_variables_header_and_link(self):
        for template in self.template | self.english:
            template.variable_ids.unlink()
        self.template.write({
            "parameter_format": "named", "body": "Bonjour {{customer}}, à {{city}}.",
            "header_type": "text", "header_text": "Commande {{1}}", "header_value": "{{ object.ref }}",
            "button_url_value": "{{ ctx.get('path') }}",
            "button_ids": [(0, 0, {"button_type": "url", "name": "Suivre", "url": "https://shop.example.com/{{1}}"})],
        })
        self.english.write({
            "parameter_format": "named", "body": "Hello {{city}}, {{customer}}.",
            "header_type": "text", "header_text": "Order {{1}}", "header_value": "{{ object.ref }}",
            "button_url_value": "{{ ctx.get('path') }}",
            "button_ids": [(0, 0, {"button_type": "url", "name": "Follow", "url": "https://shop.example.com/{{1}}"})],
        })
        for template in self.template | self.english:
            template._sync_variables()
            template.variable_ids.filtered(lambda v: v.param_name == "customer").value = "{{ object.name }}"
            template.variable_ids.filtered(lambda v: v.param_name == "city").value = "{{ ctx.get('city') }}"
        self.partner.ref = "S042"
        # values given by the code (ctx) that the message keeps
        message = self.template.with_context(city="Douala", path="o/42?t=a b")._send(self.partner)
        self.assertEqual(message.template_id, self.english)
        with patch(REQUEST, side_effect=[mock_response(MISSING, status=404), mock_response(SENT)]) as request:
            message._send()
        sent = self.payloads(request)[1]["template"]
        self.assertEqual(sent["language"], {"code": "fr"})
        self.assertEqual(sent["components"], [
            {"type": "header", "parameters": [{"type": "text", "text": "S042"}]},
            {"type": "body", "parameters": [
                {"type": "text", "text": "Awa Ngono", "parameter_name": "customer"},
                {"type": "text", "text": "Douala", "parameter_name": "city"},
            ]},
            {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": "o/42?t=a%20b"}]},
        ])
        self.assertEqual(message.body, "Bonjour Awa Ngono, à Douala.")

    def test_conversation_shows_the_text_sent(self):
        channel = self.env["whatsapp.message"]._process_incoming(self.account, {
            "from": "237670000000", "id": "wamid.IN1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Hello"},
        }, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}]).channel_id
        message = self.template.with_context(whatsapp_channel_id=channel.id)._send(self.partner)
        self.assertIn("Hello Awa Ngono", message.mail_message_id.body)
        with patch(REQUEST, side_effect=[mock_response(MISSING, status=404), mock_response(SENT)]):
            message._send()
        body = message.mail_message_id.body
        self.assertIn("Bonjour Awa Ngono", body)
        self.assertNotIn("Hello Awa Ngono", body)
        self.assertIn("Template: Welcome", body)
        self.assertIn("Sent in French: the version in English does not exist at Meta.", body)
        self.assertEqual(message.state, "sent")

    def test_synchronisation_finds_the_missing_versions(self):
        others = self.env["whatsapp.template"].search([("id", "not in", (self.template | self.english).ids)])
        others.action_archive()
        meta = [{
            "id": "301", "name": "welcome", "language": "fr", "status": "APPROVED",
            "components": [{"type": "BODY", "text": "Bonjour {{1}}, votre numéro {{2}} est enregistré."}],
        }]
        with patch(REQUEST, return_value=mock_response({"data": meta})):
            action = self.account.action_sync_templates()
        self.assertEqual(self.template.status, "approved")
        self.assertEqual(self.english.status, "missing")
        self.assertEqual(action["params"]["type"], "warning")
        self.assertIn("1 template version does not exist at Meta", action["params"]["message"])
        self.assertEqual(self.template._send(self.partner).template_id, self.template)
        # created at Meta in English: chosen again after the next synchronisation
        meta.append({
            "id": "302", "name": "welcome", "language": "en", "status": "APPROVED",
            "components": [{"type": "BODY", "text": "Hello {{1}}, your number {{2}} is registered."}],
        })
        with patch(REQUEST, return_value=mock_response({"data": meta})):
            action = self.account.action_sync_templates()
        self.assertEqual(self.english.status, "approved")
        self.assertFalse(self.account.missing_template_ids)
        self.assertEqual(action["params"]["type"], "success")
        self.assertEqual(self.template._send(self.partner).template_id, self.english)

    def test_synchronisation_of_another_business_account(self):
        """The templates of no account are not marked by an account whose WhatsApp Business
        account is not the only one: the other one may have them."""
        self.env["whatsapp.account"].create({
            "name": "Other", "phone_number_id": "1119999", "waba_id": "9999", "access_token": "t",
        })
        shared = self.template.copy({"account_id": False, "template_name": "shared"})
        with patch(REQUEST, return_value=mock_response({"data": []})):
            self.account.action_sync_templates()
        self.assertEqual(shared.status, "unknown")
        self.assertEqual(self.english.status, "missing")

    def test_submit_the_missing_versions(self):
        self.english.write({"status": "missing", "wa_template_id": "deleted-at-meta"})
        with patch(REQUEST, return_value=mock_response({"id": "777", "category": "UTILITY"})) as request:
            result = self.account.action_submit_missing_templates()
        method, url = request.call_args.args
        self.assertEqual((method, url), ("POST", "https://graph.facebook.com/v26.0/2220002/message_templates"))
        self.assertEqual(request.call_args.kwargs["json"]["language"], "en")
        self.assertEqual((self.english.status, self.english.wa_template_id), ("pending", "777"))
        self.assertEqual(result["params"]["type"], "success")
        self.assertFalse(self.account.missing_template_ids)
