import json
from unittest.mock import patch

import requests

from odoo.tests import tagged

from odoo.addons.whatsapp_cloud import const

from .common import REQUEST, WhatsAppCommon, mock_response


@tagged("post_install", "-at_install")
class TestWhatsAppCloud(WhatsAppCommon):

    def test_normalize_numbers(self):
        Partner = self.env["res.partner"]
        france = self.env.ref("base.fr")
        for number, country, expected in [
            ("6 70 00 00 00", self.cameroon, "237670000000"),
            ("670000000", self.cameroon, "237670000000"),
            ("+237 6 70 00 00 00", self.cameroon, "237670000000"),
            ("00237670000000", self.cameroon, "237670000000"),
            ("237670000000", self.cameroon, "237670000000"),
            ("06 12 34 56 78", france, "33612345678"),
            ("12", self.cameroon, False),
            (False, self.cameroon, False),
        ]:
            with self.subTest(number=number):
                self.assertEqual(Partner._whatsapp_normalize_number(number, country), expected)
        self.assertEqual(self.partner._whatsapp_number(), "237670000000")

    def test_send_template(self):
        message = self.template._send(self.partner)
        self.assertEqual(message.state, "queued")
        self.assertEqual(message.phone, "237670000000")
        self.assertEqual(message.body, "Bonjour Awa Ngono, votre numéro 6 70 00 00 00 est enregistré.")
        answer = {"messages": [{"id": "wamid.TEST1"}]}
        with patch(REQUEST, return_value=mock_response(answer)) as request:
            message._send()
        method, url = request.call_args.args
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://graph.facebook.com/v26.0/1110001/messages")
        self.assertEqual(
            request.call_args.kwargs["headers"], {"Authorization": "Bearer test-token"}
        )
        self.assertEqual(request.call_args.kwargs["json"], {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "+237670000000",
            "type": "template",
            "template": {
                "name": "welcome",
                "language": {"code": "fr"},
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "Awa Ngono"},
                        {"type": "text", "text": "6 70 00 00 00"},
                    ],
                }],
            },
        })
        self.assertEqual(message.state, "sent")
        self.assertEqual(message.wa_message_id, "wamid.TEST1")
        self.assertTrue(message.sent_date)
        self.assertIn("Awa Ngono", self.partner.message_ids[0].body)

    def test_named_parameters_and_button(self):
        self.template.write({
            "parameter_format": "named",
            "body": "Bonjour {{customer}}",
            "button_url_value": "/my/orders/{{ object.id }}",
        })
        self.template.variable_ids.unlink()
        self.template._sync_variables()
        self.template.variable_ids.value = "{{ object.name }}"
        message = self.template._send(self.partner)
        components = json.loads(message.sudo().payload)["template"]["components"]
        self.assertEqual(components[0]["parameters"], [
            {"type": "text", "text": "Awa Ngono", "parameter_name": "customer"},
        ])
        self.assertEqual(components[1], {
            "type": "button", "sub_type": "url", "index": "0",
            "parameters": [{"type": "text", "text": f"/my/orders/{self.partner.id}"}],
        })

    def test_end_of_the_url_of_the_link_button(self):
        self.template.write({
            "status": "approved",
            "button_url_dynamic": True,
            "button_url_value": "/my/orders/{{ object.id }}?access_token=a b:c",
            "button_ids": [(0, 0, {
                "button_type": "url", "name": "Suivre ma commande", "url": "https://shop.example.com/{{1}}",
            })],
        })

        def button_text():
            payload = json.loads(self.template._send(self.partner).sudo().payload)
            return payload["template"]["components"][1]["parameters"][0]["text"]

        # no double slash, special characters percent-encoded (documentation of Meta)
        self.assertEqual(button_text(), f"my/orders/{self.partner.id}?access_token=a%20b%3Ac")
        # template created at Meta with the variable glued to the domain name
        self.template.button_ids.url = "https://shop.example.com{{1}}"
        self.assertEqual(button_text(), f"/my/orders/{self.partner.id}?access_token=a%20b%3Ac")

    def test_send_in_the_language_of_the_contact(self):
        Lang = self.env["res.lang"]
        Lang._activate_lang("fr_FR")
        Lang._activate_lang("en_US")
        english_version = self.template.copy({
            "name": "Welcome (English)",
            "lang_code": "en",
            "body": "Hello {{1}}, your number is {{2}}.",
        })
        self.partner.lang = "fr_FR"
        english = self.partner.copy({"name": "John Doe", "lang": "en_US", "whatsapp_opt_in": True})
        no_language = self.partner.copy({"name": "Ali", "lang": False, "whatsapp_opt_in": True})
        messages = self.template._send(self.partner | english | no_language)
        by_partner = {message.partner_id: message for message in messages}
        self.assertEqual(by_partner[self.partner].template_id, self.template)
        self.assertEqual(by_partner[no_language].template_id, self.template)
        self.assertEqual(by_partner[english].template_id, english_version)
        self.assertEqual(by_partner[english].body, "Hello John Doe, your number is 6 70 00 00 00.")
        payload = json.loads(by_partner[english].sudo().payload)
        self.assertEqual(payload["template"]["language"], {"code": "en"})
        # a version refused by Meta is not used
        english_version.status = "rejected"
        self.assertEqual(self.template._send(english).template_id, self.template)
        # this template approved: a version not synchronised yet (maybe not submitted to Meta)
        # is not used, an approved one is
        self.template.status = "approved"
        english_version.status = "unknown"
        self.assertEqual(self.template._send(english).template_id, self.template)
        english_version.status = "approved"
        self.assertEqual(self.template._send(english).template_id, english_version)

    def test_sync_template_of_a_module_in_a_language_variant(self):
        Template = self.env["whatsapp.template"].with_context(active_test=False)
        Template.search([("template_name", "=", "provided")]).unlink()
        provided = Template.create({
            "name": "Provided by a module", "template_name": "provided", "lang_code": "en",
            "body": "Hello {{1}}",
        })
        answer = {"data": [{
            "name": "provided", "language": "en_US", "status": "APPROVED",
            "components": [{"type": "BODY", "text": "Hello {{1}}"}],
        }]}
        with patch(REQUEST, return_value=mock_response(answer)):
            self.account.action_sync_templates()
        self.assertEqual(Template.search([("template_name", "=", "provided")]), provided)
        self.assertEqual(provided.lang_code, "en_US")
        self.assertEqual(provided.status, "approved")

    def test_button_only_when_meta_expects_it(self):
        self.template.write({"button_url_value": "/my/{{ object.id }}", "status": "approved"})

        def components(message):
            return json.loads(message.sudo().payload)["template"]["components"]

        # synchronised, static link button (or none) at Meta: no URL variable sent
        types = [component["type"] for component in components(self.template._send(self.partner))]
        self.assertEqual(types, ["body"])
        # link button ending with a variable at Meta
        self.template.button_url_dynamic = True
        button = components(self.template._send(self.partner))[1]
        self.assertEqual(button["parameters"], [{"type": "text", "text": f"/my/{self.partner.id}"}])
        # ... but nothing to put in it: not sent, Meta would refuse it
        self.template.button_url_value = "{{ '' }}"
        message = self.template._send(self.partner)
        self.assertEqual(message.state, "skipped")
        self.assertIn("link button", message.error)

    def test_parameters_cleaned(self):
        self.partner.street = "Akwa\n\tFace   pharmacie"
        self.template.variable_ids[1].value = "{{ object.street }}"
        message = self.template._send(self.partner)
        parameters = json.loads(message.sudo().payload)["template"]["components"][0]["parameters"]
        self.assertEqual(parameters[1]["text"], "Akwa Face pharmacie")
        self.template.variable_ids[1].value = False
        message = self.template._send(self.partner)
        parameters = json.loads(message.sudo().payload)["template"]["components"][0]["parameters"]
        self.assertEqual(parameters[1]["text"], "-")

    def test_opt_in(self):
        other = self.partner.copy({"name": "Paul Mbarga", "whatsapp_opt_in": False})
        with patch(REQUEST) as request:
            message = self.template._send(other)
            message._send()
        request.assert_not_called()
        self.assertEqual(message.state, "skipped")
        self.assertIn("did not agree", message.error)
        self.account.require_opt_in = False
        self.assertEqual(self.template._send(other).state, "queued")

    def test_opt_out(self):
        self.assertFalse(self.partner.whatsapp_opt_out)
        self.partner.whatsapp_opt_in = False
        self.assertTrue(self.partner.whatsapp_opt_out)
        self.partner.whatsapp_opt_in = True
        self.assertFalse(self.partner.whatsapp_opt_out)
        never_asked = self.env["res.partner"].create({"name": "Paul"})
        self.assertFalse(never_asked.whatsapp_opt_in or never_asked.whatsapp_opt_out)
        refused = self.env["res.partner"].create({"name": "Marie", "whatsapp_opt_in": False})
        self.assertTrue(refused.whatsapp_opt_out)

    def test_no_number(self):
        self.partner.phone = False
        message = self.template._send(self.partner)
        self.assertEqual(message.state, "skipped")

    def test_meta_error(self):
        message = self.template._send(self.partner)
        error = {"error": {
            "message": "(#132001) Template name does not exist in the translation",
            "code": 132001,
            "error_data": {"details": "template name (welcome) does not exist in fr"},
        }}
        with patch(REQUEST, return_value=mock_response(error, status=404)):
            message._send()
        self.assertEqual(message.state, "failed")
        self.assertIn("does not exist in fr", message.error)
        self.assertIn("not sent", self.partner.message_ids[0].body)

    def test_retry_when_meta_does_not_answer(self):
        message = self.template._send(self.partner)
        with patch(REQUEST, side_effect=requests.exceptions.ConnectionError("timeout")):
            for _attempt in range(4):
                message._send()
                self.assertEqual(message.state, "queued")
            message._send()
        self.assertEqual(message.attempts, 5)
        self.assertEqual(message.state, "failed")
        message.action_retry()
        self.assertEqual((message.state, message.attempts), ("queued", 0))

    def test_document_header(self):
        self.template.header_type = "document"
        message = self.template._send(self.partner)
        message.attachment_id = self.env["ir.attachment"].create({
            "name": "S00042.pdf", "raw": b"%PDF-1.4", "mimetype": "application/pdf",
        })
        answers = [
            mock_response({"id": "media-1"}),
            mock_response({"messages": [{"id": "wamid.2"}]}),
        ]
        with patch(REQUEST, side_effect=answers) as request:
            message._send()
        upload, send = request.call_args_list
        self.assertEqual(upload.args[1], "https://graph.facebook.com/v26.0/1110001/media")
        self.assertEqual(upload.kwargs["files"]["file"][0], "S00042.pdf")
        header = send.kwargs["json"]["template"]["components"][0]
        self.assertEqual(header, {"type": "header", "parameters": [
            {"type": "document", "document": {"id": "media-1", "filename": "S00042.pdf"}},
        ]})
        self.assertEqual(message.state, "sent")

    def test_document_header_made_when_sent(self):
        """The flow that queues a message never waits for its PDF: it is made when the message
        is sent; when it cannot be made, the message says why, is tried again, then fails."""
        report = self.env["ir.actions.report"].search([("report_type", "=", "qweb-pdf")], limit=1)
        self.template.write({"header_type": "document", "header_report_id": report.id})
        message = self.template._send(self.partner)
        self.assertEqual(message.state, "queued")
        self.assertFalse(message.attachment_id)
        Template = type(self.template)
        with patch.object(Template, "_render_document", side_effect=ValueError("engine down")), \
                patch(REQUEST) as request:
            message._send()
            self.assertEqual(message.state, "queued", "Tried again by the next sending")
            self.assertIn("engine down", message.error)
            request.assert_not_called()
            message.attempts = const.MAX_ATTEMPTS - 1
            message._send()
            self.assertEqual(message.state, "failed")
        message.write({"state": "queued", "attempts": 0, "error": False})
        pdf = self.env["ir.attachment"].create({"name": "S00042.pdf", "raw": b"%PDF-1.4", "mimetype": "application/pdf"})
        answers = [mock_response({"id": "media-1"}), mock_response({"messages": [{"id": "wamid.9"}]})]
        with patch.object(Template, "_render_document", return_value=pdf), patch(REQUEST, side_effect=answers):
            message._send()
        self.assertEqual(message.state, "sent")
        self.assertEqual(message.attachment_id, pdf)

    def test_server_action(self):
        action = self.env["ir.actions.server"].create({
            "name": "Welcome on WhatsApp",
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "state": "whatsapp",
            "whatsapp_template_id": self.template.id,
        })
        action.with_context(active_model="res.partner", active_ids=self.partner.ids).run()
        message = self.env["whatsapp.message"].search([("partner_id", "=", self.partner.id)])
        self.assertEqual(message.state, "queued")
        self.assertEqual(message.res_id, self.partner.id)

    def test_cron(self):
        message = self.template._send(self.partner)
        answer = mock_response({"messages": [{"id": "wamid.3"}]})
        with patch(REQUEST, return_value=answer), \
                patch.object(type(self.env["ir.cron"]), "_commit_progress", return_value=60):
            self.env["whatsapp.message"]._cron_send_queued()
        self.assertEqual(message.state, "sent")

    def test_composer(self):
        composer = self.env["whatsapp.composer"].with_context(
            active_model="res.partner", active_ids=self.partner.ids
        ).create({"template_id": self.template.id})
        self.assertEqual(composer.preview, "Bonjour Awa Ngono, votre numéro 6 70 00 00 00 est enregistré.")
        self.assertEqual(composer.recipient, "Awa Ngono (+237670000000)")
        self.assertFalse(composer.warning)
        composer.action_send()
        self.assertEqual(self.partner.whatsapp_message_count, 1)

    def test_authentication_template(self):
        template = self.env["whatsapp.template"].create({
            "name": "Login code",
            "template_name": "login_code",
            "lang_code": "fr",
            "category": "authentication",
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "account_id": self.account.id,
            "body": "Votre code est {{1}}.",
        })
        template.variable_ids.value = "{{ ctx.get('code') }}"
        # Submitted without a text: Meta writes it, with the time of the code and the button
        # that copies the code (a text here is refused: "unexpected field text")
        answer = {"id": "999", "status": "PENDING", "category": "AUTHENTICATION"}
        with patch(REQUEST, return_value=mock_response(answer)) as request:
            template.action_submit_to_meta()
        self.assertEqual(request.call_args.kwargs["json"]["components"], [
            {"type": "BODY", "add_security_recommendation": True},
            {"type": "FOOTER", "code_expiration_minutes": 10},
            {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]},
        ])
        # Sent: the code in the text and in the button that copies it
        template.status = "approved"
        message = template.with_context(code="482913")._send(self.partner)
        self.assertEqual(json.loads(message.payload)["template"]["components"], [
            {"type": "body", "parameters": [{"type": "text", "text": "482913"}]},
            {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": "482913"}]},
        ])
        # Read again from Meta: the time of the code is kept, the button is not stored
        vals = template._prepare_vals_from_meta({
            "name": "login_code", "language": "fr", "status": "APPROVED", "category": "AUTHENTICATION",
            "components": [
                {"type": "BODY", "text": "*{{1}}* est votre code de vérification.", "add_security_recommendation": True},
                {"type": "FOOTER", "text": "Ce code expire dans 5 minutes.", "code_expiration_minutes": 5},
                {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE", "text": "Copier le code"}]},
            ],
        })
        self.assertEqual(vals["code_expiration_minutes"], 5)
        self.assertEqual(len(vals["button_ids"]), 1, "Only the command that clears the buttons")
        template.write(vals)
        self.assertFalse(template.button_ids)
        with patch(REQUEST, return_value=mock_response({"success": True})) as request:
            template.action_submit_to_meta()
        self.assertEqual(request.call_args.kwargs["json"]["components"][1], {"type": "FOOTER", "code_expiration_minutes": 5})

    def test_sync_templates(self):
        Template = self.env["whatsapp.template"].with_context(active_test=False)
        Template.search([("template_name", "in", ["order_confirmed", "provided"])]).unlink()
        provided = Template.create({
            "name": "Provided by a module",
            "template_name": "provided",
            "lang_code": "fr",
            "body": "Bonjour {{1}}",
        })
        answer = {"data": [{
            "name": "order_confirmed",
            "language": "fr",
            "status": "APPROVED",
            "category": "UTILITY",
            "components": [
                {"type": "HEADER", "format": "DOCUMENT"},
                {"type": "BODY", "text": "Bonjour {{1}}, votre commande {{2}} est confirmée."},
                {"type": "BUTTONS", "buttons": [
                    {"type": "URL", "text": "Suivre ma commande", "url": "https://shop.example.com{{1}}"},
                ]},
            ],
        }, {
            "name": "provided",
            "language": "fr",
            "status": "PAUSED",
            "components": [{"type": "BODY", "text": "Bonjour {{1}}"}],
        }], "paging": {"cursors": {"after": "X"}}}
        with patch(REQUEST, return_value=mock_response(answer)) as request:
            self.account.action_sync_templates()
        self.assertEqual(
            request.call_args.args[1],
            "https://graph.facebook.com/v26.0/2220002/message_templates",
        )
        template = Template.search([("template_name", "=", "order_confirmed")])
        self.assertEqual(template.account_id, self.account)
        self.assertEqual(template.status, "approved")
        self.assertEqual(template.header_type, "document")
        self.assertEqual(template.variable_ids.mapped("placeholder"), ["{{1}}", "{{2}}"])
        self.assertTrue(template.button_url_dynamic)
        # The template provided by a module is updated, not duplicated.
        self.assertEqual(Template.search([("template_name", "=", "provided")]), provided)
        self.assertEqual(provided.status, "paused")
        self.assertFalse(provided.button_url_dynamic)
        with patch(REQUEST, return_value=mock_response(answer)):
            self.account.action_sync_templates()
        self.assertEqual(Template.search_count([("template_name", "=", "order_confirmed")]), 1)

    def test_sync_keeps_the_text_of_a_refused_template(self):
        """Refused by Meta: the text of Odoo is the one being corrected, the synchronisation
        reads only the decision of Meta."""
        self.template.write({"wa_template_id": "777", "status": "pending"})
        answer = {"data": [{
            "id": "777", "name": "welcome", "language": "fr", "status": "REJECTED",
            "rejected_reason": "INVALID_FORMAT", "category": "UTILITY",
            "components": [{"type": "BODY", "text": "Old text {{1}} refused"}],
        }]}
        with patch(REQUEST, return_value=mock_response(answer)):
            self.account.action_sync_templates()
        self.assertEqual((self.template.status, self.template.rejected_reason), ("rejected", "INVALID_FORMAT"))
        self.assertEqual(self.template.body, "Bonjour {{1}}, votre numéro {{2}} est enregistré.")

    def test_decision_of_meta_read_without_the_webhook(self):
        """Every half hour, the templates waiting for Meta get its decision and the reason of a
        refusal; the managers are told about a refusal. The text stays as submitted."""
        Template = self.env["whatsapp.template"]
        other = self.template.copy({"template_name": "welcome_two", "wa_template_id": "778", "status": "pending"})
        self.template.write({"wa_template_id": "777", "status": "pending"})
        answers = {
            "777": {"status": "REJECTED", "rejected_reason": "TAG_CONTENT_MISMATCH"},
            "778": {"status": "PENDING", "rejected_reason": "NONE"},
        }

        def meta(method, url, **kwargs):
            self.assertEqual(kwargs["params"]["fields"], "status,rejected_reason,quality_score")
            return mock_response(answers[url.rsplit("/", 1)[-1]])

        with patch(REQUEST, side_effect=meta):
            Template._cron_read_pending_from_meta()
        self.assertEqual((self.template.status, self.template.rejected_reason), ("rejected", "TAG_CONTENT_MISMATCH"))
        self.assertEqual(self.template.body, "Bonjour {{1}}, votre numéro {{2}} est enregistré.")
        self.assertEqual(other.status, "pending", "Still under review")
        self.assertIn("TAG_CONTENT_MISMATCH", self.account.message_ids[:1].body)
        # Approved later; Meta out of reach: nothing changes, nothing breaks
        answers["778"] = {"status": "APPROVED"}
        with patch(REQUEST, side_effect=meta):
            Template._cron_read_pending_from_meta()
        self.assertEqual((other.status, other.rejected_reason), ("approved", False))
        other.status = "pending"
        with patch(REQUEST, return_value=mock_response({"error": {"message": "Unavailable"}}, status=503)):
            Template._cron_read_pending_from_meta()
        self.assertEqual(other.status, "pending")
