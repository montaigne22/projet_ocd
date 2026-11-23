from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from odoo.addons.whatsapp_cloud.tests.common import REQUEST, mock_response
from odoo.addons.whatsapp_cloud_call import const

from .common import WhatsAppCallCommon


def permissions(status="temporary", can_call=True):
    return mock_response({
        "messaging_product": "whatsapp",
        "permission": {"status": status, "expiration_time": 4102444800},
        "actions": [
            {"action_name": "send_call_permission_request", "can_perform_action": True},
            {"action_name": "start_call", "can_perform_action": can_call},
        ],
    })


@tagged("post_install", "-at_install")
class TestCallsOut(WhatsAppCallCommon, HttpCase):
    """The company calls a customer (phase 2.2): prepared by Odoo, placed by the phone of the
    agent, checked by the call server with Odoo, told by Meta."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].sudo()._whatsapp_get_or_create(
            cls.account, "237670000000", None, cls.partner
        )
        cls.headers = {"Authorization": "Bearer server-key"}
        cls.agent.password = "afi.agent.password"

    def prepare(self):
        with patch(REQUEST, return_value=permissions()):
            action = self.channel.with_user(self.agent).whatsapp_action_call()
        return self.Call.browse(action["params"]["call_id"]), action

    def test_call_prepared_by_odoo(self):
        call, action = self.prepare()
        self.assertEqual(action["tag"], "whatsapp_call_dial")
        self.assertEqual(action["params"]["number"], "+237670000000")
        self.assertEqual(call.direction, "outbound")
        self.assertEqual(call.display_name, f"Call to {self.partner.display_name}")
        self.assertEqual(call.state, "ringing")
        self.assertEqual(call.user_id, self.agent)
        self.assertEqual(call.channel_id, self.channel)
        self.assertFalse(call.server_seen)

    def test_call_refused_by_meta(self):
        channel = self.channel.with_user(self.agent)
        with patch(REQUEST, return_value=permissions("no_permission", can_call=False)), \
                self.assertRaisesRegex(UserError, "ask them"):
            channel.whatsapp_action_call()
        self.channel.whatsapp_call_permission = "temporary"
        self.channel.whatsapp_call_permission_until = fields.Datetime.now() + timedelta(days=2)
        with patch(REQUEST, return_value=permissions("temporary", can_call=False)), \
                self.assertRaisesRegex(UserError, "limit"):
            channel.whatsapp_action_call()
        self.assertFalse(self.Call.search_count([("direction", "=", "outbound")]))

    def test_call_server_checks_with_odoo(self):
        call, _action = self.prepare()
        login = f"agent{self.agent.id}"
        # another agent, or a call not prepared: refused
        self.assertIn("error", self.Call._server_outbound({"call": call.id, "agent": f"agent{self.agent2.id}"}))
        self.assertIn("error", self.Call._server_outbound({"call": "999999", "agent": login}))
        response = self.url_open("/whatsapp/call/server/outbound",
                                 data={"call": call.id, "agent": login, "uuid": "uuid-out"},
                                 headers=self.headers)
        lines = dict(line.split("=", 1) for line in response.text.strip().splitlines())
        self.assertEqual(lines["number"], "237670000000")
        self.assertEqual(lines["phone_number_id"], "1110001")
        self.assertEqual(lines["business_number"], "22890000001")
        self.assertEqual(lines["srtp"], "SDES")
        self.assertTrue(call.server_seen)
        self.assertEqual(call.server_uuid, "uuid-out")
        # placed once only
        self.assertIn("error", self.Call._server_outbound({"call": call.id, "agent": login}))
        # without the key of the call server: refused
        self.assertEqual(self.url_open("/whatsapp/call/server/outbound", data={"call": call.id}).status_code, 403)

    def test_prepared_call_expires(self):
        call, _action = self.prepare()
        call.flush_recordset()
        self.env.cr.execute("UPDATE whatsapp_call SET create_date = %s WHERE id = %s",
                            (fields.Datetime.now() - const.OUTBOUND_PREPARED_FOR - timedelta(seconds=5), call.id))
        call.invalidate_recordset()
        self.assertIn("error", self.Call._server_outbound({"call": call.id, "agent": f"agent{self.agent.id}"}))
        self.Call._cron_check_calls()
        self.assertEqual(call.state, "failed")
        self.assertEqual(call.end_cause, "NOT_PLACED")

    def test_answered_then_ended_and_told_by_meta(self):
        call, _action = self.prepare()
        login = f"agent{self.agent.id}"
        self.Call._server_outbound({"call": call.id, "agent": login, "uuid": "uuid-out"})
        # Meta tells the call (its ID is known only then): the same call
        self.Call._meta_process(self.account, {"calls": [
            {"id": "wacid.OUT1", "event": "call_created", "direction": "BUSINESS_INITIATED",
             "from": "22890000001", "to": "237670000000"},
        ]})
        self.assertEqual(call.wacid, "wacid.OUT1")
        self.assertTrue(call.meta_seen)
        self.assertEqual(self.Call.search_count([("direction", "=", "outbound")]), 1)
        self.Call._server_event({"event": "answered", "call": str(call.id), "agent": login})
        self.assertEqual(call.state, "answered")
        self.Call._server_event({"event": "ended", "call": str(call.id), "agent": login, "outcome": "completed",
                                 "ended_by": "customer", "talk": "75", "cause": "NORMAL_CLEARING"})
        self.assertEqual(call.state, "completed")
        self.assertEqual(call.duration, 75)
        self.assertIn("Call to the customer of 1 min 15 s, by Afi Agent.", str(call.notice_message_id.body))

    def test_no_answer_does_not_wait_for_the_team(self):
        call, _action = self.prepare()
        login = f"agent{self.agent.id}"
        self.Call._server_outbound({"call": call.id, "agent": login})
        state = self.channel.whatsapp_state
        self.Call._server_event({"event": "ended", "call": str(call.id), "agent": login, "outcome": "missed",
                                 "ended_by": "customer", "talk": "0", "cause": "NO_ANSWER"})
        self.assertEqual(call.state, "missed")
        self.assertIn("no answer", str(call.notice_message_id.body))
        self.assertEqual(self.channel.whatsapp_state, state)

    def test_phone_could_not_place_it(self):
        call, _action = self.prepare()
        self.authenticate("afi.agent", "afi.agent.password")
        self.make_jsonrpc_request("/whatsapp/call/softphone/dial_failed",
                                  {"call_id": call.id, "reason": "PHONE_NOT_CONNECTED"})
        self.assertEqual(call.state, "failed")
        self.assertEqual(call.end_cause, "PHONE_NOT_CONNECTED")

    def test_call_back_from_a_missed_call(self):
        missed = self.Call.browse(self.route("wacid.MISS")["call"])
        with patch(REQUEST, return_value=permissions()):
            action = missed.with_user(self.agent).action_call_back()
        self.assertEqual(action["tag"], "whatsapp_call_dial")
        self.assertEqual(self.Call.browse(action["params"]["call_id"]).channel_id, missed.channel_id)
