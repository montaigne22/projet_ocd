import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from markupsafe import Markup

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from .common import REQUEST, WhatsAppCommon, mock_response

DOWNLOAD = "odoo.addons.whatsapp_cloud.models.whatsapp_account.requests.get"


@tagged("post_install", "-at_install")
class TestWhatsAppConversation(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="wa_agent", name="Agent Amina",
            groups="base.group_user,whatsapp_cloud.group_whatsapp_user",
        )
        cls.agent_2 = new_test_user(
            cls.env, login="wa_agent_2", name="Agent Boris",
            groups="base.group_user,whatsapp_cloud.group_whatsapp_user",
        )
        cls.manager = new_test_user(
            cls.env, login="wa_manager", name="Manager Carine",
            groups="base.group_user,whatsapp_cloud.group_whatsapp_manager",
        )
        (cls.agent | cls.agent_2 | cls.manager).lang = "en_US"
        cls.account.write({
            "agent_user_ids": [(6, 0, (cls.agent | cls.agent_2).ids)],
            "escalation_user_ids": [(6, 0, cls.manager.ids)],
            "resource_calendar_id": False,  # always open
        })
        cls.Message = cls.env["whatsapp.message"]

    def receive(self, body=None, wa_id="wamid.IN1", number="237670000000", name="Awa", **data):
        """A message of a customer, as given by the webhook of Meta."""
        message = {"from": number, "id": wa_id, "timestamp": "1760000000"}
        if body is not None:
            message.update(type="text", text={"body": body})
        message.update(data)
        if not number:
            message.pop("from")
        contacts = [{"profile": {"name": name}, "wa_id": number}] if number else []
        return self.Message._process_incoming(self.account, message, contacts)

    def outgoing(self, channel):
        return self.Message.search([
            ("channel_id", "=", channel.id), ("direction", "=", "outgoing"),
        ], order="id")

    # === RECEPTION === #

    def test_conversation_created_with_welcome_menu(self):
        message = self.receive("Bonjour, avez-vous la parka en M ?")
        channel = message.channel_id
        self.assertEqual(channel.channel_type, "whatsapp")
        self.assertEqual(channel.whatsapp_partner_id, self.partner)
        self.assertEqual(channel.whatsapp_number, "237670000000")
        self.assertEqual(channel.channel_member_ids.partner_id, self.partner)
        self.assertTrue(channel.whatsapp_channel_valid_until > fields.Datetime.now())
        self.assertEqual(message.mail_message_id.message_type, "whatsapp_message")
        self.assertEqual(message.mail_message_id.author_id, self.partner)
        # the welcome menu, as buttons (3 options at most), from OdooBot
        menu = self.outgoing(channel)
        self.assertEqual(menu.message_type, "interactive")
        payload = json.loads(menu.payload)
        self.assertEqual(payload["to"], "+237670000000")
        self.assertEqual(payload["interactive"]["type"], "button")
        option = self.account.bot_option_ids.filtered(lambda o: o.action == "handover")
        self.assertIn(
            option._get_reply_id(),
            [b["reply"]["id"] for b in payload["interactive"]["action"]["buttons"]],
        )
        self.assertEqual(channel.whatsapp_bot_state, "menu")
        # the bot handles it: no agent yet
        self.assertFalse(channel.whatsapp_waiting_since)
        self.assertNotIn(self.agent.partner_id, channel.channel_member_ids.partner_id)

    def test_same_conversation_and_no_duplicate(self):
        first = self.receive("Bonjour")
        self.assertFalse(self.receive("Bonjour"))  # sent again by Meta
        second = self.receive("Encore moi", wa_id="wamid.IN2")
        self.assertEqual(first.channel_id, second.channel_id)
        self.assertEqual(self.Message.search_count([("wa_message_id", "=", "wamid.IN1")]), 1)

    def test_menu_option_hands_over_to_the_agents(self):
        channel = self.receive("Bonjour").channel_id
        option = self.account.bot_option_ids.filtered(lambda o: o.action == "handover")
        self.receive(
            wa_id="wamid.IN2", type="interactive",
            interactive={"type": "button_reply",
                         "button_reply": {"id": option._get_reply_id(), "title": option.name}},
        )
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        self.assertTrue(channel.whatsapp_waiting_since)
        # assignment taken by an agent: all the agents see the conversation
        self.assertIn(self.agent.partner_id, channel.channel_member_ids.partner_id)
        self.assertIn(self.agent_2.partner_id, channel.channel_member_ids.partner_id)
        # the customer did not say what they need yet: invited to write it
        self.assertIn("Tell us here what you need", self.outgoing(channel)[-1].body)

    def test_talk_to_an_advisor_after_an_answer(self):
        channel = self.receive("Bonjour").channel_id
        self.receive("Je cherche une parka bleue en taille L", wa_id="wamid.IN2")
        # the customer already wrote what they need: no invitation
        self.assertIn("Thank you, an advisor will answer you", self.outgoing(channel)[-1].body)
        channel.whatsapp_bot_state = "menu"
        channel.whatsapp_waiting_since = False
        self.receive(wa_id="wamid.IN3", type="interactive", interactive={
            "type": "button_reply", "button_reply": {"id": "whatsapp_handover", "title": "-"},
        })
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        self.assertTrue(channel.whatsapp_waiting_since)
        self.assertIn("Tell us here what you need", self.outgoing(channel)[-1].body)

    def test_text_option_of_the_menu(self):
        self.env["whatsapp.bot.option"].create({
            "account_id": self.account.id, "sequence": 1, "name": "Horaires",
            "action": "text", "answer": "Ouvert de 9 h à 19 h.",
        })
        channel = self.receive("Bonjour").channel_id
        option = self.account.bot_option_ids.filtered(lambda o: o.name == "Horaires")
        self.receive(wa_id="wamid.IN2", type="interactive", interactive={
            "type": "button_reply", "button_reply": {"id": option._get_reply_id(), "title": "Horaires"},
        })
        # the answer, with the choices to go on without writing
        answer = self.outgoing(channel)[-1]
        self.assertEqual(answer.body.splitlines()[0], "Ouvert de 9 h à 19 h.")
        self.assertEqual(self._menu_ids(channel), ["whatsapp_menu", "whatsapp_handover"])
        self.assertEqual(channel.whatsapp_bot_state, "menu")
        self.assertFalse(channel.whatsapp_waiting_since)

    def test_not_understood_after_the_menu_goes_to_an_agent(self):
        self.account.assignment_mode = "round_robin"
        channel = self.receive("Bonjour").channel_id
        self.receive("Ma commande n'est pas arrivée", wa_id="wamid.IN2")
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        self.assertIn(channel.whatsapp_user_id, self.agent | self.agent_2)
        self.assertEqual(channel.whatsapp_state, "open")

    def test_without_menu_straight_to_the_agents(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        self.assertTrue(channel.whatsapp_waiting_since)
        self.assertFalse(self.outgoing(channel))

    def test_welcome_without_options_goes_to_the_team(self):
        self.account.bot_option_ids.active = False
        channel = self.receive("Bonsoir").channel_id
        self.assertEqual(len(self.outgoing(channel)), 1)  # the welcome message
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        self.assertTrue(channel.whatsapp_waiting_since)
        self.assertIn(self.agent.partner_id, channel.channel_member_ids.partner_id)
        self.assertTrue(any(
            "take it to answer" in body for body in channel.message_ids.mapped("body")
        ))

    def test_account_created_from_its_form(self):
        # the form sends an empty list of options: the default ones are created all the same
        account = self.env["whatsapp.account"].create({
            "name": "Shop Yaoundé",
            "phone_number_id": "1110009",
            "waba_id": "2220002",
            "access_token": "test-token",
            "bot_option_ids": [],
        })
        self.assertIn("handover", account.bot_option_ids.mapped("action"))

    def test_notices_in_the_language_of_the_team(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        (self.agent | self.agent_2).lang = "fr_FR"
        self.account.bot_enabled = False
        self.assertEqual(self.account._get_team_lang(), "fr_FR")
        event = self.env["whatsapp.webhook.event"].create({
            "account_id": self.account.id,
            "field": "messages",
            "payload": json.dumps({
                "metadata": {"phone_number_id": "1110001"},
                "contacts": [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}],
                "messages": [{"from": "237670000000", "id": "wamid.FR1", "timestamp": "1760000000",
                              "type": "text", "text": {"body": "Bonsoir"}}],
            }),
        })
        event._process()
        channel = self.Message.search([("wa_message_id", "=", "wamid.FR1")]).channel_id
        self.assertTrue(any(
            "Nouvelle conversation WhatsApp" in body for body in channel.message_ids.mapped("body")
        ))

    def _choose(self, option_or_id, wa_id):
        reply_id = option_or_id if isinstance(option_or_id, str) else option_or_id._get_reply_id()
        return self.receive(wa_id=wa_id, type="interactive", interactive={
            "type": "button_reply", "button_reply": {"id": reply_id, "title": "-"},
        })

    def _menu_ids(self, channel):
        payload = json.loads(self.outgoing(channel)[-1].payload)
        action = payload["interactive"]["action"]
        if "buttons" in action:
            return [button["reply"]["id"] for button in action["buttons"]]
        return [row["id"] for row in action["sections"][0]["rows"]]

    def _option(self, action):
        return self.account.with_context(active_test=False).bot_option_ids.filtered(
            lambda option: option.action == action
        )

    def test_submenu(self):
        submenu = self.env["whatsapp.bot.option"].create({
            "account_id": self.account.id, "sequence": 50, "name": "Infos pratiques",
            "action": "submenu", "answer": "Que voulez-vous savoir ?",
        })
        hours = self.env["whatsapp.bot.option"].create({
            "parent_id": submenu.id, "name": "Horaires", "action": "text",
            "answer": "Du lundi au samedi, 9 h - 19 h.",
        })
        self.env["whatsapp.bot.option"].create({
            "parent_id": submenu.id, "name": "Retours", "action": "text", "answer": "Sous 14 jours.",
        })
        self.assertEqual(hours.account_id, self.account)
        self.assertNotIn(hours, self.account.bot_option_ids)  # only in its sub-menu
        channel = self.receive("Bonjour").channel_id
        self.assertIn(submenu._get_reply_id(), self._menu_ids(channel))
        self._choose(submenu, "wamid.IN2")
        self.assertEqual(self.outgoing(channel)[-1].body.splitlines()[0], "Que voulez-vous savoir ?")
        self.assertEqual(self._menu_ids(channel)[:1] + self._menu_ids(channel)[-1:],
                         [hours._get_reply_id(), "whatsapp_menu"])
        self._choose(hours, "wamid.IN3")
        self.assertEqual(self.outgoing(channel)[-1].body.splitlines()[0], "Du lundi au samedi, 9 h - 19 h.")
        self.assertEqual(channel.whatsapp_bot_state, "menu")
        self._choose("whatsapp_menu", "wamid.IN4")
        self.assertIn(submenu._get_reply_id(), self._menu_ids(channel))
        # a sub-menu without active option is not offered
        submenu.child_ids.active = False
        self.receive("menu", wa_id="wamid.IN5")
        self.assertNotIn(submenu._get_reply_id(), self._menu_ids(channel))

    def test_language_option(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        options = self._option("lang")
        self.assertEqual(sorted(options.mapped("lang")), ["en_US", "fr_FR"])
        french = options.filtered(lambda option: option.lang == "fr_FR")
        self.assertEqual(french.name, "Français")
        options.active = True
        channel = self.receive("Bonjour").channel_id
        ids = self._menu_ids(channel)
        self.assertIn(french._get_reply_id(), ids)
        self.assertNotIn((options - french)._get_reply_id(), ids)  # already in English
        self._choose(french, "wamid.IN2")
        self.assertEqual(self.partner.lang, "fr_FR")
        ids = self._menu_ids(channel)
        self.assertNotIn(french._get_reply_id(), ids)
        self.assertIn((options - french)._get_reply_id(), ids)
        self.assertIn(
            self.account.with_context(lang="fr_FR").welcome_message.split("\n")[0],
            self.outgoing(channel)[-1].body,
        )

    def test_stop_and_start_options(self):
        stop, start = self._option("stop"), self._option("start")
        (stop | start).active = True
        channel = self.receive("Bonjour").channel_id
        self.assertIn(stop._get_reply_id(), self._menu_ids(channel))
        self.assertNotIn(start._get_reply_id(), self._menu_ids(channel))
        self._choose(stop, "wamid.IN2")
        self.assertFalse(self.partner.whatsapp_opt_in)
        self.assertIn("Send START", self.outgoing(channel)[-1].body)
        self.receive("menu", wa_id="wamid.IN3")
        self.assertIn(start._get_reply_id(), self._menu_ids(channel))
        self._choose(start, "wamid.IN4")
        self.assertTrue(self.partner.whatsapp_opt_in)

    def test_round_robin_fewest_open_conversations(self):
        self.account.write({"assignment_mode": "round_robin", "bot_enabled": False})
        first = self.receive("Bonjour").channel_id
        second = self.receive("Bonjour", wa_id="wamid.B1", number="237699000001", name="Bob").channel_id
        self.assertEqual(first.whatsapp_user_id | second.whatsapp_user_id, self.agent | self.agent_2)
        # the assigned agent only is in the conversation
        self.assertNotIn(
            ((self.agent | self.agent_2) - first.whatsapp_user_id).partner_id,
            first.channel_member_ids.partner_id,
        )

    def test_unknown_number_and_identification(self):
        message = self.receive("Bonjour", number="237699887766", name="Client Inconnu")
        unknown = message.partner_id
        self.assertTrue(unknown.whatsapp_to_identify)
        self.assertEqual(unknown.name, "Client Inconnu")
        self.assertEqual(unknown.phone, "+237699887766")
        channel = message.channel_id
        wizard = self.env["whatsapp.link.partner"].with_user(self.agent).create({
            "channel_id": channel.id, "partner_id": self.partner.id,
        })
        wizard.action_link()
        self.assertEqual(channel.whatsapp_partner_id, self.partner)
        self.assertFalse(unknown.exists())
        self.assertEqual(message.partner_id, self.partner)
        self.assertEqual(self.partner._whatsapp_number(), "237699887766")
        self.assertFalse(self.partner.whatsapp_to_identify)

    def test_username_without_number(self):
        """A customer with a WhatsApp username hides their number: their BSUID identifies
        them, and the answers go to it."""
        message = self.Message._process_incoming(self.account, {
            "from_user_id": "CM.1349120865530", "id": "wamid.U1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Bonjour"},
        }, [{"profile": {"name": "Sheena", "username": "sheena237"},
             "user_id": "CM.1349120865530"}])
        partner = message.partner_id
        self.assertEqual(partner.whatsapp_user_ref, "CM.1349120865530")
        self.assertEqual(partner.whatsapp_username, "sheena237")
        channel = message.channel_id
        self.assertFalse(channel.whatsapp_number)
        self.assertEqual(json.loads(self.outgoing(channel).payload)["recipient"], "CM.1349120865530")
        again = self.Message._process_incoming(self.account, {
            "from_user_id": "CM.1349120865530", "id": "wamid.U2", "timestamp": "1760000001",
            "type": "text", "text": {"body": "Re"},
        }, [])
        self.assertEqual(again.channel_id, channel)

    def test_number_change(self):
        channel = self.receive("Bonjour").channel_id
        self.Message._process_incoming(self.account, {
            "from": "237670000000", "id": "wamid.SYS", "timestamp": "1760000000", "type": "system",
            "system": {"body": "User Awa changed from 237670000000 to 237699000099",
                       "wa_id": "237699000099", "type": "user_changed_number",
                       "user_id": "CM.NEW"},
        }, [])
        self.assertEqual(channel.whatsapp_number, "237699000099")
        self.assertEqual(self.partner._whatsapp_number(), "237699000099")
        self.assertEqual(self.partner.whatsapp_user_ref, "CM.NEW")

    def test_media_downloaded(self):
        content = b"\x89PNG fake image"
        download = MagicMock()
        download.raise_for_status.return_value = None
        download.iter_content.return_value = [content]
        download.headers = {"Content-Type": "image/png"}
        with patch(DOWNLOAD, return_value=download) as get, patch(REQUEST) as request:
            message = self.receive(
                type="image",
                image={"id": "media-9", "mime_type": "image/png", "caption": "Cette couleur ?",
                       "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=9"},
            )
        request.assert_not_called()  # the URL of the webhook is used directly
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer test-token"})
        attachment = message.attachment_id
        self.assertEqual(attachment.raw.content, content)
        self.assertEqual(attachment.mimetype, "image/png")
        self.assertEqual((attachment.res_model, attachment.res_id), ("discuss.channel", message.channel_id.id))
        self.assertEqual(message.mail_message_id.attachment_ids, attachment)
        self.assertEqual(message.body, "Cette couleur ?")

    def test_media_not_downloaded(self):
        with patch(REQUEST, return_value=mock_response({"error": {"code": 131052, "message": "No"}}, 400)):
            message = self.receive(type="audio", audio={"id": "media-10", "voice": True})
        self.assertFalse(message.attachment_id)
        self.assertIn("could not be downloaded", message.body)

    def test_location_reaction_and_reply(self):
        channel = self.receive("Bonjour").channel_id
        menu = self.outgoing(channel)
        menu.write({"state": "sent", "wa_message_id": "wamid.MENU"})
        location = self.receive(wa_id="wamid.L", type="location", location={
            "latitude": 4.05, "longitude": 9.7, "name": "Akwa", "address": "Douala",
        })
        self.assertIn("https://maps.google.com/?q=4.05,9.7", location.body)
        self.receive(wa_id="wamid.R", type="reaction",
                     reaction={"message_id": "wamid.MENU", "emoji": "👍"})
        self.assertEqual(menu.mail_message_id.reaction_ids.content, "👍")
        self.assertEqual(menu.mail_message_id.reaction_ids.partner_id, self.partner)
        self.receive(wa_id="wamid.R2", type="reaction", reaction={"message_id": "wamid.MENU"})
        self.assertFalse(menu.mail_message_id.reaction_ids)
        reply = self.receive("Merci", wa_id="wamid.C", context={"from": "1", "id": "wamid.MENU"})
        self.assertEqual(reply.parent_id, menu)
        self.assertEqual(reply.mail_message_id.parent_id, menu.mail_message_id)

    def test_stop_and_start(self):
        channel = self.receive("STOP").channel_id
        self.assertFalse(self.partner.whatsapp_opt_in)
        self.assertIn("Send START", self.outgoing(channel)[-1].body)
        self.assertFalse(channel.whatsapp_waiting_since)
        self.receive("Start", wa_id="wamid.IN2")
        self.assertTrue(self.partner.whatsapp_opt_in)

    # === ANSWERS OF THE AGENTS === #

    def test_agent_answer_sent_to_the_customer(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        channel.whatsapp_message_ids.write({"wa_message_id": "wamid.IN1"})
        incoming_post = channel.whatsapp_message_ids.mail_message_id
        message = channel.with_user(self.agent).message_post(
            body=Markup("Bonjour {first_name}, c'est <b>noté</b> !"),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            parent_id=incoming_post.id,
        )
        self.assertEqual(message.message_type, "whatsapp_message")
        wa_message = self.outgoing(channel)
        self.assertEqual(wa_message.mail_message_id, message)
        payload = json.loads(wa_message.payload)
        self.assertEqual(payload["text"]["body"], "Bonjour Awa, c'est *noté* !")
        self.assertEqual(payload["context"], {"message_id": "wamid.IN1"})
        # the agent took the conversation, the customer no longer waits
        self.assertEqual(channel.whatsapp_user_id, self.agent)
        self.assertFalse(channel.whatsapp_waiting_since)
        self.assertEqual(channel.whatsapp_state, "open")
        with patch(REQUEST, return_value=mock_response({"messages": [{"id": "wamid.OUT"}]})):
            wa_message._send()
        self.assertEqual(wa_message.state, "sent")

    def test_agent_answer_with_files(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        image = self.env["ir.attachment"].create({
            "name": "parka.png", "raw": b"\x89PNG", "mimetype": "image/png",
            "res_model": "discuss.channel", "res_id": channel.id,
        })
        pdf = self.env["ir.attachment"].create({
            "name": "devis.pdf", "raw": b"%PDF", "mimetype": "application/pdf",
            "res_model": "discuss.channel", "res_id": channel.id,
        })
        channel.with_user(self.agent).message_post(
            body="Voici", message_type="comment", attachment_ids=(image | pdf).ids,
        )
        messages = self.outgoing(channel)
        self.assertEqual(messages.mapped("message_type"), ["text", "image", "document"])
        document = json.loads(messages[2].payload)
        self.assertEqual(document["document"]["filename"], "devis.pdf")
        answers = [mock_response({"id": "media-1"}), mock_response({"messages": [{"id": "w"}]})]
        with patch(REQUEST, side_effect=answers):
            messages[2]._send()
        self.assertEqual(json.loads(messages[2].payload)["document"]["id"], False)
        self.assertEqual(messages[2].state, "sent")

    def test_no_free_answer_after_24_hours(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        channel.whatsapp_last_inbound_date = fields.Datetime.now() - timedelta(hours=25)
        with self.assertRaises(UserError):
            channel.with_user(self.agent).message_post(body="Bonjour", message_type="comment")
        action = channel.with_user(self.agent).whatsapp_action_send_template()
        self.assertEqual(action["res_model"], "whatsapp.composer")

    def test_template_sent_by_the_number_of_the_conversation(self):
        second = self.env["whatsapp.account"].create({
            "name": "Shop Yaoundé", "phone_number_id": "1110002", "waba_id": "2220002",
            "access_token": "test-token", "bot_enabled": False,
        })
        channel = self.Message._process_incoming(second, {
            "from": "237670000000", "id": "wamid.Y1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Bonjour"},
        }, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}]).channel_id
        self.assertEqual(channel.whatsapp_account_id, second)
        # the template of the first number exists in the same WhatsApp Business account
        message = self.template.with_context(whatsapp_channel_id=channel.id)._send(self.partner)
        self.assertEqual(message.account_id, second)
        self.assertIn(message, self.outgoing(channel))
        # without conversation: the account of the template
        self.assertEqual(self.template._send(self.partner).account_id, self.account)
        # the conversation where the customer wrote last
        self.assertEqual(
            self.env["discuss.channel"]._whatsapp_find(self.account | second, "237670000000"),
            channel,
        )

    def test_template_from_the_conversation(self):
        channel = self.receive("Bonjour").channel_id
        composer = self.env["whatsapp.composer"].with_user(self.agent).with_context(
            default_res_model="res.partner", default_res_ids=self.partner.ids,
            whatsapp_channel_id=channel.id,
        ).create({"template_id": self.template.id})
        composer.action_send()
        message = self.Message.search([("template_id", "=", self.template.id)])
        self.assertEqual(message.channel_id, channel)
        self.assertIn("Template: Welcome", message.mail_message_id.body)

    def test_internal_note_not_sent(self):
        channel = self.receive("Bonjour").channel_id
        before = self.outgoing(channel)
        channel.with_user(self.agent).execute_command_note(body="/note vérifier le stock")
        self.assertEqual(self.outgoing(channel), before)
        self.assertIn("vérifier le stock", channel.message_ids[0].body)

    def test_read_receipt_and_typing(self):
        self.account.bot_enabled = False
        message = self.receive("Bonjour")
        channel = message.channel_id
        channel.with_user(self.agent).whatsapp_action_take()
        member = channel.channel_member_ids.filtered(lambda m: m.partner_id == self.agent.partner_id)
        member._mark_as_read(channel.message_ids[0].id)
        self.assertEqual(message.read_receipt, "todo")
        with patch(REQUEST, return_value=mock_response({"success": True})) as request:
            message._send_read_receipt()
        self.assertEqual(request.call_args.kwargs["json"], {
            "messaging_product": "whatsapp", "status": "read", "message_id": "wamid.IN1",
        })
        member._notify_typing(True)
        self.assertEqual(message.read_receipt, "typing")
        with patch(REQUEST, return_value=mock_response({"success": True})) as request:
            message._send_read_receipt()
        self.assertEqual(request.call_args.kwargs["json"]["typing_indicator"], {"type": "text"})

    def test_status_shown_on_the_message(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        post = channel.with_user(self.agent).message_post(body="Oui", message_type="comment")
        wa_message = self.outgoing(channel)
        wa_message.write({"state": "sent", "wa_message_id": "wamid.OUT"})
        self.Message._process_status(self.account, {"id": "wamid.OUT", "status": "played"})
        self.assertEqual(wa_message.state, "read")
        self.Message._process_status(self.account, {
            "id": "wamid.OUT", "status": "failed",
            "errors": [{"code": 131047, "title": "Re-engagement message"}],
        })
        self.assertEqual(wa_message.state, "failed")
        self.assertIn("only an approved template", wa_message.error_help)
        self.assertIn("Message not delivered", channel.message_ids[0].body)
        self.assertTrue(post.exists())

    # === TEAM === #

    def test_transfer_resolve_reopen(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        channel.with_user(self.agent).whatsapp_action_take()
        self.assertEqual(channel.whatsapp_user_id, self.agent)
        self.assertNotIn(self.agent_2.partner_id, channel.channel_member_ids.partner_id)
        wizard = self.env["whatsapp.conversation.assign"].with_user(self.agent).create({
            "channel_id": channel.id, "user_id": self.agent_2.id, "note": "Échange de taille",
        })
        wizard.action_transfer()
        self.assertEqual(channel.whatsapp_user_id, self.agent_2)
        self.assertNotIn(self.agent.partner_id, channel.channel_member_ids.partner_id)
        channel.with_user(self.agent_2).whatsapp_action_resolve()
        self.assertEqual(channel.whatsapp_state, "done")
        # the customer writes again soon after: back to the same agent, no menu
        self.receive("Une autre question", wa_id="wamid.IN2")
        self.assertEqual(channel.whatsapp_state, "open")
        self.assertEqual(channel.whatsapp_user_id, self.agent_2)

    def test_agents_only_see_their_conversations(self):
        self.account.write({"assignment_mode": "round_robin", "bot_enabled": False})
        channel = self.receive("Bonjour").channel_id
        other = (self.agent | self.agent_2) - channel.whatsapp_user_id
        Channel = self.env["discuss.channel"]
        self.assertFalse(Channel.with_user(other).search([("id", "=", channel.id)]))
        self.assertTrue(Channel.with_user(channel.whatsapp_user_id).search([("id", "=", channel.id)]))
        self.assertTrue(Channel.with_user(self.manager).search([("id", "=", channel.id)]))

    def test_managers_see_the_conversations_of_their_companies(self):
        other_company = self.env["res.company"].create({"name": "Other Shop"})
        other_account = self.env["whatsapp.account"].create({
            "name": "Other Shop", "phone_number_id": "3330001", "waba_id": "4440002",
            "access_token": "test-token", "company_id": other_company.id, "bot_enabled": False,
        })
        other = self.Message._process_incoming(other_account, {
            "from": "237655000000", "id": "wamid.OTHER1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Bonjour"},
        }, [{"profile": {"name": "Paul"}, "wa_id": "237655000000"}]).channel_id
        mine = self.receive("Bonjour").channel_id
        visible = self.env["discuss.channel"].with_user(self.manager).search([
            ("channel_type", "=", "whatsapp"),
        ])
        self.assertIn(mine, visible)
        self.assertNotIn(other, visible)
        self.assertNotIn(
            other_account,
            self.env["whatsapp.account"].with_user(self.manager).search([]),
        )

    def test_reminder_then_escalation(self):
        self.account.write({"bot_enabled": False, "response_delay": 15, "escalation_delay": 60})
        channel = self.receive("Bonjour").channel_id
        Channel = self.env["discuss.channel"]
        channel.whatsapp_waiting_since = fields.Datetime.now() - timedelta(minutes=20)
        Channel._cron_whatsapp_check_delays()
        self.assertEqual(channel.whatsapp_alert_level, 1)
        self.assertIn("waiting for an answer for 20 minutes", channel.message_ids[0].body)
        channel.whatsapp_waiting_since = fields.Datetime.now() - timedelta(minutes=61)
        Channel._cron_whatsapp_check_delays()
        self.assertEqual(channel.whatsapp_alert_level, 2)
        self.assertIn(self.manager.partner_id, channel.channel_member_ids.partner_id)
        self.assertIn(self.manager.partner_id, channel.message_ids[0].partner_ids)
        # an answer resets the alerts
        channel.with_user(self.agent).message_post(body="Pardon pour l'attente", message_type="comment")
        self.assertEqual((channel.whatsapp_alert_level, channel.whatsapp_waiting_since), (0, False))

    # === SETTINGS === #

    def test_conversations_disabled(self):
        self.env.company.whatsapp_conversations = False
        Channel = self.env["discuss.channel"]
        channels = Channel.search_count([("channel_type", "=", "whatsapp")])
        message = self.receive("Bonjour, avez-vous la parka en M ?")
        self.assertFalse(message.channel_id)
        self.assertEqual(Channel.search_count([("channel_type", "=", "whatsapp")]), channels)
        self.assertEqual(
            (message.partner_id, message.model, message.res_id),
            (self.partner, "res.partner", self.partner.id),
        )
        self.assertIn("avez-vous la parka", self.partner.message_ids[0].body)
        # no automatic answer
        self.assertFalse(self.Message.search([
            ("account_id", "=", self.account.id), ("direction", "=", "outgoing"),
        ]))
        # STOP still works
        self.receive("STOP", wa_id="wamid.IN2")
        self.assertFalse(self.partner.whatsapp_opt_in)
        self.assertIn("no longer receives", self.partner.message_ids[0].body)
        # an unknown number is kept, without creating a contact
        partners = self.env["res.partner"].search_count([])
        unknown = self.receive("Hello", wa_id="wamid.IN3", number="237655555555")
        self.assertEqual((unknown.body, unknown.partner_id), ("Hello", self.env["res.partner"]))
        self.assertEqual(self.env["res.partner"].search_count([]), partners)

    def test_read_receipts_disabled(self):
        self.env.company.whatsapp_read_receipts = False
        self.account.bot_enabled = False
        message = self.receive("Bonjour")
        channel = message.channel_id
        channel.with_user(self.agent).whatsapp_action_take()
        member = channel.channel_member_ids.filtered(lambda m: m.partner_id == self.agent.partner_id)
        member._mark_as_read(channel.message_ids[0].id)
        member._notify_typing(True)
        self.assertNotIn(message.read_receipt, ("todo", "typing"))

    def test_answer_reminders_disabled(self):
        self.env.company.whatsapp_answer_reminders = False
        self.account.write({"bot_enabled": False, "response_delay": 15, "escalation_delay": 60})
        channel = self.receive("Bonjour").channel_id
        channel.whatsapp_waiting_since = fields.Datetime.now() - timedelta(minutes=90)
        self.env["discuss.channel"]._cron_whatsapp_check_delays()
        self.assertEqual(channel.whatsapp_alert_level, 0)

    def test_settings(self):
        settings = self.env["res.config.settings"].create({})
        self.assertTrue(settings.whatsapp_conversations)
        self.assertEqual(settings.whatsapp_welcome_menu, self.account.bot_enabled)
        settings.write({
            "whatsapp_welcome_menu": False,
            "whatsapp_away_message": False,
            "whatsapp_read_receipts": False,
        })
        settings.execute()
        self.assertFalse(self.account.bot_enabled)
        self.assertFalse(self.account.away_message_enabled)
        self.assertFalse(self.env.company.whatsapp_read_receipts)
        settings = self.env["res.config.settings"].create({})
        self.assertFalse(settings.whatsapp_welcome_menu)
        self.assertFalse(settings.whatsapp_away_message)
        # the welcome menu disabled: straight to the agents
        channel = self.receive("Bonjour").channel_id
        self.assertFalse(self.outgoing(channel))
        self.assertTrue(channel.whatsapp_waiting_since)

    def test_away_message_outside_opening_hours(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Never open", "attendance_ids": [(5, 0, 0)],
        })
        self.account.write({"resource_calendar_id": calendar.id, "bot_enabled": False})
        channel = self.receive("Bonjour").channel_id
        self.assertIn("We are closed right now", self.outgoing(channel).body)
        self.receive("Allô ?", wa_id="wamid.IN2")
        self.assertEqual(len(self.outgoing(channel)), 1)  # once every 12 hours

    def test_placeholders_and_canned_responses(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        channel.with_user(self.agent).message_post(
            body="{prenom}, {conseiller} de {company} vous répond.", message_type="comment",
        )
        self.assertEqual(
            self.outgoing(channel).body,
            f"Awa, Agent Amina de {self.account.company_id.name} vous répond.",
        )

    # === ACCOUNT === #

    def test_health_check(self):
        answer = {
            "display_phone_number": "237 699 00 00 00", "verified_name": "My Shop",
            "quality_rating": "YELLOW", "status": "CONNECTED", "name_status": "APPROVED",
            "whatsapp_business_manager_messaging_limit": "TIER_2K",
            "health_status": {"can_send_message": "AVAILABLE"},
        }
        with patch(REQUEST, return_value=mock_response(answer)):
            self.account._check_health()
        self.assertEqual(self.account.health_state, "warning")
        self.assertEqual(self.account.messaging_limit, "TIER_2K")
        self.assertIn("medium", self.account.health_message)
        error = {"error": {"code": 190, "message": "Error validating access token"}}
        with patch(REQUEST, return_value=mock_response(error, 401)):
            self.account._check_health()
        self.assertEqual(self.account.health_state, "error")
        self.assertIn("permanent token", self.account.health_message)
        self.assertIn(self.manager.partner_id, self.account.message_ids[0].partner_ids)

    def test_submit_template_to_meta(self):
        template = self.env["whatsapp.template"].create({
            "name": "Ready for pickup",
            "template_name": "ready_for_pickup",
            "lang_code": "fr",
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "account_id": self.account.id,
            "body": "Bonjour {{1}}, votre commande est prête.",
            "footer_text": "My Shop Douala",
            "button_ids": [(0, 0, {"button_type": "url", "name": "Suivre ma commande",
                                   "url": "https://shop.example.com{{1}}", "url_example": "/my/orders/1"}),
                           (0, 0, {"button_type": "quick_reply", "name": "Merci"})],
        })
        template.variable_ids.sample_value = "Awa"
        with patch(REQUEST, return_value=mock_response(
            {"id": "5461", "status": "PENDING", "category": "UTILITY"}
        )) as request:
            template.action_submit_to_meta()
        self.assertEqual(request.call_args.args[1], "https://graph.facebook.com/v26.0/2220002/message_templates")
        self.assertEqual(request.call_args.kwargs["json"], {
            "name": "ready_for_pickup",
            "language": "fr",
            "category": "UTILITY",
            "parameter_format": "positional",
            "components": [
                {"type": "BODY", "text": "Bonjour {{1}}, votre commande est prête.",
                 "example": {"body_text": [["Awa"]]}},
                {"type": "FOOTER", "text": "My Shop Douala"},
                {"type": "BUTTONS", "buttons": [
                    # the variable after a slash, the example as a whole URL: else "not a valid URI"
                    {"type": "URL", "text": "Suivre ma commande", "url": "https://shop.example.com/{{1}}",
                     "example": ["https://shop.example.com/my/orders/1"]},
                    {"type": "QUICK_REPLY", "text": "Merci"},
                ]},
            ],
        })
        self.assertEqual((template.status, template.wa_template_id), ("pending", "5461"))
        self.assertEqual(template.button_ids[0].url, "https://shop.example.com/{{1}}")
        # waiting for the approval: not sent
        message = template._send(self.partner)
        self.assertEqual(message.state, "skipped")

    def test_link_button_with_the_address_of_the_site(self):
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "https://shop.example.com/")
        self.template.write({"button_ids": [(0, 0, {
            "button_type": "url", "name": "Voir et payer", "url": "{base_url}{{1}}",
            "url_example": "/my/orders/12?access_token=abc123",
        })]})
        self.template.button_ids._normalize_url_for_meta()
        button = self.template.button_ids
        self.assertEqual(button.url, "{base_url}/{{1}}")
        self.assertEqual(button._prepare_meta_button(), {
            "type": "URL", "text": "Voir et payer", "url": "https://shop.example.com/{{1}}",
            "example": ["https://shop.example.com/my/orders/12?access_token=abc123"],
        })
        # an address that Meta cannot open
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "http://localhost:8069")
        with self.assertRaisesRegex(UserError, "web.base.url"):
            self.template._check_for_meta()

    def test_template_rules_of_meta(self):
        refused = {
            "{{1}} {{2}}": "separated by words",
            "Bonjour {{1}}, {{2}} arrive demain.": "separated by words",
            "Bonjour {{1}}, rendez-vous ({{2}}) : {{3}} à la boutique.": "separated by words",
            "{{1}}, votre commande est prête.": "start or end",
            "Bonjour {{1}}, votre commande est prête : {{2}}": "start or end",
            # a punctuation mark after the variable: still at the end for Meta
            "Bonjour {{1}}, retrait à partir de {{2}}.": "start or end",
            "Bonjour {{1}}, votre paiement ({{2}}).": "start or end",
        }
        for body, error in refused.items():
            with self.subTest(body=body), self.assertRaisesRegex(UserError, error):
                self.template.body = body
                self.template._check_for_meta()
        for body in (
            "Bonjour {{1}}, votre commande {{2}} est prête.",
            "Bonjour {{1}}, retrait à partir de {{2}}, à la boutique.",
            "Bonjour {{1}}, livraison de {{2}} à {{3}} demain.",
            "Hello {{ customer }}, see you soon!",
        ):
            with self.subTest(body=body):
                self.template.body = body
                self.template._check_for_meta()

    def test_login_words_refused_in_a_utility_template(self):
        """Meta takes a code, a password, a username or a link to keep for yourself for an
        authentication message, and refuses the Utility template (INCORRECT_CATEGORY): Odoo
        says it before submitting."""
        for body in (
            "Bonjour {{1}}, votre code de livraison est {{2}} pour ce colis.",
            "Bonjour {{1}}, choisissez votre mot de passe avec ce lien.",
            "Bonjour {{1}}, votre identifiant est votre numéro WhatsApp.",
            "Hello {{1}}, here is your personal link to your space.",
            "Hello {{1}}, your space is ready. Keep it to yourself.",
        ):
            with self.subTest(body=body), self.assertRaisesRegex(UserError, "INCORRECT_CATEGORY"):
                self.template.body = body
                self.template._check_for_meta()
        # A word of the button counts too
        self.template.write({
            "body": "Bonjour {{1}}, votre commande {{2}} est prête.",
            "button_ids": [(0, 0, {"button_type": "quick_reply", "name": "Voir mon code"})],
        })
        with self.assertRaisesRegex(UserError, "INCORRECT_CATEGORY"):
            self.template._check_for_meta()
        self.template.button_ids.name = "Merci"
        self.template._check_for_meta()
        # A promotion code is free in a marketing template
        self.template.write({"category": "marketing", "body": "Bonjour {{1}}, votre code promo {{2}} vaut cette semaine."})
        self.template._check_for_meta()

    def test_submit_selected_templates_to_meta(self):
        """Several templates at once, after an update gave new texts to the refused ones: the
        refused one goes, the approved one stays as it is, a text that Odoo refuses says why."""
        Template = self.env["whatsapp.template"]
        common = {
            "lang_code": "fr", "model_id": self.env["ir.model"]._get_id("res.partner"),
            "account_id": self.account.id,
        }
        refused = Template.create({**common, "name": "Refused", "template_name": "refused_one",
                                   "body": "Bonjour {{1}}, votre commande est prête.", "wa_template_id": "777"})
        approved = Template.create({**common, "name": "Approved", "template_name": "approved_one",
                                    "body": "Bonjour {{1}}, votre commande est en route.", "wa_template_id": "778"})
        wrong = Template.create({**common, "name": "Wrong", "template_name": "wrong_one",
                                 "body": "Bonjour {{1}}, votre code est prêt."})
        refused.status = "rejected"
        approved.status = "approved"
        templates = refused | approved | wrong
        templates.variable_ids.sample_value = "Awa"
        with patch(REQUEST, return_value=mock_response({"success": True})) as request:
            action = templates.action_submit_selected_to_meta()
        self.assertEqual(request.call_count, 1, "The refused one only")
        self.assertTrue(request.call_args.args[1].endswith("/777"))
        self.assertEqual(request.call_args.kwargs["json"]["category"], "UTILITY")
        self.assertEqual(refused.status, "pending")
        self.assertEqual(approved.status, "approved")
        self.assertEqual(wrong.status, "unknown")
        self.assertEqual(action["params"]["type"], "warning")
        self.assertIn("1 template submitted", action["params"]["message"])
        self.assertIn("wrong_one", action["params"]["message"])
        with patch(REQUEST) as request:
            action = approved.action_submit_selected_to_meta()
        request.assert_not_called()
        self.assertEqual(action["params"]["type"], "info")

    def test_module_texts_reach_existing_databases(self):
        """A text corrected in a module replaces its previous text, kept in the database by
        the noupdate data, unless the user wrote another text or Meta approved it."""
        Template = self.env["whatsapp.template"]
        xmlid = "whatsapp_cloud.template_conversation_follow_up"
        follow_up = self.env.ref(xmlid)
        text = Template._get_module_bodies("whatsapp_cloud")[xmlid]
        self.assertEqual(text, follow_up.body, "The text of the data file of the module")
        old = "Bonjour {{1}}, nous revenons vers vous au sujet de {{2}}"
        olds = {xmlid: [old]}
        variable = follow_up.variable_ids
        # a text written by the user: kept
        follow_up.body = "Bonjour {{1}}, notre équipe vous répond ici."
        self.assertFalse(Template._update_module_texts("whatsapp_cloud", olds))
        # approved by Meta with the old text: it is the text Meta sends, kept
        follow_up.write({"body": old, "status": "approved"})
        self.assertFalse(Template._update_module_texts("whatsapp_cloud", olds))
        self.assertEqual(follow_up.body, old)
        # never submitted, or refused by Meta: the new text, with its variables only
        for status in ("unknown", "rejected"):
            follow_up.write({"body": old, "status": status})
            self.assertEqual(len(follow_up.variable_ids), 2)
            self.assertEqual(Template._update_module_texts("whatsapp_cloud", olds), follow_up)
            self.assertEqual(follow_up.body, text)
            self.assertEqual(follow_up.variable_ids, variable, "The variable {{2}} is gone")
        # an authentication template: Meta writes its text, the history follows the module
        follow_up.write({"body": old, "status": "approved", "category": "authentication"})
        self.assertEqual(Template._update_module_texts("whatsapp_cloud", olds), follow_up)
        self.assertEqual(follow_up.body, text)
