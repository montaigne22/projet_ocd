from datetime import timedelta
from unittest.mock import patch

from markupsafe import Markup

from odoo import fields
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

    def test_time_left_to_answer_for_free(self):
        """« 2 h 15 » in the list for a contact who waits, the end of the free window in the
        conversation; urgent the last hour."""
        channel = self._receive("Bonjour")
        channel.whatsapp_last_inbound_date = fields.Datetime.now() - timedelta(hours=24) + timedelta(minutes=135, seconds=30)
        page = self.Inbox.get_inbox(channel.id)
        row = next(row for row in page["conversations"] if row["id"] == channel.id)
        self.assertEqual((row["window_left"], row["window_urgent"]), ("2 h 15", False))
        self.assertIn("Free answer for 2 h 15 more (until ", page["current"]["window"])
        self.assertFalse(page["current"]["window_urgent"])
        channel.whatsapp_last_inbound_date = fields.Datetime.now() - timedelta(hours=24) + timedelta(minutes=40, seconds=30)
        page = self.Inbox.get_inbox(channel.id)
        row = next(row for row in page["conversations"] if row["id"] == channel.id)
        self.assertEqual((row["window_left"], row["window_urgent"]), ("40 min", True))
        self.assertIn("Only 40 min left to answer for free (until ", page["current"]["window"])
        self.assertTrue(page["current"]["window_urgent"])
        # answered: nobody waits, the list says nothing more
        self.Inbox.ocd_post(channel.id, "On regarde.", False)
        row = next(row for row in self.Inbox.get_inbox(channel.id)["conversations"] if row["id"] == channel.id)
        self.assertEqual(row["window_left"], "")

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

    def _receive_from(self, number, name, body, wa_id):
        message = {"from": number, "id": wa_id, "timestamp": "1760000000", "type": "text", "text": {"body": body}}
        self.env["whatsapp.message"]._process_incoming(self.account, message, [{"profile": {"name": name}, "wa_id": number}])
        return self.env["discuss.channel"].search([("whatsapp_number", "=", number)])

    def _rows(self, page):
        return [row["id"] for row in page["conversations"]]

    def test_search_by_name_or_number(self):
        brenda = self._receive("Bonjour")
        paul = self._receive_from("237699000001", "Paul Mbarga", "Ma commande ?", "wamid.PAUL1")
        for search, expected in [
            ("brend", brenda), ("Mbarga", paul), ("6 99 00", paul), ("+237 670", brenda), ("670000002", brenda),
        ]:
            with self.subTest(search=search):
                page = self.Inbox.get_inbox(None, {"search": search})
                self.assertEqual(self._rows(page), expected.ids)
                self.assertEqual(page["counts"]["all"], 1)
        page = self.Inbox.get_inbox(None, {"search": "Personne"})
        self.assertEqual(page["conversations"], [])
        self.assertFalse(page["current"], "Nothing found, nothing shown")
        # the conversation shown stays, out of the list too
        page = self.Inbox.get_inbox(brenda.id, {"search": "Mbarga"})
        self.assertEqual((self._rows(page), page["current"]["id"]), (paul.ids, brenda.id))

    def test_filters_and_more_conversations(self):
        channels = [self._receive_from(f"23769900000{index}", f"Client {index}", "Bonjour", f"wamid.C{index}")
                    for index in range(1, 4)]
        with patch("odoo.addons.ocd_live_whatsapp.models.ocd_whatsapp_inbox.LIST_LIMIT", 2):
            page = self.Inbox.get_inbox()
            self.assertEqual((len(page["conversations"]), page["has_more"]), (2, True))
            self.assertEqual(page["counts"], {"all": 3, "waiting": 3, "mine": 0})
            page = self.Inbox.get_inbox(None, {"limit": page["options"]["limit"] + 2})
            self.assertEqual((len(page["conversations"]), page["has_more"]), (3, False))
        self.Inbox.ocd_take(channels[0].id)
        page = self.Inbox.get_inbox(None, {"filter": "mine"})
        self.assertEqual(self._rows(page), channels[0].ids)
        self.assertTrue(page["conversations"][0]["mine"])
        self.Inbox.ocd_resolve(channels[1].id)
        page = self.Inbox.get_inbox(None, {"filter": "waiting"})
        self.assertNotIn(channels[1].id, self._rows(page))
        self.assertEqual(page["counts"]["waiting"], 2)
        # a filter that does not exist: all of them
        self.assertEqual(self.Inbox.get_inbox(None, {"filter": "nope"})["options"]["filter"], "all")

    def test_take_resolve_reopen(self):
        channel = self._receive("Bonjour")
        current = self.Inbox.get_conversation(channel.id)
        self.assertEqual((current["state"], current["mine"], current["state_label"]), ("new", False, "Not taken yet"))
        page = self.Inbox.ocd_take(channel.id, {"filter": "mine"})
        self.assertEqual(channel.whatsapp_user_id, self.agent)
        self.assertEqual((page["current"]["mine"], page["current"]["state_label"]), (True, "Taken by you"))
        self.assertEqual(page["options"]["filter"], "mine", "The list keeps its filter")
        page = self.Inbox.ocd_resolve(channel.id)
        self.assertEqual(page["current"]["state"], "done")
        self.assertEqual(page["current"]["state_label"], "Resolved")
        self.assertFalse(channel.whatsapp_waiting_since)
        row = next(row for row in page["conversations"] if row["id"] == channel.id)
        self.assertEqual((row["done"], row["waiting"]), (True, False))
        self.assertIn("Conversation resolved by Régie OCD", page["current"]["messages"][-1]["text"])
        page = self.Inbox.ocd_reopen(channel.id)
        self.assertEqual(page["current"]["state"], "open")
        # a new message of the contact opens it again by itself
        self.Inbox.ocd_resolve(channel.id)
        self._receive("Encore une question", wa_id="wamid.OCD2")
        self.assertEqual(channel.whatsapp_state, "open")

    def test_files_sent_to_the_contact(self):
        """Photos, documents and voice messages: uploaded by the agent, then sent with the message
        or alone, and shown in the conversation; a note keeps its files for the team."""
        channel = self._receive("Vous avez la facture ?")
        # as /mail/attachment/upload makes them: pending files of the agent
        Attachment = self.env["ir.attachment"].with_user(self.agent).sudo()

        def upload(name, raw, mimetype):
            return Attachment.create({"name": name, "raw": raw, "mimetype": mimetype,
                                      "res_model": "mail.compose.message", "res_id": 0})

        invoice = upload("Facture-S042.pdf", b"%PDF-1.4 facture", "application/pdf")
        photo = upload("colis.jpg", b"\xff\xd8\xff photo", "image/jpeg")
        page = self.Inbox.ocd_post(channel.id, "Voici la facture et le colis.", False, [invoice.id, photo.id])
        # the last answer (the conversation is then assigned to the agent: a notice follows it)
        message = [row for row in page["current"]["messages"] if row["kind"] == "out"][-1]
        self.assertEqual(message["text"], "Voici la facture et le colis.")
        self.assertEqual(sorted(file["name"] for file in message["files"]), ["Facture-S042.pdf", "colis.jpg"])
        sent = self.env["whatsapp.message"].search([("channel_id", "=", channel.id), ("direction", "=", "outgoing")])
        self.assertEqual(sorted(sent.mapped("message_type")), ["document", "image", "text"])
        self.assertEqual((invoice.res_model, invoice.res_id), ("discuss.channel", channel.id))
        # a voice message alone
        voice = upload("Voice-2026-11-25.mp3", b"ID3 voice", "audio/mpeg")
        page = self.Inbox.ocd_post(channel.id, "", False, [voice.id])
        answer = [row for row in page["current"]["messages"] if row["kind"] == "out"][-1]
        self.assertEqual((answer["text"], answer["files"][0]["name"]), ("", "Voice-2026-11-25.mp3"))
        self.assertIn("audio", self.env["whatsapp.message"].search(
            [("channel_id", "=", channel.id), ("attachment_id", "=", voice.id)]).mapped("message_type"))
        # a note with a file: never sent
        before = self.env["whatsapp.message"].search_count([("channel_id", "=", channel.id)])
        scan = upload("bon-de-livraison.jpg", b"\xff\xd8\xff scan", "image/jpeg")
        page = self.Inbox.ocd_post(channel.id, "Bon signé", True, [scan.id])
        note = page["current"]["messages"][-1]
        self.assertEqual((note["kind"], note["files"][0]["name"]), ("note", "bon-de-livraison.jpg"))
        self.assertEqual(self.env["whatsapp.message"].search_count([("channel_id", "=", channel.id)]), before)

    def test_files_of_someone_else_refused(self):
        channel = self._receive("Bonjour")
        other = self.env["ir.attachment"].create({
            "name": "secret.pdf", "raw": b"%PDF", "res_model": "mail.compose.message", "res_id": 0,
        })
        with self.assertRaises(UserError):
            self.Inbox.ocd_post(channel.id, "Tenez", False, [other.id])
        with self.assertRaises(UserError):
            self.Inbox.ocd_post(channel.id, "", False, [])

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
