from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged


from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveSettings(OcdLiveCommon):

    def test_closed_day_has_no_slot(self):
        field = ["ocd_open_mon", "ocd_open_tue", "ocd_open_wed", "ocd_open_thu", "ocd_open_fri",
                 "ocd_open_sat", "ocd_open_sun"][self.day.weekday()]
        self.company[field] = False
        self.assertEqual(self.company._ocd_slot_starts(self.day), [])
        self.assertEqual(self.env["ocd.live.booking"]._ocd_get_day_slots(self.day), [])
        with self.assertRaises(ValidationError):
            self._book(self.starts[0])

    def test_one_calendar_by_default(self):
        self.assertEqual(self.company.ocd_calendar_mode, "shared")
        self._book(self.starts[0], mode="studio")
        with self.assertRaises(ValidationError):
            self._book(self.starts[0], partner=self.other_vendor, mode="remote")

    def test_two_calendars(self):
        self.company.ocd_calendar_mode = "separate"
        studio = self._book(self.starts[0], mode="studio")
        remote = self._book(self.starts[0], partner=self.other_vendor, mode="remote")
        self.assertEqual(studio.slot_ids.calendar_key, "studio")
        self.assertEqual(remote.slot_ids.calendar_key, "remote")
        slots = self.env["ocd.live.booking"]._ocd_get_day_slots(self.day, mode="remote")
        self.assertFalse(slots[0]["available"])
        self.assertTrue(slots[1]["available"])
        with self.assertRaises(UserError, msg="Two lives share a slot"):
            self.company.ocd_calendar_mode = "shared"
        remote.action_cancel()
        self.company.ocd_calendar_mode = "shared"
        self.assertEqual(studio.slot_ids.calendar_key, "all")

    def test_moving_to_the_other_mode_changes_the_calendar(self):
        self.company.ocd_calendar_mode = "separate"
        booking = self._book(self.starts[2], mode="studio")
        booking.mode = "remote"
        self.assertEqual(booking.slot_ids.calendar_key, "remote")

    def test_find_the_vendor_by_phone(self):
        Partner = self.env["res.partner"]
        self.assertEqual(Partner._ocd_find_vendor_by_phone("670 00 00 02"), self.vendor)
        self.assertEqual(Partner._ocd_find_vendor_by_phone("+237 6 70 00 00 02"), self.vendor)
        self.assertFalse(Partner._ocd_find_vendor_by_phone("123"))
        self.assertFalse(Partner._ocd_find_vendor_by_phone("699 99 99 99"))

    def test_login_with_a_whatsapp_code(self):
        sent = []
        with patch.object(type(self.env["res.partner"]), "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
            self.assertTrue(self.vendor._ocd_send_login_code())
            self.assertFalse(self.vendor._ocd_send_login_code(), "One code per minute")
        code = sent[0]
        self.assertRegex(code, r"^\d{6}$")
        self.assertNotEqual(self.vendor.sudo().ocd_login_code_hash, code, "Only a hash is stored")
        wrong = "000000" if code != "000000" else "111111"
        self.assertFalse(self.vendor._ocd_check_login_code(wrong))
        self.assertTrue(self.vendor._ocd_check_login_code(code))
        self.assertFalse(self.vendor._ocd_check_login_code(code), "A code is used once")

    def test_login_code_expires_and_attempts_are_limited(self):
        sent = []
        with patch.object(type(self.env["res.partner"]), "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
            self.vendor._ocd_send_login_code()
        code = sent[-1]
        with freeze_time(fields.Datetime.now() + timedelta(minutes=11)):
            self.assertFalse(self.vendor._ocd_check_login_code(code))
        with freeze_time(fields.Datetime.now() + timedelta(minutes=2)), \
                patch.object(type(self.env["res.partner"]), "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
            self.vendor._ocd_send_login_code()
            code = sent[-1]
            wrong = "000000" if code != "000000" else "111111"
            for _attempt in range(5):
                self.vendor._ocd_check_login_code(wrong)
            self.assertFalse(self.vendor._ocd_check_login_code(code), "Locked after 5 wrong codes")

    def test_access_with_a_password(self):
        action = self.vendor.action_ocd_create_password_access()
        user = self.vendor.user_ids
        self.assertEqual(user.login, "+237670000002")
        self.assertTrue(user._is_portal())
        self.assertIn("/web/", action["params"]["message"])

    def test_voice_in_several_languages(self):
        prompt = self.env.ref("ocd_live.voice_prompt_day")
        french = self.env.ref("ocd_live.voice_language_fr")
        ewe = self.env.ref("ocd_live.voice_language_ee")
        data = prompt._ocd_voice_data(french)
        self.assertFalse(data["url"])
        self.assertEqual(data["speech_code"], "fr-FR")
        self.assertTrue(data["text"])
        self.assertEqual(prompt._ocd_voice_data(ewe), {"url": False, "text": False, "speech_code": False})
        recording = self.env["ocd.voice.recording"].create({
            "prompt_id": prompt.id,
            "language_id": ewe.id,
            "audio": "SUQzBA==",
            "audio_filename": "day-ee.mp3",
        })
        self.assertEqual(prompt._ocd_voice_data(ewe)["url"], f"/ocd/voix/audio/{recording.id}")

    def test_dashboard_figures(self):
        team = self.env["res.users"].create({
            "name": "Team", "login": "ocd_dashboard_team",
            "group_ids": [fields.Command.set(self.env.ref("ocd_live.group_ocd_live_user").ids)],
        })
        booking = self._book(self.starts[0], mode="remote")
        booking._ocd_confirm()
        data = self.env["ocd.live.dashboard"].with_user(team).get_dashboard_data()
        tiles = {tile["key"]: tile for tile in data["tiles"]}
        self.assertEqual(tiles["lives"]["action"]["res_model"], "ocd.live.booking")
        self.assertIn("passes", tiles)
        # The remote live without host is to do, and opens the booking
        todos = {todo["key"]: todo for todo in data["todos"]}
        todo = todos[f"host_{booking.id}"]
        self.assertEqual(todo["tone"], "grey")
        self.assertEqual(todo["action"]["res_id"], booking.id)
        # The paid booking is in the bar of today, the last of the 14 days
        self.assertEqual(len(data["chart"]["bars"]), 14)
        self.assertGreaterEqual(data["chart"]["bars"][-1]["value"], 1)
        ticks = data["chart"]["ticks"]
        self.assertEqual(len(ticks), 5)
        self.assertEqual(ticks[0], 0)
        self.assertGreaterEqual(ticks[-1], data["chart"]["bars"][-1]["value"])
        self.assertEqual([row["key"] for row in data["revenue"]["rows"]][:2], ["packages", "passes"])