import json
from datetime import timedelta
from unittest.mock import patch

from markupsafe import Markup

from odoo import fields
from odoo.tests import tagged

from odoo.addons.whatsapp_cloud_call import const

from .common import WhatsAppCallCommon


@tagged("post_install", "-at_install")
class TestCalls(WhatsAppCallCommon):

    def test_route_creates_the_call_and_the_conversation(self):
        route = self.route()
        call = self.Call.browse(route["call"])
        self.assertEqual(call.state, "ringing")
        self.assertTrue(call.server_seen)
        self.assertEqual(call.number, "237670000000")
        self.assertEqual(call.partner_id, self.partner, "The known customer")
        self.assertEqual(call.channel_id.whatsapp_number, "237670000000")
        self.assertEqual(route["name"], "Awa Ngono")
        self.assertEqual(set(route["agents"]), {f"agent{self.agent.id}", f"agent{self.agent2.id}"})
        self.assertEqual(route["first"], [])
        self.assertEqual(route["max_wait"], 180)
        # asked again while the customer waits: the same call
        self.assertEqual(self.route()["call"], call.id)

    def test_route_agent_of_the_conversation_first(self):
        call = self.Call.browse(self.route()["call"])
        call.channel_id.whatsapp_user_id = self.agent2
        route = self.route()
        self.assertEqual(route["first"], [f"agent{self.agent2.id}"])
        self.assertEqual(route["agents"][0], f"agent{self.agent2.id}")

    def test_route_skips_busy_declined_and_unavailable(self):
        other = self.Call.browse(self.route("wacid.OTHER", "237690000000")["call"])
        self.Call._server_event({"event": "answered", "call": other.id, "agent": f"agent{self.agent.id}"})
        route = self.route()
        self.assertEqual(route["agents"], [f"agent{self.agent2.id}"], "Afi is in a call")
        call = self.Call.browse(route["call"])
        call.declined_user_ids = self.agent2
        self.assertEqual(self.route()["agents"], [])
        self.agent2.whatsapp_call_available = False
        call.declined_user_ids = False
        self.assertEqual(self.route()["agents"], [])

    def test_unknown_number_gets_a_contact_to_identify(self):
        call = self.Call.browse(self.route(number="22890111222")["call"])
        self.assertTrue(call.partner_id.whatsapp_to_identify)
        self.assertEqual(call.channel_id.whatsapp_partner_id, call.partner_id)

    def test_customer_with_a_hidden_number(self):
        """A customer who hides their number behind a WhatsApp username: Meta gives their
        WhatsApp user ID (BSUID), the call goes to their conversation all the same."""
        channel = self.env["discuss.channel"].sudo()._whatsapp_get_or_create(
            self.account, False, "CM.1349120865530", self.partner
        )
        route = self.Call._server_route({
            "wacid": "wacid.HIDDEN", "uuid": "uuid-hidden", "number": "",
            "user_ref": "CM.1349120865530", "phone_number_id": self.account.phone_number_id,
        })
        call = self.Call.browse(route["call"])
        self.assertFalse(call.number)
        self.assertEqual(call.user_ref, "CM.1349120865530")
        self.assertEqual(call.channel_id, channel)
        self.assertEqual(call.partner_id, self.partner)
        self.assertEqual(route["channel"], channel.id)
        # Meta tells the same call with the BSUID only
        self.Call._meta_process(self.account, {"calls": [
            {"id": "wacid.HIDDEN", "event": "terminate", "status": "COMPLETED", "duration": 12,
             "from_user_id": "CM.1349120865530"},
        ]})
        self.assertEqual(self.Call.search_count([("wacid", "=", "wacid.HIDDEN")]), 1)
        self.assertFalse(call.number)
        # an unknown customer who hides their number: a contact to identify, named after the ID
        self.Call._meta_process(self.account, {"calls": [
            {"id": "wacid.NEW", "event": "call_created", "direction": "USER_INITIATED",
             "from_user_id": "CM.NEW99", "from": "CM.NEW99"},
        ]})
        new = self.Call.search([("wacid", "=", "wacid.NEW")])
        self.assertFalse(new.number)
        self.assertEqual(new.partner_id.whatsapp_user_ref, "CM.NEW99")
        self.assertTrue(new.partner_id.whatsapp_to_identify)
        self.assertEqual(new.channel_id.whatsapp_user_ref, "CM.NEW99")
        self.assertIn("CM.NEW99", new.display_name)
        # the record of the call server carries it too
        self.Call._server_cdr({"variables": {"ocd_wacid": "wacid.CDR", "ocd_from": "",
                                             "ocd_user_ref": "CM.1349120865530",
                                             "ocd_pnid": self.account.phone_number_id,
                                             "ocd_outcome": "missed"}})
        cdr_call = self.Call.search([("wacid", "=", "wacid.CDR")])
        self.assertEqual(cdr_call.channel_id, channel)

    def test_answered_then_completed(self):
        call = self.Call.browse(self.route()["call"])
        self.Call._server_event({
            "event": "answered", "wacid": "wacid.ABC", "agent": f"agent{self.agent.id}", "wait": "25",
        })
        self.assertEqual(call.state, "answered")
        self.assertEqual(call.user_id, self.agent)
        self.assertEqual(call.wait_duration, 25)
        self.assertEqual(call.channel_id.whatsapp_user_id, self.agent, "The agent takes the conversation")
        self.Call._server_event({
            "event": "ended", "wacid": "wacid.ABC", "agent": f"agent{self.agent.id}",
            "outcome": "completed", "talk": "192", "wait": "25", "ended_by": "customer",
            "cause": "NORMAL_CLEARING",
        })
        self.assertEqual(call.state, "completed")
        self.assertEqual(call.duration, 192)
        self.assertEqual(call.ended_by, "customer")
        notice = call.notice_message_id
        self.assertIn("3 min 12 s", str(notice.body))
        self.assertIn("Afi Agent", str(notice.body))
        self.assertFalse(call.channel_id.whatsapp_waiting_since)
        # the record of the call afterwards changes nothing
        self.Call._server_cdr({"variables": {"ocd_wacid": "wacid.ABC", "ocd_outcome": "completed",
                                             "ocd_talk": "190"}})
        self.assertEqual(call.duration, 192)
        self.assertEqual(call.notice_message_id, notice)

    def test_agent_cut_off_gets_the_call_back(self):
        call = self.Call.browse(self.route()["call"])
        self.Call._server_event({"event": "answered", "call": call.id, "agent": f"agent{self.agent.id}"})
        self.Call._server_event({"event": "agent_lost", "call": call.id, "agent": f"agent{self.agent.id}"})
        self.assertEqual(call.state, "ringing")
        self.assertEqual(call.reconnect_count, 1)
        route = self.route()
        self.assertEqual(route["first"], [f"agent{self.agent.id}"], "Afi gets the call back first")
        self.Call._server_event({"event": "answered", "call": call.id, "agent": f"agent{self.agent.id}"})
        self.Call._server_event({"event": "ended", "call": call.id, "outcome": "completed", "talk": "60",
                                 "reconnects": "1"})
        self.assertIn("cut off 1 time", str(call.notice_message_id.body))

    def test_call_taken_answers_the_customer_who_waits(self):
        """A customer who waited for an answer is answered by the call taken: the figures of the
        conversations count it as the first answer of the agent."""
        call = self.Call.browse(self.route()["call"])
        channel = call.channel_id
        channel.whatsapp_waiting_since = fields.Datetime.now() - timedelta(minutes=12)
        self.Call._server_event({"event": "answered", "call": call.id, "agent": f"agent{self.agent.id}"})
        event = self.env["whatsapp.conversation.event"].search([("channel_id", "=", channel.id)])
        self.assertEqual((event.kind, event.user_id, event.minutes), ("answer", self.agent, 12))
        self.assertFalse(channel.whatsapp_waiting_since)

    def test_missed_call_waits_for_an_answer(self):
        call = self.Call.browse(self.route()["call"])
        self.Call._server_event({"event": "ended", "call": call.id, "outcome": "missed", "wait": "180",
                                 "ended_by": "customer"})
        self.assertEqual(call.state, "missed")
        self.assertTrue(call.channel_id.whatsapp_waiting_since, "The reminders of WhatsApp apply")
        self.assertIn("Missed call", str(call.notice_message_id.body))

    def test_voicemail_posted_in_the_conversation(self):
        call = self.Call.browse(self.route()["call"])
        self.Call._server_voicemail({"wacid": "wacid.ABC"}, b"RIFF....WAVEfmt ", "audio/wav")
        self.assertEqual(call.state, "voicemail")
        message = call.channel_id.message_ids.filtered(lambda m: m.attachment_ids)[:1]
        self.assertEqual(message.author_id, self.partner)
        self.assertEqual(message.attachment_ids, call.voicemail_attachment_id)
        self.assertFalse(
            self.env["whatsapp.message"].search([("mail_message_id", "=", message.id)]),
            "Never sent to the customer",
        )
        # sent again by the call server: once only
        self.Call._server_voicemail({"wacid": "wacid.ABC"}, b"RIFF....WAVEfmt ", "audio/wav")
        self.assertEqual(len(call.channel_id.message_ids.filtered(lambda m: m.attachment_ids)), 1)
        # played in the conversation like a voice message of Discuss, not a file to download first
        self.assertTrue(call.voicemail_attachment_id.voice_ids)

    def test_voicemail_in_the_language_of_the_team(self):
        """The line of the message left is for the team: in its language, whatever the language
        of the customer; the messages left before are repaired."""
        self.env["res.lang"]._activate_lang("fr_FR")
        (self.agent | self.agent2).lang = "fr_FR"
        call = self.Call.browse(self.route()["call"])
        self.Call.with_context(lang="en_US")._server_voicemail({"wacid": "wacid.ABC"}, b"RIFF....WAVEfmt ", "audio/wav")
        message = call.channel_id.message_ids.filtered(lambda m: m.attachment_ids)[:1]
        self.assertIn("Message vocal laissé après un appel.", str(message.body))
        # a message left before: a file, its line in English
        call.voicemail_attachment_id.voice_ids.unlink()
        message.body = Markup("<p>Voice message left after a call.</p>")
        self.Call._voicemail_repair()
        self.assertTrue(call.voicemail_attachment_id.voice_ids)
        self.assertIn("Message vocal laissé après un appel.", str(message.body))
        self.Call._voicemail_repair()  # twice: nothing more
        self.assertEqual(len(call.voicemail_attachment_id.voice_ids), 1)

    def test_event_without_route(self):
        """The call server could not reach Odoo when the call arrived: its record of the call
        creates it."""
        call = self.Call._server_cdr({"variables": {
            "ocd_wacid": "wacid.LATE", "ocd_from": "237670000000",
            "ocd_pnid": self.account.phone_number_id, "ocd_outcome": "completed",
            "ocd_answered_agent": f"agent{self.agent.id}", "ocd_talk": "30", "ocd_wait": "4",
        }})
        self.assertEqual(call.state, "completed")
        self.assertEqual(call.user_id, self.agent)
        self.assertEqual(call.partner_id, self.partner)

    def test_meta_webhook_and_lost_call(self):
        event = self.env["whatsapp.webhook.event"].create({
            "account_id": self.account.id,
            "field": "calls",
            "payload": json.dumps({
                "metadata": {"phone_number_id": self.account.phone_number_id},
                "calls": [{"id": "wacid.META", "event": "call_created", "direction": "USER_INITIATED",
                           "from": "237670000000", "to": "22890000001", "timestamp": "1795000000"}],
            }),
        })
        event._process()
        call = self.Call.search([("wacid", "=", "wacid.META")])
        self.assertTrue(call.meta_seen)
        self.assertFalse(call.server_seen)
        self.assertEqual(call.channel_id.whatsapp_partner_id, self.partner)
        # the call server never told it: lost after 10 minutes, the managers are alerted
        call.flush_recordset()
        self.env.cr.execute(
            "UPDATE whatsapp_call SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - const.LOST_AFTER - timedelta(minutes=1), call.id),
        )
        call.invalidate_recordset()
        self.Call._cron_check_calls()
        self.assertEqual(call.state, "lost")
        self.assertIn("Call lost", str(call.notice_message_id.body))
        self.assertTrue(any("(lost)" in str(m.body) for m in self.account.message_ids))
        # the record of the call server arrives after all: the real end
        self.Call._server_cdr({"variables": {"ocd_wacid": "wacid.META", "ocd_outcome": "completed",
                                             "ocd_talk": "40", "ocd_answered_agent": f"agent{self.agent.id}"}})
        self.assertEqual(call.state, "completed")
        self.assertIn("answered by Afi Agent", str(call.notice_message_id.body))

    def test_meta_and_server_same_call(self):
        call = self.Call.browse(self.route("wacid.SAME")["call"])
        self.Call._meta_process(self.account, {"calls": [
            {"id": "wacid.SAME", "event": "terminate", "status": "COMPLETED", "duration": 55,
             "from": "237670000000"},
        ]})
        self.assertEqual(self.Call.search_count([("wacid", "=", "wacid.SAME")]), 1)
        self.assertTrue(call.meta_seen)
        self.assertEqual(call.meta_duration, 55)

    def test_ended_at_meta_hangs_up_the_phones(self):
        """Meta tells the end of a call still going on the call server (its end did not reach
        it): the phones of the agents hang up; nothing when the call server ended it first."""
        call = self.Call.browse(self.route("wacid.GHOST")["call"])
        self.Call._server_event({"event": "answered", "wacid": "wacid.GHOST",
                                 "agent": f"agent{self.agent.id}"})
        Users = type(self.env["res.users"])
        terminate = {"calls": [{"id": "wacid.GHOST", "event": "terminate", "status": "COMPLETED",
                                "duration": 80, "from": "237670000000"}]}
        with patch.object(Users, "_bus_send") as bus:
            self.Call._meta_process(self.account, terminate)
        sent = [args for args, _kwargs in bus.call_args_list if args[0] == "whatsapp.call/update"]
        self.assertTrue(sent)
        self.assertTrue(all(payload["ended_at_meta"] and payload["id"] == call.id for _n, payload in sent))
        self.assertEqual(call.state, "answered")
        # ended by the call server first: nothing more to hang up
        self.Call._server_event({"event": "ended", "wacid": "wacid.GHOST", "outcome": "completed",
                                 "talk": "80", "ended_by": "customer"})
        with patch.object(Users, "_bus_send") as bus:
            self.Call._meta_process(self.account, terminate)
        self.assertFalse(bus.call_args_list)

    def test_thresholds_to_open_the_calls(self):
        """The thresholds of the trial on the account: calls cut, voicemail while an agent was
        free, average wait during the call hours."""
        self.assertFalse(self.account.call_stats_count)
        now = fields.Datetime.now()
        calls = self.Call
        for wacid in ("wacid.S1", "wacid.S2", "wacid.S3"):
            calls |= self.Call.browse(self.route(wacid)["call"])
        self.assertEqual(calls.mapped("available_agents"), [2, 2, 2])
        self.assertTrue(all(calls.mapped("in_hours")))
        calls[0].write({"state": "completed", "answer_date": now, "wait_duration": 30})
        calls[1].write({"state": "completed", "answer_date": now, "wait_duration": 50, "reconnect_count": 1})
        calls[2].write({"state": "voicemail", "wait_duration": 180})
        # seen by Meta only (lost): no agent known as free
        self.Call._meta_process(self.account, {"calls": [
            {"id": "wacid.S4", "event": "call_created", "direction": "USER_INITIATED", "from": "237670000001"},
        ]})
        self.Call.search([("wacid", "=", "wacid.S4")]).state = "lost"
        account = self.account
        account.invalidate_recordset()
        self.assertEqual(account.call_stats_count, 4)
        self.assertAlmostEqual(account.call_stats_cut_rate, 0.5)
        self.assertAlmostEqual(account.call_stats_voicemail_rate, 1 / 3)
        self.assertEqual(account.call_stats_wait, 40)
        self.assertFalse(account.call_stats_ok)

    def test_silence_of_the_call_server(self):
        server = self.env["whatsapp.call.server"]._get()
        server.last_seen = fields.Datetime.now() - timedelta(minutes=20)
        with patch.object(type(self.account), "_alert_managers") as alert:
            self.Call._cron_check_server()
            self.Call._cron_check_server()
        self.assertEqual(alert.call_count, 1, "Alerted once")
        server._report({"registrations": ["agent5"], "version": "1.10.12", "spool": "2"})
        self.Call._cron_check_server()
        self.assertFalse(server.silence_alerted)
        self.assertEqual((server.registration_count, server.spool), (1, 2))
        # the reports never write configuration parameters (their writes empty the caches)
        self.assertFalse(self.env["ir.config_parameter"].sudo().search([("key", "like", "server_last")]))

    def test_stale_call_ended(self):
        call = self.Call.browse(self.route()["call"])
        call.start_date = fields.Datetime.now() - const.STALE_AFTER - timedelta(minutes=5)
        self.Call._cron_check_calls()
        self.assertEqual(call.state, "missed")
        self.assertEqual(call.ended_by, "system")

    def test_info_panel(self):
        call = self.Call.browse(self.route()["call"])
        sections = call.channel_id._whatsapp_get_info_sections()
        calls = next(section for section in sections if section["title"] == "Calls")
        self.assertEqual(calls["items"][0]["id"], call.id)
