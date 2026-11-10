from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.ocd_live.models.ocd_live_price_rule import RULE_DAY_FIELDS

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLivePriceRule(OcdLiveCommon):
    """Price of the hours: some hours cost more or less, as set by the team."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env["ocd.live.price.rule"]
        cls.discovery.list_price = 15000
        cls.duo.list_price = 27000
        # Evening of the test day, from 17:30: +25 %
        cls.evening = cls._rule("Evening", 25, hour_from=17.5, hour_to=22)

    @classmethod
    def _rule(cls, name, percent, **vals):
        days = {field: False for field in RULE_DAY_FIELDS}
        days[RULE_DAY_FIELDS[cls.day.weekday()]] = True
        return cls.env["ocd.live.price.rule"].create({"name": name, "percent": percent, **days, **vals})

    def _percent(self, start, mode="studio", product=None):
        return self.Rule._ocd_percent(self.company, start, mode, product or self.discovery)

    def test_rule_matches_its_days_hours_period_mode_and_packages(self):
        self.assertEqual(self._percent(self.starts[7]), 25, "19:00 is in the evening")
        self.assertEqual(self._percent(self.starts[1]), 0, "10:00 is not")
        self.assertEqual(
            self.Rule._ocd_percent(self.company, self.starts[7] + timedelta(days=1), "studio", self.discovery), 0,
            "Another day of the week",
        )
        self.evening.write({"date_from": self.day + timedelta(days=1)})
        self.assertEqual(self._percent(self.starts[7]), 0, "Before the period")
        self.evening.write({"date_from": self.day, "date_to": self.day, "mode": "remote"})
        self.assertEqual(self._percent(self.starts[7]), 0, "Only the remote lives")
        self.assertEqual(self._percent(self.starts[7], mode="remote"), 25)
        self.evening.write({"mode": "all", "product_tmpl_ids": [(6, 0, self.duo.product_tmpl_id.ids)]})
        self.assertEqual(self._percent(self.starts[7]), 0, "Only the Duo")
        self.assertEqual(self._percent(self.starts[7], product=self.duo), 25)

    def test_first_rule_of_the_list_applies(self):
        holidays = self._rule("Holidays", 40, sequence=1)
        self.assertEqual(self._percent(self.starts[7]), 40)
        holidays.active = False
        self.assertEqual(self._percent(self.starts[7]), 25)

    def test_booking_on_an_expensive_hour(self):
        booking = self.env["ocd.live.booking"]._ocd_book_from_website(
            self.vendor, self.discovery, self.starts[7], "studio"
        )
        order = booking.sale_order_id
        self.assertEqual(booking.price_percent, 25)
        hour_line = order.order_line.filtered(lambda l: l.product_id.ocd_product_kind == "hour_price")
        self.assertEqual(hour_line.price_unit, 3750, "25 % of the price of one live")
        self.assertEqual(order.amount_untaxed, 18750)
        order.action_confirm()
        self.assertEqual(booking.state, "confirmed")

    def test_cheaper_hour_and_package_of_several_lives(self):
        self._rule("Morning", -20, hour_to=10)
        booking = self.env["ocd.live.booking"]._ocd_book_from_website(self.vendor, self.duo, self.starts[0], "studio")
        hour_line = booking.sale_order_id.order_line.filtered(lambda l: l.product_id.ocd_product_kind == "hour_price")
        self.assertEqual(hour_line.price_unit, -2700, "20 % less on one live of the Duo (27 000 / 2)")

    def test_live_of_a_package_on_an_expensive_hour(self):
        credit = self._sell(self.duo).order_line.ocd_credit_ids
        Booking = self.env["ocd.live.booking"]
        # A normal hour: placed at once
        normal = Booking._ocd_book_with_credit(credit, self.starts[1], "studio")
        self.assertEqual(normal.state, "confirmed")
        # An expensive hour: held until the difference is paid
        held = Booking._ocd_book_with_credit(credit, self.starts[7], "studio")
        self.assertEqual(held.state, "draft")
        self.assertEqual(credit.remaining, 0, "The held live counts in the package")
        order = held.sale_order_id
        self.assertEqual(order.amount_untaxed, 3375, "25 % of one live of the Duo")
        order.action_confirm()
        self.assertEqual(held.state, "confirmed")
        self.assertEqual(held.credit_id, credit)

    def test_unpaid_difference_frees_the_live_of_the_package(self):
        credit = self._sell(self.discovery).order_line.ocd_credit_ids
        held = self.env["ocd.live.booking"]._ocd_book_with_credit(credit, self.starts[7], "studio")
        held.action_cancel()
        self.assertEqual(held.sale_order_id.state, "cancel")
        self.assertEqual(credit.remaining, 1)

    def test_cheaper_hour_gives_nothing_back_on_a_package(self):
        self._rule("Morning", -20, hour_to=10)
        credit = self._sell(self.discovery).order_line.ocd_credit_ids
        booking = self.env["ocd.live.booking"]._ocd_book_with_credit(credit, self.starts[0], "studio")
        self.assertEqual(booking.state, "confirmed")
        self.assertEqual(booking.price_percent, 0)

    def test_move_not_to_a_more_expensive_hour(self):
        credit = self._sell(self.duo).order_line.ocd_credit_ids
        booking = self.env["ocd.live.booking"]._ocd_book_with_credit(credit, self.starts[1], "studio")
        with self.assertRaises(UserError):
            booking._ocd_move(self.starts[7])
        booking._ocd_move(self.starts[2])
        self.assertEqual(booking.start_datetime, self.starts[2])
