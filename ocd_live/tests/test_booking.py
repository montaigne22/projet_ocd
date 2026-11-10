from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveBooking(OcdLiveCommon):

    def test_live_starts_on_the_grid(self):
        booking = self._book(self.starts[0])
        self.assertEqual(booking.state, "draft")
        self.assertEqual(booking.slot_ids.mapped("start_datetime"), [self.starts[0]])
        self.assertEqual(booking.end_datetime, self.starts[0] + timedelta(hours=1.5))
        with self.assertRaises(ValidationError):
            self._book(self.starts[0] + timedelta(minutes=30))

    def test_no_double_booking(self):
        self._book(self.starts[2])
        with self.assertRaises(ValidationError):
            self._book(self.starts[2], partner=self.other_vendor, mode="remote")

    def test_four_hour_live_takes_three_slots(self):
        booking = self._book(self.starts[1], product=self.four_hours)
        self.assertEqual(booking.slot_count, 3)
        self.assertEqual(booking.slot_ids.mapped("start_datetime"), self.starts[1:4])
        with self.assertRaises(ValidationError):
            self._book(self.starts[3], partner=self.other_vendor)
        with self.assertRaises(ValidationError, msg="A 4-hour live cannot end after the closing"):
            self._book(self.starts[7], partner=self.other_vendor, product=self.four_hours)

    def test_cancel_releases_the_slot(self):
        booking = self._book(self.starts[4])
        booking.action_cancel()
        self.assertEqual(booking.state, "cancelled")
        self.assertFalse(booking.slot_ids)
        self.assertTrue(self._book(self.starts[4], partner=self.other_vendor))

    def test_move_a_live(self):
        booking = self._book(self.starts[0])
        self._book(self.starts[1], partner=self.other_vendor)
        with self.assertRaises(ValidationError):
            booking.start_datetime = self.starts[1]
        booking.start_datetime = self.starts[5]
        self.assertEqual(booking.slot_ids.mapped("start_datetime"), [self.starts[5]])

    def test_booking_before_the_opening(self):
        self.company.ocd_booking_open_date = self.day + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self._book(self.starts[0])

    def test_website_booking_confirmed_by_the_payment(self):
        booking = self.env["ocd.live.booking"]._ocd_book_from_website(
            self.vendor, self.discovery, self.starts[3], "studio", "rack"
        )
        order = booking.sale_order_id
        self.assertTrue(order)
        self.assertEqual(booking.state, "draft")
        self.assertTrue(booking.hold_until)
        self.assertFalse(order.require_signature)
        self.assertEqual(order.prepayment_percent, 1.0)
        self.assertTrue(order._has_to_be_paid())
        message_count = len(self.env.ref("ocd_live.channel_lives").message_ids)
        order.action_confirm()
        self.assertEqual(booking.state, "confirmed")
        self.assertFalse(booking.hold_until)
        self.assertEqual(booking.credit_id.quantity, 1)
        self.assertEqual(booking.credit_id.remaining, 0)
        self.assertEqual(booking.credit_id.state, "used")
        self.assertEqual(len(self.env.ref("ocd_live.channel_lives").message_ids), message_count + 1)

    def test_package_lives_become_credits(self):
        order = self._sell(self.duo)
        credit = order.order_line.ocd_credit_ids
        self.assertEqual(credit.quantity, 2)
        self.assertEqual(credit.remaining, 2)
        Booking = self.env["ocd.live.booking"]
        first = Booking._ocd_book_with_credit(credit, self.starts[0], "studio")
        self.assertEqual(first.state, "confirmed")
        Booking._ocd_book_with_credit(credit, self.starts[2], "remote")
        self.assertEqual(credit.remaining, 0)
        self.assertEqual(self.vendor.ocd_lives_remaining, 0)
        with self.assertRaises(UserError):
            Booking._ocd_book_with_credit(credit, self.starts[4], "studio")
        first.action_cancel()
        self.assertEqual(credit.remaining, 1, "A cancelled live goes back to the credit")

    def test_monthly_credits_expire(self):
        order = self._sell(self.monthly)
        credit = order.order_line.ocd_credit_ids
        self.assertEqual(credit.quantity, 8)
        self.assertEqual(credit.date_expiry, fields.Date.today() + timedelta(days=30))
        credit.date_expiry = fields.Date.today() - timedelta(days=1)
        self.env["ocd.live.credit"]._cron_expire()
        self.assertEqual(credit.state, "expired")
        with self.assertRaises(UserError):
            self.env["ocd.live.booking"]._ocd_book_with_credit(credit, self.starts[0], "studio")

    def test_unpaid_slot_is_released(self):
        booking = self.env["ocd.live.booking"]._ocd_book_from_website(
            self.vendor, self.discovery, self.starts[6], "remote"
        )
        order = booking.sale_order_id
        booking.hold_until = fields.Datetime.now() - timedelta(minutes=1)
        self.env["ocd.live.booking"]._cron_release_expired_holds()
        self.assertEqual(booking.state, "cancelled")
        self.assertEqual(order.state, "cancel")
        self.assertTrue(self._book(self.starts[6], partner=self.other_vendor))

    def test_late_payment_keeps_the_lives_as_credit(self):
        booking = self.env["ocd.live.booking"]._ocd_book_from_website(
            self.vendor, self.discovery, self.starts[6], "studio"
        )
        order = booking.sale_order_id
        booking.action_cancel()
        order.action_draft()
        order.action_confirm()
        credit = order.order_line.ocd_credit_ids
        self.assertEqual(booking.state, "cancelled")
        self.assertEqual(credit.remaining, 1)

    def test_remote_live_asks_for_a_host(self):
        booking = self._book(self.starts[5], mode="remote")
        booking._ocd_confirm()
        host_type = self.env.ref("ocd_live.mail_activity_type_choose_host")
        self.assertTrue(booking.needs_host)
        self.assertEqual(booking.activity_ids.activity_type_id, host_type)
        booking.animatrice_id = self.host
        self.assertFalse(booking.needs_host)
        self.assertFalse(booking.activity_ids.filtered(lambda a: a.activity_type_id == host_type))
        self.assertIn(booking, self.env["ocd.live.booking"].search([("needs_host", "=", False)]))

    def test_day_slots_for_the_website(self):
        self._book(self.starts[1])
        slots = self.env["ocd.live.booking"]._ocd_get_day_slots(self.day)
        self.assertEqual(len(slots), 9)
        self.assertEqual(slots[0]["label"], "08:30")
        self.assertTrue(slots[0]["available"])
        self.assertFalse(slots[1]["available"])
        self.assertTrue(slots[1]["taken"])
        long_slots = self.env["ocd.live.booking"]._ocd_get_day_slots(self.day, slot_count=3)
        self.assertFalse(long_slots[0]["available"], "08:30 + 3 slots crosses the taken 10:00 slot")
        self.assertTrue(long_slots[2]["available"])
        self.assertFalse(long_slots[7]["available"], "Not enough slots before the closing")
        counts = self.env["ocd.live.booking"]._ocd_get_free_counts([self.day])
        self.assertEqual(counts[self.day], 8)

    def test_confirmed_live_cannot_be_deleted(self):
        booking = self._book(self.starts[0])
        booking._ocd_confirm()
        with self.assertRaises(UserError):
            booking.unlink()
