import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.whatsapp_cloud.tests.common import REQUEST, mock_response

from .common import WhatsAppCallCommon


@tagged("post_install", "-at_install")
class TestCallPermission(WhatsAppCallCommon):
    """The customer allows the company to call them (phase 2: the company calls)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].sudo()._whatsapp_get_or_create(
            cls.account, "237670000000", None, cls.partner
        )

    def setUp(self):
        super().setUp()
        self.channel.whatsapp_channel_valid_until = fields.Datetime.now() + timedelta(hours=20)

    def permissions(self, status="no_permission", can_ask=True, expiration=None):
        permission = {"status": status}
        if expiration:
            permission["expiration_time"] = expiration
        return mock_response({
            "messaging_product": "whatsapp",
            "permission": permission,
            "actions": [
                {"action_name": "send_call_permission_request", "can_perform_action": can_ask},
                {"action_name": "start_call", "can_perform_action": status != "no_permission"},
            ],
        })

    def reply(self, wamid, response, **extra):
        event = self.env["whatsapp.webhook.event"].create({
            "account_id": self.account.id,
            "field": "messages",
            "payload": json.dumps({
                "metadata": {"phone_number_id": self.account.phone_number_id},
                "messages": [{
                    "from": "237670000000", "id": wamid, "timestamp": "1795000000",
                    "type": "interactive",
                    "interactive": {"type": "call_permission_reply", "call_permission_reply": {
                        "response": response, **extra,
                    }},
                }],
            }),
        })
        event._process()

    def test_ask_to_call(self):
        channel = self.channel.with_user(self.agent)
        with patch(REQUEST, return_value=self.permissions()) as request:
            channel.whatsapp_action_call_permission_request()
        get = request.call_args_list[0]
        self.assertEqual(get.args, ("GET", "https://graph.facebook.com/v26.0/1110001/call_permissions"))
        self.assertEqual(get.kwargs["params"], {"user_wa_id": "237670000000"})
        sent = self.env["whatsapp.message"].search([
            ("channel_id", "=", self.channel.id), ("direction", "=", "outgoing"),
        ], order="id desc", limit=1)
        payload = json.loads(sent.payload)
        self.assertEqual(payload["type"], "interactive")
        self.assertEqual(payload["interactive"]["type"], "call_permission_request")
        self.assertEqual(payload["interactive"]["action"], {"name": "call_permission_request"})
        self.assertIn("call you on WhatsApp", payload["interactive"]["body"]["text"])
        self.assertEqual(self.channel.whatsapp_call_permission, "requested")
        self.assertTrue(self.channel.whatsapp_call_permission_asked)

    def test_ask_limits_and_window(self):
        channel = self.channel.with_user(self.agent)
        with patch(REQUEST, return_value=self.permissions(can_ask=False)), self.assertRaises(UserError):
            channel.whatsapp_action_call_permission_request()
        self.channel.whatsapp_channel_valid_until = fields.Datetime.now() - timedelta(hours=1)
        with self.assertRaises(UserError):
            channel.whatsapp_action_call_permission_request()

    def test_already_allowed(self):
        """Meta says the customer allows the calls already (they called): nothing is sent."""
        until = int((datetime.now(UTC) + timedelta(days=5)).timestamp())
        count = self.env["whatsapp.message"].search_count([("channel_id", "=", self.channel.id)])
        with patch(REQUEST, return_value=self.permissions("temporary", expiration=until)):
            self.channel.with_user(self.agent).whatsapp_action_call_permission_request()
        self.assertEqual(self.env["whatsapp.message"].search_count([("channel_id", "=", self.channel.id)]), count)
        self.assertEqual(self.channel.whatsapp_call_permission, "temporary")
        self.assertTrue(self.channel._whatsapp_call_allowed())

    def test_answers_of_the_customer(self):
        until = int((datetime.now(UTC) + timedelta(days=7)).timestamp())
        messages = self.env["whatsapp.message"].search_count([("direction", "=", "incoming")])
        self.reply("wamid.P1", "accept", is_permanent=False, expiration_timestamp=str(until),
                   response_source="user_action")
        self.assertEqual(self.channel.whatsapp_call_permission, "temporary")
        self.assertEqual(self.channel.whatsapp_call_permission_until,
                         datetime.fromtimestamp(until, UTC).replace(tzinfo=None))
        self.assertTrue(self.channel._whatsapp_call_allowed())
        # not a message of the customer: no answer expected from the team, no bot
        self.assertEqual(self.env["whatsapp.message"].search_count([("direction", "=", "incoming")]), messages)
        notices = self.channel.message_ids.filtered(lambda m: "until" in (m.body or ""))
        self.assertEqual(len(notices), 1)
        # the same notification again (not acknowledged): noted once
        self.reply("wamid.P1", "accept", is_permanent=False, expiration_timestamp=str(until),
                   response_source="user_action")
        self.assertEqual(len(self.channel.message_ids.filtered(lambda m: "until" in (m.body or ""))), 1)
        self.reply("wamid.P2", "accept", is_permanent=True, response_source="user_action")
        self.assertEqual(self.channel.whatsapp_call_permission, "permanent")
        self.reply("wamid.P3", "reject", response_source="user_action")
        self.assertEqual(self.channel.whatsapp_call_permission, "refused")
        self.assertFalse(self.channel._whatsapp_call_allowed())
        # given by WhatsApp when the customer calls the company
        self.reply("wamid.P4", "accept", is_permanent=False, expiration_timestamp=str(until),
                   response_source="automatic")
        self.assertTrue(self.channel._whatsapp_call_allowed())
        self.assertIn("The customer called", str(self.channel.message_ids[0].body))

    def test_information_panel(self):
        sections = self.channel._whatsapp_get_info_sections()
        section = next(s for s in sections if s["title"] == "Calling the Customer")
        self.assertEqual(section["buttons"][0]["method"], "whatsapp_action_call_permission_request")
        self.channel.whatsapp_call_permission = "permanent"
        section = next(s for s in self.channel._whatsapp_get_info_sections() if s["title"] == "Calling the Customer")
        self.assertFalse(section["buttons"])
