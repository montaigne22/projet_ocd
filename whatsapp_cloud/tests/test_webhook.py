import hashlib
import hmac
import json

from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import WhatsAppCommon


@tagged("post_install", "-at_install")
class TestWhatsAppWebhook(HttpCase, WhatsAppCommon):

    def _post(self, payload, secret="test-secret"):
        """Call the webhook as Meta, then process the stored notifications (done by a
        scheduled action triggered at once)."""
        body = json.dumps(payload).encode()
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        response = self.url_open("/whatsapp/webhook", data=body, headers={
            "Content-Type": "application/json", "X-Hub-Signature-256": signature,
        })
        self.env["whatsapp.webhook.event"]._process_pending()
        return response

    def _payload(self, value):
        return {"object": "whatsapp_business_account", "entry": [{
            "id": "2220002",
            "changes": [{"field": "messages", "value": {
                "messaging_product": "whatsapp",
                "metadata": {"phone_number_id": "1110001"},
                **value,
            }}],
        }]}

    def test_verification(self):
        response = self.url_open(
            "/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=test-verify-token"
            "&hub.challenge=1158201444"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "1158201444")
        response = self.url_open(
            "/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=1"
        )
        self.assertEqual(response.status_code, 403)

    def test_receipts(self):
        message = self.template._send(self.partner)
        message.write({"state": "sent", "wa_message_id": "wamid.ABC"})
        delivered = self._payload({"statuses": [
            {"id": "wamid.ABC", "status": "delivered", "timestamp": "1760000000",
             "recipient_id": "237670000000"},
        ]})
        self.assertEqual(self._post(delivered, secret="wrong").status_code, 403)
        self.assertEqual(message.state, "sent")
        self.assertEqual(self._post(delivered).status_code, 200)
        self.assertEqual(message.state, "delivered")
        self.assertTrue(message.delivered_date)
        read = self._payload({"statuses": [
            {"id": "wamid.ABC", "status": "read", "timestamp": "1760000100"},
        ]})
        self._post(read)
        self._post(delivered)  # late receipt: the message stays read
        self.assertEqual(message.state, "read")

    def test_failed_receipt(self):
        message = self.template._send(self.partner)
        message.write({"state": "sent", "wa_message_id": "wamid.DEF"})
        self._post(self._payload({"statuses": [{
            "id": "wamid.DEF", "status": "failed", "timestamp": "1760000000",
            "errors": [{"code": 131026, "title": "Message undeliverable"}],
        }]}))
        self.assertEqual(message.state, "failed")
        self.assertEqual(message.error, "Message undeliverable")

    def test_reply_and_stop(self):
        contacts = [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}]
        self._post(self._payload({"contacts": contacts, "messages": [{
            "from": "237670000000", "id": "wamid.IN1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Merci, à quelle heure ?"},
        }]}))
        incoming = self.env["whatsapp.message"].search([("wa_message_id", "=", "wamid.IN1")])
        self.assertEqual(incoming.partner_id, self.partner)
        self.assertEqual(incoming.state, "received")
        self.assertEqual(incoming.channel_id.whatsapp_partner_id, self.partner)
        self.assertIn("à quelle heure", incoming.mail_message_id.body)
        # Meta sends the notification again: the message is not duplicated
        self._post(self._payload({"contacts": contacts, "messages": [{
            "from": "237670000000", "id": "wamid.IN1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Merci, à quelle heure ?"},
        }]}))
        self.assertEqual(
            self.env["whatsapp.message"].search_count([("wa_message_id", "=", "wamid.IN1")]), 1
        )
        self.assertTrue(self.partner.whatsapp_opt_in)
        self._post(self._payload({"contacts": contacts, "messages": [{
            "from": "237670000000", "id": "wamid.IN2", "timestamp": "1760000001",
            "type": "text", "text": {"body": "STOP"},
        }]}))
        self.assertFalse(self.partner.whatsapp_opt_in)
        self.assertTrue(self.partner.whatsapp_opt_out)

    def test_two_numbers_of_the_same_business_account(self):
        second = self.env["whatsapp.account"].create({
            "name": "Shop Yaoundé",
            "phone_number_id": "1110002",
            "waba_id": "2220002",
            "access_token": "test-token",
            "app_secret": "test-secret",
        })
        payload = self._payload({
            "contacts": [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}],
            "messages": [{"from": "237670000000", "id": "wamid.Y1", "timestamp": "1760000000",
                          "type": "text", "text": {"body": "Bonjour Yaoundé"}}],
        })
        payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] = "1110002"
        self._post(payload)
        message = self.env["whatsapp.message"].search([("wa_message_id", "=", "wamid.Y1")])
        self.assertEqual(message.account_id, second)
        self.assertEqual(message.channel_id.whatsapp_account_id, second)

    def test_events_kept_when_processing_fails(self):
        with patch(
            "odoo.addons.whatsapp_cloud.models.whatsapp_message.WhatsappMessage._process_status",
            side_effect=ValueError("boom"),
        ):
            self._post(self._payload({"statuses": [{"id": "wamid.X", "status": "sent"}]}))
        event = self.env["whatsapp.webhook.event"].search([], order="id desc", limit=1)
        self.assertEqual((event.state, event.attempts, event.error), ("pending", 1, "boom"))
        self.env["whatsapp.webhook.event"]._process_pending()
        self.assertEqual(event.state, "done")

    def test_template_status_webhook(self):
        self.template.wa_template_id = "1689556908129835"
        payload = {"object": "whatsapp_business_account", "entry": [{
            "id": "2220002",
            "changes": [{"field": "message_template_status_update", "value": {
                "event": "REJECTED",
                "message_template_id": 1689556908129835,
                "message_template_name": "welcome",
                "message_template_language": "fr",
                "reason": "INVALID_FORMAT",
                "rejection_info": {"reason": "Parameters next to each other."},
            }}],
        }]}
        self._post(payload)
        self.assertEqual(self.template.status, "rejected")
        self.assertIn("Parameters next to each other.", self.template.rejected_reason)
