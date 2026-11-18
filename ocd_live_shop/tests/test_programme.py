from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdProgramme(HttpCase, OcdShopCommon):
    """The programme of the lives (chantier 7, design ProgrammeSoirees): the next 7 days, the lives
    of now first, a TV guide on a computer, « Tell me » = « Follow »."""

    def _live(self, vendor, start, minutes=90, slot=0, **values):
        """A confirmed live of `vendor` at `start` (written directly: no slot of the studio)."""
        later = self.company._ocd_local_today() + timedelta(days=40)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": vendor.id, "start_datetime": self.company._ocd_slot_starts(later)[slot], "mode": "remote",
        })
        booking.write({"state": "confirmed", **values})
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [start, start + timedelta(minutes=minutes), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        return booking

    def test_the_programme_of_the_lives(self):
        now = fields.Datetime.now()
        self._live(self.brenda, now - timedelta(minutes=20))
        tomorrow = self._live(self.fatou, now + timedelta(days=1), slot=1)
        self.authenticate(None, None)
        self.assertIn("/lives/programme", self.url_open("/lives").text, "From the feed of the lives")
        page = self.url_open("/lives/programme?pays=tous").text
        self.assertEqual(page.count("o_ocd_programme_day "), 7, "7 days")
        self.assertIn("Live now", page)
        self.assertIn("Brenda Wax", page)
        self.assertNotIn("Fatou Karite", page, "Tomorrow")
        self.assertIn("o_ocd_guide", page, "The TV guide of the computers")
        self.assertIn(f"/ocd/suivre/{self.brenda.id}?", page, "The bell follows the vendor")
        day = fields.Date.to_string(tomorrow.start_datetime.date())
        page = self.url_open(f"/lives/programme?pays=tous&jour={day}").text
        self.assertIn("Fatou Karite", page)
        # A day out of the programme: today
        self.assertIn("Brenda Wax", self.url_open("/lives/programme?pays=tous&jour=2000-01-01").text)
        # Followed: the bell says it
        follower = self.env["ocd.vendor.follower"]._ocd_follow(self.brenda, self.estelle, lives=True, news=False,
                                                                source="programme")
        self.assertEqual(follower.source, "programme")
