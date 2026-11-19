from datetime import timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import BinaryBytes, mute_logger

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon
from odoo.addons.ocd_live_shop.tests.test_shop_pages import PNG

from ..hooks import post_init_hook


class OcdBusinessCommon(OcdShopCommon):
    """Brenda Wax buys OCD Business; the features offered to all have stopped."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            "ocd_business_offered_all": False, "ocd_business_launch_date": False, "ocd_business_launch_done": False,
            "ocd_business_launch_months": 2, "ocd_business_reminder_days": 7, "ocd_business_grace_days": 3,
            "ocd_studio_tz": "Africa/Douala",
        })
        cls.brenda.write({"phone": "+237 690001122", "tz": "Africa/Douala"})
        cls.Period = cls.env["ocd.business.period"]
        cls.month = cls.env.ref("ocd_business.product_business_1").product_variant_id
        cls.quarter = cls.env.ref("ocd_business.product_business_3").product_variant_id

    def _today(self):
        return self.brenda._ocd_business_today()

    def _order(self, product=None, vendor=None, confirm=True):
        order = self.env["sale.order"].create({
            "partner_id": (vendor or self.brenda).id,
            "require_signature": False,
            "prepayment_percent": 1.0,
            "order_line": [Command.create({"product_id": (product or self.month).id, "product_uom_qty": 1,
                                           "tax_ids": [Command.clear()]})],
        })
        if confirm:
            order.action_confirm()
        return order

    def _period(self, start_days, end_days, vendor=None, kind="offered"):
        vendor = vendor or self.brenda
        today = vendor._ocd_business_today()
        period = self.Period.create({
            "vendor_id": vendor.id, "kind": kind, "date_start": today + timedelta(days=start_days),
            "date_end": today + timedelta(days=end_days), "days": end_days - start_days + 1, "state": "active",
        })
        vendor._ocd_business_refresh()
        return period


@tagged("post_install", "-at_install")
class TestOcdBusiness(OcdBusinessCommon):
    """The formula (design OcdBusiness, « Pour que ça tienne en vrai »)."""

    def test_a_payment_once_and_no_day_lost(self):
        self.assertFalse(self.brenda._ocd_business())
        first = self._order()
        period = self.Period.search([("sale_order_id", "=", first.id)])
        self.assertEqual((period.kind, period.date_start, period.days), ("paid", self._today(), 30))
        self.assertEqual(self.brenda.ocd_business_until, self._today() + timedelta(days=29))
        self.assertTrue(self.brenda._ocd_business() and self.brenda._ocd_business_formula())
        # A second confirmation of the same payment adds nothing
        first.order_line._ocd_process_confirmed_lines()
        self.assertEqual(self.Period.search_count([("vendor_id", "=", self.brenda.id)]), 1)
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.Period.create({"vendor_id": self.brenda.id, "kind": "paid", "date_start": self._today(),
                                "date_end": self._today(), "days": 1, "sale_line_id": first.order_line.id})
        # Renewed before the end: the days follow, none is lost
        second = self._order(self.quarter)
        renewal = self.Period.search([("sale_order_id", "=", second.id)])
        self.assertEqual((renewal.date_start, renewal.state), (self._today() + timedelta(days=30), "scheduled"))
        self.assertEqual(self.brenda.ocd_business_until, self._today() + timedelta(days=119))
        # One invoice per payment
        self.assertEqual(first.invoice_ids.state, "posted")
        self.assertEqual(len(second.invoice_ids), 1)

    def test_the_duration_of_the_order_stays(self):
        order = self._order(confirm=False)
        self.env.ref("ocd_business.product_business_1").ocd_business_days = 10
        order.action_confirm()
        self.assertEqual(self.Period.search([("sale_order_id", "=", order.id)]).days, 10,
                         "The product of the order at its confirmation")

    def test_a_refund_takes_back_the_days_not_passed(self):
        first = self._order()
        second = self._order(self.quarter)
        later = self.Period.search([("sale_order_id", "=", second.id)])
        first._action_cancel()
        running = self.Period.search([("sale_order_id", "=", first.id)])
        self.assertEqual((running.date_end, running.state), (self._today(), "active"), "Ends today, never backwards")
        later.invalidate_recordset()
        self.assertEqual(later.date_start, self._today() + timedelta(days=1), "The next period comes closer")
        self.assertEqual(self.brenda.ocd_business_until, self._today() + timedelta(days=90))
        second._action_cancel()
        self.assertEqual(later.state, "cancelled")
        self.assertEqual(self.brenda.ocd_business_until, self._today())

    def test_a_payment_checked_by_hand_keeps_the_features(self):
        self._period(-20, -2)
        self.assertFalse(self.brenda._ocd_business())
        order = self._order(confirm=False)
        order._ocd_announce_payment("OM-12345")
        self.assertEqual(self.brenda.ocd_business_grace_until, self._today() + timedelta(days=1), "3 days after the end")
        self.assertTrue(self.brenda._ocd_business())
        note = self.brenda._ocd_business_space_note()
        self.assertEqual(note["kind"], "grace")
        order.action_confirm()
        paid = self.Period.search([("sale_order_id", "=", order.id)])
        self.assertEqual(paid.date_start, self._today() - timedelta(days=1), "From the end: the grace is paid")
        self.assertFalse(self.brenda.ocd_business_grace_until)
        # Too late: no grace any more
        self._period(-40, -10, vendor=self.fatou)
        late = self._order(vendor=self.fatou, confirm=False)
        late._ocd_announce_payment("OM-1")
        self.assertFalse(self.fatou.ocd_business_grace_until)
        # Refused: the grace stops
        self._period(-10, -1, vendor=self.herve)
        refused = self._order(vendor=self.herve, confirm=False)
        refused._ocd_announce_payment("OM-2")
        self.assertTrue(self.herve.ocd_business_grace_until)
        refused._action_cancel()
        self.assertFalse(self.herve.ocd_business_grace_until)

    def test_the_reminders_once_per_date_of_end(self):
        told = []
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_business_tell", autospec=True,
                          side_effect=lambda partner, event: told.append((partner.id, event))):
            period = self._period(-23, 6)
            self.env["res.partner"]._ocd_business_tell_ends()
            self.env["res.partner"]._ocd_business_tell_ends()
            self.assertEqual(told, [(self.brenda.id, "soon")])
            self.assertEqual(self.brenda._ocd_business_space_note()["kind"], "soon")
            period.date_end = self._today() + timedelta(days=1)
            self.brenda._ocd_business_refresh()
            self.env["res.partner"]._ocd_business_tell_ends()
            self.assertEqual(told[-1], (self.brenda.id, "last_call"))
            period.date_end = self._today() - timedelta(days=1)
            self.brenda._ocd_business_refresh()
            self.env["res.partner"]._ocd_business_tell_ends()
            self.env["res.partner"]._ocd_business_tell_ends()
            self.assertEqual([event for _id, event in told], ["soon", "last_call", "ended"])
            self.assertEqual(self.brenda._ocd_business_space_note()["kind"], "ended")
            # Offered to all: nothing is told
            self.company.ocd_business_offered_all = True
            period.date_end = self._today() + timedelta(days=3)
            self.brenda._ocd_business_refresh()
            self.env["res.partner"]._ocd_business_tell_ends()
            self.assertEqual(len(told), 3)
            self.assertFalse(self.brenda._ocd_business_space_note())

    def test_the_launch_once_and_nobody_loses_the_features(self):
        Place = self.env["ocd.vendor.place"]
        for name in ("Brenda Wax Akwa", "Brenda Wax Bonapriso"):
            Place.create({"name": name, "vendor_id": self.brenda.id, "kind": "store", "district_id": self.akwa.id,
                          "city_id": self.akwa.city_id.id, "state": "approved"})
        self.company.write({"ocd_business_offered_all": True, "ocd_business_launch_date": self.company._ocd_local_today()})
        told = []
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_business_tell", autospec=True,
                          side_effect=lambda partner, event: told.append((partner.id, event))):
            self.Period._cron_ocd_business()
            self.Period._cron_ocd_business()
        launch = self.Period.search([("vendor_id", "=", self.brenda.id), ("kind", "=", "launch")])
        self.assertEqual(launch.days, 60)
        self.assertFalse(self.Period.search([("vendor_id", "=", self.fatou.id)]), "One store: nothing to offer")
        self.assertEqual(told, [(self.brenda.id, "launch")])
        self.assertFalse(self.company.ocd_business_offered_all)
        self.assertTrue(self.company.ocd_business_launch_done)
        self.assertTrue(self.brenda._ocd_business())
        self.assertFalse(self.fatou._ocd_business())

    def test_the_team_offers_days_never_a_date(self):
        manager = new_test_user(self.env, "manager_business", groups="ocd_live.group_ocd_live_manager")
        offer = self.env["ocd.business.offer"].with_user(manager).create(
            {"vendor_id": self.brenda.id, "days": 10, "note": "Vendeuse testée"})
        offer.action_confirm()
        period = self.Period.search([("vendor_id", "=", self.brenda.id)])
        self.assertEqual((period.kind, period.note, period.user_id, period.days), ("offered", "Vendeuse testée", manager, 10))
        user = new_test_user(self.env, "user_business", groups="ocd_live.group_ocd_live_user")
        with self.assertRaises(AccessError):
            self.env["ocd.business.offer"].with_user(user).sudo().create(
                {"vendor_id": self.brenda.id, "days": 5, "note": "x"}).with_user(user).action_confirm()
        with self.assertRaises(UserError):
            self.env["ocd.business.offer"].with_user(manager).create(
                {"vendor_id": self.brenda.id, "days": 0, "note": "x"}).action_confirm()

    def test_the_dates_typed_by_hand_become_periods(self):
        self.brenda.ocd_business_until = self._today() + timedelta(days=20)
        post_init_hook(self.env)
        period = self.Period.search([("vendor_id", "=", self.brenda.id)])
        self.assertEqual((period.kind, period.date_end), ("offered", self._today() + timedelta(days=20)))
        self._order()
        self.assertEqual(self.brenda.ocd_business_until, self._today() + timedelta(days=50), "The paid days follow")

    def test_settings(self):
        sections = {section["key"]: section for section in self.env["ocd.live.settings"]._ocd_sections()}
        self.assertIn("business", sections)
        Settings = self.env["ocd.live.settings"]
        Settings._ocd_set_business_price("ocd_business.product_business_1", 12000)
        self.assertEqual(Settings._ocd_get_business_price("ocd_business.product_business_1"), 12000)


@tagged("post_install", "-at_install")
class TestOcdBusinessPages(HttpCase, OcdBusinessCommon):

    def _login(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")

    def test_buy_then_the_formula_runs(self):
        self._login()
        page = self.url_open("/ocd/espace/moi/business").text
        for text in ("Choose your formula", "3 months", "12 months", "Several stores", "For all, always"):
            self.assertIn(text, page)
        response = self.url_open("/ocd/espace/moi/business", data={
            "csrf_token": self.csrf_token(), "duree": self.quarter.id}, allow_redirects=False)
        self.assertIn("/ocd/payer/", response.headers["Location"])
        order = self.env["sale.order"].search([("partner_id", "=", self.brenda.id)], order="id desc", limit=1)
        self.assertEqual(order.order_line.product_id, self.quarter)
        # Back without paying, another duration: the same order, never a second one
        again = self.url_open("/ocd/espace/moi/business", data={
            "csrf_token": self.csrf_token(), "duree": self.month.id}, allow_redirects=False)
        self.assertEqual(again.headers["Location"], response.headers["Location"])
        self.assertEqual(order.order_line.product_id, self.month)
        self.assertEqual(order.order_line.price_unit, self.month.lst_price)
        self.url_open("/ocd/espace/moi/business", data={"csrf_token": self.csrf_token(), "duree": self.quarter.id})
        self.assertEqual(self.env["sale.order"].search_count([("partner_id", "=", self.brenda.id)]), 1)
        self.assertEqual(order.order_line.product_id, self.quarter)
        page = self.url_open(response.headers["Location"])
        self.assertEqual(page.status_code, 200, "The payment page opens")
        self.assertNotIn("Your hour", page.text, "A formula holds no hour")
        self.assertFalse(order.order_line.tax_ids, "The price of the settings is the price paid, as the pass")
        order.action_confirm()
        page = self.url_open("/ocd/espace/moi/business?paye=1").text
        self.assertIn("Paid: thank you", page)
        self.assertIn("Renew", page)
        self.assertIn("Invoice", page)
        # Close to the end: « My space » says it
        self.Period.search([("sale_order_id", "=", order.id)]).date_end = self._today() + timedelta(days=3)
        self.brenda._ocd_business_refresh()
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn("Your formula OCD Business ends on", page)
        self.assertIn("/ocd/espace/moi/business", page)

    def test_each_feature_kept_leads_to_the_formula(self):
        self._login()
        page = self.url_open("/ocd/espace/moi/equipe").text
        self.assertIn("The team comes with OCD Business", page)
        self.assertIn('href="/ocd/espace/moi/business"', page)
        # One store without the formula: the next ones come with it
        akwa = self.env.ref("delivery_cameroon.district_douala_akwa")
        self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "city_id": akwa.city_id.id, "district_id": akwa.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
            "position_accuracy": 15, "photo": BinaryBytes(PNG, filename="devanture.png"),
        })
        page = self.url_open("/ocd/espace/moi/magasins").text
        self.assertIn("More stores come with OCD Business", page)
        self.assertNotIn("Write to OCD Live for more", page)
        # With the formula, the limit of the settings speaks again
        self._period(0, 30)
        self.company.ocd_vendor_places_max = 1
        page = self.url_open("/ocd/espace/moi/magasins").text
        self.assertNotIn("More stores come with OCD Business", page)
        self.assertIn("Write to OCD Live for more", page)

    def test_the_page_for_the_shops(self):
        self.authenticate(None, None)
        page = self.url_open("/business").text
        self.assertIn("Your online shop, your stores, your deliveries", page)
        self.assertIn("per month", page)
