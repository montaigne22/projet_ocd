from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.whatsapp_cloud.tests.common import REQUEST, mock_response
from odoo.addons.whatsapp_cloud_call import const

from .common import WhatsAppCallCommon


@tagged("post_install", "-at_install")
class TestCallSettings(WhatsAppCallCommon):

    def test_payload_sip_server_and_hours(self):
        payload = self.account._call_settings_payload()["calling"]
        self.assertEqual(payload["status"], "ENABLED")
        self.assertEqual(payload["call_icon_visibility"], "DEFAULT")
        self.assertEqual(payload["callback_permission_status"], "ENABLED")
        self.assertEqual(payload["sip"], {
            "status": "ENABLED",
            "servers": [{"hostname": "calls.example.com", "port": 5061}],
            "webhook_delivery": "ENABLED",
        })
        # in "calling": Meta refuses it in "sip" ("Unexpected key ... on param calling.sip")
        self.assertEqual(payload["srtp_key_exchange_protocol"], "SDES")
        # no opening hours: the calls at any time
        self.assertEqual(payload["call_hours"], {"status": "DISABLED"})

    def test_payload_calls_disabled(self):
        self.account.call_enabled = False
        payload = self.account._call_settings_payload()["calling"]
        self.assertEqual(payload["status"], "DISABLED")
        self.assertEqual(payload["sip"]["status"], "DISABLED")
        self.assertNotIn("srtp_key_exchange_protocol", payload, "SDES only with the SIP server enabled")

    def test_payload_needs_the_call_server(self):
        self.env["ir.config_parameter"].sudo().set_str(const.PARAM_HOST, "")
        with self.assertRaises(UserError):
            self.account._call_settings_payload()

    def test_call_hours_from_the_opening_hours(self):
        # Monday to Friday, 8:00 to 12:00 and 13:00 to 17:00 (a new schedule of Odoo 20 only
        # has hours a day, without the times: see test_call_hours_without_times)
        calendar = self.env["resource.calendar"].create({
            "name": "Team",
            "attendance_ids": [
                (0, 0, {"dayofweek": day, "hour_from": start, "hour_to": end})
                for day in "01234" for start, end in ((8.0, 12.0), (13.0, 17.0))
            ],
        })
        self.account.resource_calendar_id = calendar
        self.account.company_id.tz = "Africa/Lome"
        hours = self.account._call_hours_payload()
        self.assertEqual(hours["status"], "ENABLED")
        self.assertEqual(hours["timezone_id"], "Africa/Lome")
        days = {period["day_of_week"] for period in hours["weekly_operating_hours"]}
        self.assertIn("MONDAY", days)
        self.assertNotIn("SUNDAY", days)
        for period in hours["weekly_operating_hours"]:
            self.assertRegex(period["open_time"], r"^\d{4}$")
            self.assertLess(period["open_time"], period["close_time"])
        per_day = {}
        for period in hours["weekly_operating_hours"]:
            per_day[period["day_of_week"]] = per_day.get(period["day_of_week"], 0) + 1
        self.assertLessEqual(max(per_day.values()), 2, "Meta takes 2 periods a day at most")
        self.assertIn({"day_of_week": "MONDAY", "open_time": "1300", "close_time": "1700"},
                      hours["weekly_operating_hours"])

    def test_call_hours_without_times(self):
        """Opening hours with only a number of hours a day (the default in Odoo 20 for a new
        schedule): not sent to Meta, a warning says how to set the times."""
        calendar = self.env["resource.calendar"].create({
            "name": "Team, hours only",
            "attendance_ids": [
                (0, 0, {"dayofweek": day, "duration_hours": 10.0}) for day in "012345"
            ],
        })
        self.assertTrue(calendar.attendance_ids[0].duration_based)
        self.account.resource_calendar_id = calendar
        self.assertTrue(self.account.call_hours_warning)
        with self.assertRaises(UserError):
            self.account._call_hours_payload()
        # calls at any time: nothing to warn about
        self.account.call_use_hours = False
        self.assertFalse(self.account.call_hours_warning)
        self.assertEqual(self.account._call_hours_payload(), {"status": "DISABLED"})
        # the times set on each day: sent
        self.account.call_use_hours = True
        calendar.attendance_ids.write({"hour_from": 9.0, "hour_to": 19.0})
        self.assertFalse(calendar.attendance_ids.filtered("duration_based"))
        self.assertFalse(self.account.call_hours_warning)
        hours = self.account._call_hours_payload()
        self.assertEqual(hours["status"], "ENABLED")
        self.assertIn({"day_of_week": "SATURDAY", "open_time": "0900", "close_time": "1900"},
                      hours["weekly_operating_hours"])

    def test_merge_periods(self):
        day = datetime(2026, 11, 23)

        def at(hour, minute=0):
            return day.replace(hour=hour, minute=minute)

        merge = self.env["whatsapp.account"]._call_merge_periods
        self.assertEqual(merge([(at(8), at(12)), (at(13), at(17))]), [("0800", "1200"), ("1300", "1700")])
        self.assertEqual(merge([(at(8), at(12)), (at(12), at(17))]), [("0800", "1700")])
        # 3 periods: the shortest break is filled
        self.assertEqual(
            merge([(at(8), at(10)), (at(10, 30), at(12)), (at(14), at(18))]),
            [("0800", "1200"), ("1400", "1800")],
        )

    def test_send_and_read_settings(self):
        answers = [
            mock_response({"success": True}),
            mock_response({"calling": {
                "status": "ENABLED",
                "sip": {"status": "ENABLED", "servers": [
                    {"hostname": "calls.example.com", "sip_user_password": "new-password"},
                ]},
            }}),
        ]
        with patch(REQUEST, side_effect=answers) as request:
            self.account.action_call_send_settings()
        post, get = request.call_args_list
        self.assertEqual(post.args, ("POST", "https://graph.facebook.com/v26.0/1110001/settings"))
        self.assertEqual(post.kwargs["json"]["calling"]["status"], "ENABLED")
        self.assertEqual(get.kwargs["params"], {"include_sip_credentials": "true"})
        self.assertEqual(self.account.call_meta_state, "ok")
        self.assertEqual(self.account.sudo().call_sip_password, "new-password")

    def test_restrictions_of_meta(self):
        answer = mock_response({"calling": {
            "status": "ENABLED",
            "restrictions": {"restrictions_list": [{
                "type": "RESTRICTED_USER_INITIATED_CALLING",
                "reason": "Low call quality",
                "expiration": 1798761600,
            }]},
        }})
        with patch(REQUEST, return_value=answer):
            self.account.action_call_read_settings()
        self.assertEqual(self.account.call_meta_state, "restricted")
        self.assertIn("Low call quality", self.account.call_meta_message)

    def test_error_of_meta(self):
        answer = mock_response({"error": {"code": 138039, "message": "Not eligible"}}, status=400)
        with patch(REQUEST, return_value=answer):
            self.account.action_call_send_settings()
        self.assertEqual(self.account.call_meta_state, "error")

    def test_changed_settings_to_send(self):
        self.account.call_meta_state = "ok"
        self.account.call_icon_visibility = "DISABLE_ALL"
        self.assertEqual(self.account.call_meta_state, "pending")

    def test_messaging_limit_warning(self):
        self.account.messaging_limit = "TIER_250"
        self.assertTrue(self.account.call_limit_warning)
        self.account.messaging_limit = "TIER_10K"
        self.assertFalse(self.account.call_limit_warning)

    def test_version_of_the_phone(self):
        """The phone shows the version of the module (in its menu and its diagnostic): kept
        equal to the manifest, to tell which phone a browser loaded."""
        import ast
        import re

        from odoo.tools.misc import file_open
        with file_open("whatsapp_cloud_call/__manifest__.py") as manifest:
            version = ast.literal_eval(manifest.read())["version"]
        with file_open("whatsapp_cloud_call/static/src/softphone/softphone_service.js") as script:
            phone = re.search(r'SOFTPHONE_VERSION = "([^"]+)"', script.read()).group(1)
        self.assertEqual(phone, version, "Raise SOFTPHONE_VERSION with the version of the module")

    def test_softphone_of_an_agent(self):
        config = self.agent._whatsapp_call_softphone()
        self.assertEqual(config["wss"], "wss://calls.example.com:7443")
        self.assertEqual(config["uri"], f"sip:agent{self.agent.id}@calls.example.com")
        self.assertTrue(config["password"])
        self.assertEqual(config["password"], self.agent._whatsapp_call_softphone()["password"])
        # no TURN secret: STUN only
        self.assertEqual(len(config["ice_servers"]), 1)
        self.env["ir.config_parameter"].sudo().set_str(const.PARAM_TURN_SECRET, "turn-secret")
        turn = self.agent._whatsapp_call_softphone()["ice_servers"][1]
        self.assertTrue(turn["username"].endswith(f":agent{self.agent.id}"))
        self.assertTrue(turn["credential"])
        self.assertIn("turns:calls.example.com:443?transport=tcp", turn["urls"])
        # nginx holds 443 on the call server: coturn on 5349
        self.env["ir.config_parameter"].sudo().set_str(const.PARAM_TURN_TLS_PORT, "5349")
        turn = self.agent._whatsapp_call_softphone()["ice_servers"][1]
        self.assertIn("turns:calls.example.com:5349?transport=tcp", turn["urls"])

    def test_no_softphone_for_others(self):
        other = self.env["res.users"].create({"name": "Not an Agent", "login": "not.agent"})
        self.assertIsNone(other._whatsapp_call_softphone())
        self.account.call_enabled = False
        self.assertIsNone(self.agent._whatsapp_call_softphone())
