from markupsafe import Markup

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools.misc import verify_limited_field_access_token

from odoo.addons.ocd_live.tests.common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdWhatsappInbox(OcdLiveCommon):
    """The WhatsApp conversations of the team (BoWhatsApp), on those of whatsapp_cloud."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="ocd_wa_agent", name="Régie OCD",
            groups="base.group_user,whatsapp_cloud.group_whatsapp_user",
        )
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live",
            "phone_number_id": "1110021",
            "waba_id": "2220021",
            "access_token": "test-token",
            "app_secret": "test-secret",
            "verify_token": "test-verify",
            "agent_user_ids": [(6, 0, cls.agent.ids)],
            "resource_calendar_id": False,
            "bot_enabled": False,
            "away_message_enabled": False,
        })
        cls.vendor.ocd_whatsapp_optin = True
        cls.Inbox = cls.env["ocd.whatsapp.inbox"].with_user(cls.agent)

    def _receive(self, body, wa_id="wamid.OCD1"):
        message = {"from": "237670000002", "id": wa_id, "timestamp": "1760000000", "type": "text", "text": {"body": body}}
        contacts = [{"profile": {"name": "Brenda"}, "wa_id": "237670000002"}]
        self.env["whatsapp.message"]._process_incoming(self.account, message, contacts)
        return self.env["discuss.channel"].search([("whatsapp_number", "=", "237670000002")])

    def test_list_and_conversation(self):
        channel = self._receive("Bonjour, mon live est à quelle heure ?")
        self.assertEqual(channel.whatsapp_partner_id, self.vendor)
        page = self.Inbox.get_inbox()
        row = next(row for row in page["conversations"] if row["id"] == channel.id)
        self.assertTrue(row["waiting"])
        self.assertTrue(row["vendor"])
        self.assertEqual(page["waiting"], 1)
        current = page["current"]
        self.assertEqual(current["id"], channel.id)
        self.assertTrue(current["open"], "The vendor just wrote: free answer")
        incoming = [message for message in current["messages"] if message["kind"] == "in"]
        self.assertEqual(incoming[-1]["text"], "Bonjour, mon live est à quelle heure ?")
        self.assertEqual(current["consent"]["tone"], "green")

    def test_answer_and_internal_note(self):
        channel = self._receive("Bonjour")
        page = self.Inbox.ocd_post(channel.id, "On regarde et on vous répond.", False)
        kinds = [message["kind"] for message in page["current"]["messages"]]
        self.assertIn("out", kinds)
        self.assertTrue(self.env["whatsapp.message"].search([("channel_id", "=", channel.id), ("direction", "=", "outgoing")]))
        self.assertFalse(channel.whatsapp_waiting_since, "Answered: nobody waits any more")
        page = self.Inbox.ocd_post(channel.id, "Elle a déjà appelé hier.", True)
        note = page["current"]["messages"][-1]
        self.assertEqual(note["kind"], "note")
        self.assertEqual(note["text"], "Elle a déjà appelé hier.")
        with self.assertRaises(UserError):
            self.Inbox.ocd_post(channel.id, "   ", False)

    def test_window_closed_only_a_template(self):
        channel = self._receive("Merci")
        channel.sudo().whatsapp_last_inbound_date = channel.whatsapp_last_inbound_date.replace(year=2020)
        current = self.Inbox.get_conversation(channel.id)
        self.assertFalse(current["open"])
        with self.assertRaises(UserError):
            self.Inbox.ocd_post(channel.id, "Bonjour", False)
        # the follow-up template first, chosen by default
        self.assertEqual(current["templates"][0]["name"], "conversation_follow_up")
        self.assertEqual(current["templates"][0]["res_model"], "res.partner")
        # an internal note: at any time
        page = self.Inbox.ocd_post(channel.id, "Rappelé, pas de réponse", True)
        self.assertEqual(page["current"]["messages"][-1]["kind"], "note")
        self.assertEqual(page["current"]["messages"][-1]["text"], "Rappelé, pas de réponse")
        template = next(t for t in current["templates"] if t["name"] == "ocd_lien_espace")
        page = self.Inbox.ocd_send_template(channel.id, template["template_id"], template["res_model"], template["res_id"])
        auto = page["current"]["messages"][-1]
        self.assertEqual(auto["kind"], "auto")
        self.assertIn("ocd_lien_espace", auto["tag"])

    def test_codes_are_hidden(self):
        channel = self._receive("Bonjour")
        self.vendor.with_context(whatsapp_channel_id=channel.id)._ocd_deliver_login_code("482913")
        page = self.Inbox.get_conversation(channel.id)
        auto = page["messages"][-1]
        self.assertNotIn("482913", auto["text"])
        self.assertIn("••••", auto["text"])

    def test_only_the_agents(self):
        user = new_test_user(self.env, login="ocd_not_agent", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["ocd.whatsapp.inbox"].with_user(user).get_inbox()

    def test_files_shown_like_in_whatsapp(self):
        """A file of the conversation: given with its own token (read by an agent who did not
        take the conversation), not written as its name."""
        channel = self._receive("Voici mon message vocal")
        sound = self.env["ir.attachment"].create({
            "name": "Voice message.ogg", "raw": b"OggS-voice", "mimetype": "audio/ogg",
            "res_model": "discuss.channel", "res_id": channel.id,
        })
        channel.sudo().with_context(whatsapp_skip_send=True).message_post(
            author_id=self.vendor.id, body=Markup(""), attachment_ids=sound.ids,
            message_type="whatsapp_message", subtype_xmlid="mail.mt_comment",
        )
        row = self.Inbox.get_conversation(channel.id)["messages"][-1]
        self.assertEqual(row["text"], "", "A file alone: shown, not written")
        file = row["files"][0]
        self.assertEqual((file["name"], file["mimetype"], file["size"]), ("Voice message.ogg", "audio/ogg", 10))
        self.assertTrue(file["url"].startswith(f"/web/content/{sound.id}?access_token="))
        self.assertIn(f"unique={sound.checksum}", file["url"])
        self.assertEqual(file["downloadUrl"], file["url"] + "&download=true")
        self.assertTrue(file["viewable"])
        self.assertTrue(verify_limited_field_access_token(sound, "raw", file["access_token"], scope="binary"))
        # the same token at each refresh: a sound being played does not start again
        self.assertEqual(self.Inbox.get_conversation(channel.id)["messages"][-1]["files"][0]["url"], file["url"])

    def test_calls_in_the_conversation(self):
        """With the WhatsApp calls: a call is a line of its own (call back a missed call), the
        customer is called from the conversation, the last calls are next to it."""
        if "whatsapp.call" not in self.env:
            self.skipTest("The WhatsApp calls (whatsapp_cloud_call) are not installed")
        channel = self._receive("Je vous ai appelé")
        self.assertFalse(self.Inbox.get_conversation(channel.id)["calls"], "Calls not enabled on the account")
        self.account.call_enabled = True
        notice = channel.sudo().message_post(body=Markup("<p>Missed call</p>"), message_type="notification")
        call = self.env["whatsapp.call"].sudo().create({
            "account_id": self.account.id, "channel_id": channel.id, "partner_id": self.vendor.id,
            "number": "237670000002", "direction": "inbound", "state": "missed", "notice_message_id": notice.id,
        })
        current = self.Inbox.get_conversation(channel.id)
        row = next(message for message in current["messages"] if message["id"] == notice.id)
        self.assertEqual(row["call"], {
            "id": call.id, "state": "missed", "inbound": True, "missed": True, "call_back": True, "recording": False,
        })
        self.assertEqual(current["calls"]["allowed"], False)
        self.assertTrue(current["calls"]["can_ask"], "The customer just wrote: the team may ask to call them")
        self.assertIn("Calls", [section["title"] for section in current["sections"]])
        channel.sudo().whatsapp_call_permission = "permanent"
        self.assertTrue(self.Inbox.get_conversation(channel.id)["calls"]["allowed"])
