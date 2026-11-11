from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveAutomations(OcdLiveCommon):
    """The catalogue of the automations (BoAutomatisations): what it shows, and that its
    switches really stop what they say."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["res.users"].create({
            "name": "Esi Manager",
            "login": "esi.manager.autos",
            "group_ids": [Command.set([cls.env.ref("ocd_live.group_ocd_live_manager").id])],
        })
        cls.Automation = cls.env["ocd.automation"].with_user(cls.manager)

    def _row(self, page, code):
        return next(row for group in page["groups"] for row in group["rows"] if row["code"] == code)

    def test_catalogue(self):
        page = self.Automation.get_automations_page()
        keys = [group["key"] for group in page["groups"]]
        self.assertEqual(keys[0], "lives")
        self.assertEqual(keys[-1], "technical")
        kinds = {kind["kind"]: kind["count"] for kind in page["kinds"]}
        self.assertTrue(kinds["rule"] and kinds["cron"])
        row = self._row(page, "hold_release")
        self.assertTrue(row["locked"])
        self.assertEqual(row["status"], "Always on")
        self.assertTrue(row["actions"], "Then, in this order")
        booking = self._row(page, "booking_confirmed")
        self.assertFalse(booking["locked"])
        self.assertTrue(booking["active"])

    def test_only_the_managers(self):
        user = self.env["res.users"].create({
            "name": "Kofi", "login": "kofi.autos",
            "group_ids": [Command.set([self.env.ref("ocd_live.group_ocd_live_user").id])],
        })
        with self.assertRaises(AccessError):
            self.env["ocd.automation"].with_user(user).get_automations_page()

    def test_paused_rule_stops_the_message_to_the_team(self):
        automation = self.env.ref("ocd_live.automation_booking_confirmed")
        channel = self.company.ocd_lives_channel_id
        booking = self._book(self.starts[0])
        row = self.Automation.ocd_switch(automation.id, False)
        self.assertFalse(row["active"])
        self.assertIn("Paused", row["warning"])
        before = channel.message_ids
        booking._ocd_confirm()
        self.assertEqual(channel.message_ids, before, "Paused: no message in the channel")
        self.Automation.ocd_switch(automation.id, True)
        second = self._book(self.starts[1], partner=self.other_vendor)
        second._ocd_confirm()
        self.assertNotEqual(channel.message_ids, before)

    def test_cron_switch_and_locked(self):
        automation = self.env.ref("ocd_live.automation_remote_host")
        self.Automation.ocd_switch(automation.id, False)
        self.assertFalse(automation.cron_id.active, "The scheduled action is archived")
        self.assertFalse(self.env["ocd.automation"]._ocd_enabled("remote_host"))
        self.Automation.ocd_switch(automation.id, True)
        self.assertTrue(automation.cron_id.active)
        with self.assertRaises(UserError):
            self.Automation.ocd_switch(self.env.ref("ocd_live.automation_hold_release").id, False)

    def test_runs_over_seven_days(self):
        automation = self.env.ref("ocd_live.automation_windows")
        self.env["ir.cron.progress"].create([{"cron_id": automation.cron_id.id} for _i in range(3)])
        count, _last, _label = automation._ocd_runs()
        self.assertEqual(count, 3)
        self.assertIn("3", automation._ocd_row()["history"])
        self.assertTrue(self.env["ocd.automation"]._ocd_enabled("not_in_the_catalogue"))
