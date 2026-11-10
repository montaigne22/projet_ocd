from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.ocd_live.models.ocd_directory_listing import _platform_of

from .common import OcdLiveCommon

TIKTOK = "https://www.tiktok.com/@brendawax/live"


@tagged("post_install", "-at_install")
class TestOcdDirectory(OcdLiveCommon):

    def _give_pass(self, partner=None):
        return self._sell(self.pass_product, partner=partner).ocd_pass_ids

    def test_platform_of_links(self):
        self.assertEqual(_platform_of(TIKTOK), "tiktok")
        self.assertEqual(_platform_of("https://vm.tiktok.com/ZM123/"), "tiktok")
        self.assertEqual(_platform_of("https://fb.watch/abc/"), "facebook")
        self.assertEqual(_platform_of("https://youtu.be/xyz"), "youtube")
        self.assertFalse(_platform_of("http://www.tiktok.com/@a/live"), "Only https links")
        self.assertFalse(_platform_of("https://tiktok.com.evil.example/live"))
        self.assertFalse(_platform_of("javascript:alert(1)"))

    def test_pass_from_an_order(self):
        directory_pass = self._give_pass()
        today = fields.Date.today()
        self.assertEqual(directory_pass.state, "active")
        self.assertEqual(directory_pass.date_start, today)
        self.assertEqual(directory_pass.date_end, today + timedelta(days=29))
        self.assertTrue(self.vendor.ocd_pass_active)
        second = self._give_pass()
        self.assertEqual(second.state, "scheduled")
        self.assertEqual(second.date_start, today + timedelta(days=30), "No day is lost")
        self.vendor.invalidate_recordset(["ocd_pass_end_date"])
        self.assertEqual(self.vendor.ocd_pass_end_date, today + timedelta(days=59))

    def test_pass_states_and_reminder(self):
        directory_pass = self._give_pass()
        directory_pass.date_end = fields.Date.today() + timedelta(days=2)
        self.env["ocd.directory.pass"]._cron_send_reminders()
        self.assertTrue(directory_pass.reminder_sent)
        directory_pass.write({"date_start": fields.Date.today() - timedelta(days=40),
                              "date_end": fields.Date.today() - timedelta(days=1)})
        self.env["ocd.directory.pass"]._cron_update_states()
        self.assertEqual(directory_pass.state, "expired")
        self.vendor.invalidate_recordset(["ocd_pass_active"])
        self.assertFalse(self.vendor.ocd_pass_active)

    def test_link_needs_a_pass(self):
        with self.assertRaises(UserError):
            self.env["ocd.directory.listing"]._ocd_submit(self.vendor, TIKTOK)

    def test_bad_link_is_refused(self):
        self._give_pass()
        with self.assertRaises(UserError):
            self.env["ocd.directory.listing"]._ocd_submit(self.vendor, "https://example.com/live")
        with self.assertRaises(ValidationError):
            self.env["ocd.directory.listing"].create({"partner_id": self.vendor.id, "url": "http://tiktok.com/x"})

    def test_link_inside_and_outside_a_window(self):
        self._give_pass()
        self._give_pass(self.other_vendor)
        day = fields.Date.today() + timedelta(days=1)
        Listing = self.env["ocd.directory.listing"]
        with freeze_time(datetime.combine(day, datetime.min.time()) + timedelta(hours=9)):
            inside = Listing._ocd_submit(self.vendor, TIKTOK)
            self.assertEqual(inside.state, "to_check")
            self.assertEqual(inside.window_id, self.env.ref("ocd_live.window_morning"))
            self.assertEqual(inside.platform, "tiktok")
        with freeze_time(datetime.combine(day, datetime.min.time()) + timedelta(hours=12)):
            outside = Listing._ocd_submit(self.other_vendor, "https://www.facebook.com/fatou/live")
            self.assertEqual(outside.state, "queued")
            self.assertEqual(outside.window_id, self.env.ref("ocd_live.window_evening"))
            self.assertEqual(inside.state, "to_check")
            Listing._cron_update_windows()
            self.assertEqual(inside.state, "ended", "The morning window is over")
        with freeze_time(datetime.combine(day, datetime.min.time()) + timedelta(hours=18, minutes=5)):
            Listing._cron_update_windows()
            self.assertEqual(outside.state, "to_check")
            outside.action_publish()
            self.assertEqual(outside.state, "published")
            self.assertEqual(outside.checked_by_id, self.env.user)
        with freeze_time(datetime.combine(day, datetime.min.time()) + timedelta(hours=21, minutes=1)):
            Listing._cron_update_windows()
            self.assertEqual(outside.state, "ended")

    def test_one_open_link_per_vendor(self):
        self._give_pass()
        day = fields.Date.today() + timedelta(days=1)
        with freeze_time(datetime.combine(day, datetime.min.time()) + timedelta(hours=9)):
            self.env["ocd.directory.listing"]._ocd_submit(self.vendor, TIKTOK)
            with self.assertRaises(Exception), mute_logger("odoo.sql_db"), self.env.cr.savepoint():
                self.env["ocd.directory.listing"]._ocd_submit(self.vendor, TIKTOK)

    def test_refuse_with_a_reason(self):
        self._give_pass()
        day = fields.Date.today() + timedelta(days=1)
        with freeze_time(datetime.combine(day, datetime.min.time()) + timedelta(hours=9)):
            listing = self.env["ocd.directory.listing"]._ocd_submit(self.vendor, TIKTOK)
            reason = self.env.ref("ocd_live.refuse_reason_not_started")
            wizard = self.env["ocd.directory.listing.refuse"].create({
                "listing_ids": [fields.Command.set(listing.ids)],
                "reason_id": reason.id,
            })
            wizard.action_refuse()
            self.assertEqual(listing.state, "refused")
            self.assertEqual(listing.refuse_reason_id, reason)
            # The vendor can send a new link after a refusal
            self.assertTrue(self.env["ocd.directory.listing"]._ocd_submit(self.vendor, TIKTOK))
