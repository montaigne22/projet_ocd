import json
from datetime import timedelta
from unittest.mock import patch

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
