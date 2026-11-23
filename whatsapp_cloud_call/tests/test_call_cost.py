from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.whatsapp_cloud.tests.common import REQUEST, mock_response

from .common import WhatsAppCallCommon


def permissions():
    return mock_response({
        "messaging_product": "whatsapp",
        "permission": {"status": "temporary", "expiration_time": 4102444800},
        "actions": [
            {"action_name": "send_call_permission_request", "can_perform_action": True},
            {"action_name": "start_call", "can_perform_action": True},
        ],
    })


@tagged("post_install", "-at_install")
class TestCallCost(WhatsAppCallCommon):
    """The cost of the calls of the company (phase 2.5): pulses of 6 seconds at the rate of the
    country called, the countries refused by Meta, the budget of the month, the longest call."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].sudo()._whatsapp_get_or_create(
            cls.account, "237670000000", None, cls.partner
        )
        cls.cameroon = cls.env.ref("base.cm")
        cls.account.write({
            "call_default_rate": 0.05,
            "call_rate_ids": [(0, 0, {"country_id": cls.cameroon.id, "price_per_minute": 0.012})],
        })

    def call(self, channel=None):
        with patch(REQUEST, return_value=permissions()):
            action = (channel or self.channel).with_user(self.agent).whatsapp_action_call()
        return self.Call.browse(action["params"]["call_id"])

    def end(self, call, talk, cause="NORMAL_CLEARING", ended_by="customer"):
        login = f"agent{self.agent.id}"
        self.Call._server_outbound({"call": call.id, "agent": login, "uuid": f"uuid-{call.id}"})
        self.Call._server_event({"event": "answered", "call": str(call.id), "agent": login})
        self.Call._server_event({"event": "ended", "call": str(call.id), "agent": login, "outcome": "completed",
                                 "ended_by": ended_by, "talk": str(talk), "cause": cause})

    def test_pulses_of_6_seconds_at_the_rate_of_the_country(self):
        call = self.call()
        self.assertEqual(call.country_id, self.cameroon)
        self.assertEqual(call.call_rate, 0.012)
        self.assertEqual(call.currency_id, self.account.call_currency_id)
        self.assertEqual(call.billed_pulses, 0)
        self.end(call, 31)
        # 31 s: 6 pulses (a pulse begun is due), 36 s at 0.012 a minute
        self.assertEqual(call.billed_pulses, 6)
        self.assertAlmostEqual(call.cost, 0.0072)
        # the duration of Meta is the one billed
        self.Call._meta_process(self.account, {"calls": [{
            "id": "wacid.COST1", "event": "terminate", "direction": "BUSINESS_INITIATED",
            "to": "237670000000", "status": "COMPLETED", "duration": 29,
        }]})
        self.assertEqual(call.meta_duration, 29)
        self.assertEqual(call.billed_pulses, 5)
        self.assertAlmostEqual(call.cost, 0.006)
        self.assertEqual(self.account.call_month_count, 1)
        self.assertAlmostEqual(self.account._call_month_costs()[self.account.id][0], 0.006)
        self.assertAlmostEqual(self.account.call_month_cost, 0.01)  # shown to the cent

    def test_calls_not_answered_and_calls_of_customers_are_free(self):
        missed = self.call()
        login = f"agent{self.agent.id}"
        self.Call._server_outbound({"call": missed.id, "agent": login})
        self.Call._server_event({"event": "ended", "call": str(missed.id), "agent": login, "outcome": "missed",
                                 "ended_by": "customer", "talk": "0", "cause": "NO_ANSWER"})
        self.assertEqual((missed.billed_pulses, missed.cost), (0, 0))
        inbound = self.Call.create({
            "account_id": self.account.id, "direction": "inbound", "state": "completed", "duration": 60,
            "call_rate": 0.012, "number": "237670000000",
        })
        self.assertEqual((inbound.billed_pulses, inbound.cost), (0, 0))

    def test_country_of_the_number(self):
        Account = self.env["whatsapp.account"]
        self.assertEqual(Account._call_country("237670000000"), self.cameroon)
        self.assertEqual(Account._call_country("+228 90 00 00 01"), self.env.ref("base.tg"))
        self.assertFalse(Account._call_country(""))
        # without its own rate: the default one
        self.assertEqual(self.account._call_rate(self.env.ref("base.tg")), 0.05)

    def test_countries_refused_by_meta_are_not_called(self):
        Account = self.env["whatsapp.account"]
        self.assertEqual(Account._call_blocked_country("2348031234567"), "Nigeria")
        self.assertEqual(Account._call_blocked_country("15145550123"), "United States / Canada")
        self.assertIsNone(Account._call_blocked_country("237670000000"))
        nigeria = self.env["discuss.channel"].sudo()._whatsapp_get_or_create(
            self.account, "2348031234567", None, self.env["res.partner"].create({"name": "Ada"})
        )
        with patch(REQUEST) as request, self.assertRaisesRegex(UserError, "Nigeria"):
            nigeria.with_user(self.agent).whatsapp_action_call()
        request.assert_not_called()
        # nor by the call server, for a call prepared before
        call = self.call()
        call.number = "2348031234567"
        self.assertIn("error", self.Call._server_outbound({"call": call.id, "agent": f"agent{self.agent.id}"}))

    def test_budget_of_the_month(self):
        self.end(self.call(), 600)  # 100 pulses at 0.012 a minute: 0.12
        self.account.call_monthly_budget = 0.20
        self.assertFalse(self.account.call_budget_warning)
        self.account.call_monthly_budget = 0.14
        self.assertIn("80", self.account.call_budget_warning)
        self.account.call_monthly_budget = 0.10
        self.assertIn("spent", self.account.call_budget_warning)
        with patch(REQUEST) as request, self.assertRaisesRegex(UserError, "budget"):
            self.channel.with_user(self.agent).whatsapp_action_call()
        request.assert_not_called()
        # no limit
        self.account.call_monthly_budget = 0
        self.assertTrue(self.call())

    def test_longest_call_of_the_company(self):
        call = self.call()
        answer = self.Call._server_outbound({"call": call.id, "agent": f"agent{self.agent.id}"})
        self.assertEqual(answer["max_talk"], 1800)
        self.account.call_max_outbound_minutes = 0
        call2 = self.call()
        self.assertEqual(self.Call._server_outbound({"call": call2.id, "agent": f"agent{self.agent.id}"})["max_talk"], 0)
        # ended by the call server at the longest duration: told in the conversation
        call3 = self.call()
        self.end(call3, 1800, cause="ALLOTTED_TIMEOUT", ended_by="system")
        self.assertEqual(call3.ended_by, "system")
        self.assertIn("ended at the longest duration", str(call3.notice_message_id.body))

    def test_rates_entered_after_the_calls(self):
        self.account.write({"call_rate_ids": [(5, 0, 0)], "call_default_rate": 0})
        call = self.call()
        self.end(call, 60)
        self.assertEqual(call.cost, 0)
        self.account.call_rate_ids = [(0, 0, {"country_id": self.cameroon.id, "price_per_minute": 0.01})]
        self.account.action_call_recompute_costs()
        self.assertEqual(call.call_rate, 0.01)
        self.assertAlmostEqual(call.cost, 0.01)
        action = self.account.action_call_costs()
        self.assertEqual(action["res_model"], "whatsapp.call")
        self.assertIn(("account_id", "=", self.account.id), action["domain"])
