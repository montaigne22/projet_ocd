from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLivePlanning(OcdLiveCommon):
    """Planning of the week for the team (BoReservations)."""

    def _cells(self, data):
        return {cell["key"]: cell for row in data["rows"] for cell in row["cells"]}

    def _key(self, start):
        local = self.company._ocd_to_local(start)
        return f"{local.date().isoformat()}|{local.strftime('%H:%M')}"

    def test_cells_and_detail(self):
        held = self._book(self.starts[0], mode="studio", studio_need="table")
        remote = self._book(self.starts[2], partner=self.other_vendor, mode="remote")
        remote._ocd_confirm()
        data = self.env["ocd.live.planning"].get_planning_data(self.day.isoformat())
        self.assertEqual(len(data["days"]), 7)
        self.assertEqual(len(data["rows"]), 9)
        cells = self._cells(data)
        self.assertEqual(cells[self._key(self.starts[0])]["kind"], "held")
        self.assertEqual(cells[self._key(self.starts[1])]["kind"], "free")
        self.assertEqual(cells[self._key(self.starts[2])]["kind"], "remote")
        self.assertEqual(cells[self._key(self.starts[2])]["label"], self.other_vendor.name)
        detail = data["details"][self._key(self.starts[2])]
        self.assertEqual(detail["booking_id"], remote.id)
        self.assertTrue(detail["remote"])
        self.assertFalse(detail["host_id"])
        self.assertTrue(detail["can_cancel"])
        # The first live shown is the coming one
        self.assertEqual(data["default_key"], self._key(self.starts[0]))
        self.assertEqual(data["details"][self._key(self.starts[0])]["booking_id"], held.id)

    def test_four_hours_live_takes_its_slots(self):
        self._book(self.starts[3], product=self.four_hours, state="confirmed")
        cells = self._cells(self.env["ocd.live.planning"].get_planning_data(self.day.isoformat()))
        self.assertEqual(cells[self._key(self.starts[3])]["kind"], "studio")
        self.assertEqual(cells[self._key(self.starts[4])]["kind"], "studio")
        self.assertNotEqual(cells[self._key(self.starts[4])]["sub"], cells[self._key(self.starts[3])]["sub"])

    def test_team_moves_a_live(self):
        booking = self._book(self.starts[1], state="confirmed")
        booking.action_ocd_team_move(self.starts[5])
        self.assertEqual(booking.start_datetime, self.starts[5])
        self.assertEqual(booking.slot_ids.start_datetime, self.starts[5])

    def test_offer_free_slot_to_the_waiting_list(self):
        entry = self.env["ocd.live.waitlist"].create({"partner_id": self.other_vendor.id, "day": self.day, "mode": "studio"})
        count = self.env["ocd.live.planning"].ocd_offer_free_slot(self.starts[4])
        self.assertEqual(count, 1)
        self.assertEqual(entry.state, "notified")

    def test_payment_checked_by_a_manager(self):
        booking = self._book(self.starts[6])
        team = self.env["res.users"].create({
            "name": "Team member", "login": "ocd_planning_team",
            "group_ids": [(6, 0, self.env.ref("ocd_live.group_ocd_live_user").ids)],
        })
        with self.assertRaises(AccessError):
            booking.with_user(team).action_ocd_mark_paid()
        booking.action_ocd_mark_paid()
        self.assertEqual(booking.state, "confirmed")
