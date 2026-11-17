from datetime import date, datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdProductHold(HttpCase, OcdShopCommon):
    """Hold a piece to try it in a store (chantier 20, A.7 of the plan of « My products », design
    MettreDeCote): reserved at once, the vendor answers, the customer pays at the store only if
    they take it; one hold at a time at a vendor, no more after two absences."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                           "ocd_place_proof_required": False, "ocd_hold_enabled": True, "ocd_hold_hours": 24,
                           "ocd_hold_max_absences": 2, "ocd_vendor_login": "link"})
        cls.brenda.country_id = cls.env.ref("base.cm")  # the hours of her stores are the ones of Douala
        cls.dress.product_tmpl_id.write({"is_storable": True, "allow_out_of_stock_order": False, "is_published": True,
                                         "ocd_review_state": "approved"})
        cls.store = cls.env["ocd.vendor.place"]._ocd_vendor_create(cls.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": cls.akwa.id, "city_id": cls.akwa.city_id.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
        })
        cls.store._ocd_set_hours(cls.company._ocd_place_default_intervals())
        cls.dress._ocd_change_stock(3)
        cls.Hold = cls.env["ocd.product.hold"]

    def _hold(self, partner=None):
        with patch.object(type(self.Hold), "_ocd_notify_vendor", lambda holds: self.told.append("vendor")):
            return self.Hold._ocd_request(self.store, self.dress, partner or self.estelle)

    def setUp(self):
        super().setUp()
        self.told = []
        patcher = patch.object(type(self.Hold), "_ocd_notify_customer", lambda holds, event: self.told.append(event))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _free(self):
        return self.dress._ocd_free_qty(self.store.location_id)

    def test_held_at_once_then_bought_at_the_store(self):
        hold = self._hold()
        self.assertEqual((hold.state, hold.vendor_id, self.told), ("requested", self.brenda, ["vendor"]))
        self.assertEqual(hold.picking_id.state, "assigned")
        self.assertEqual(self._free(), 2, "The piece is no longer free for the other customers")
        with self.assertRaisesRegex(UserError, "You already hold"):
            self._hold()
        hold.action_ocd_accept()
        self.assertEqual((hold.state, self.told[-1]), ("accepted", "accepted"))
        hold.action_ocd_outcome("taken")
        self.assertEqual((hold.state, hold.picking_id.state), ("taken", "done"))
        self.assertEqual(self._free(), 2, "Bought: the piece left the stock of the store")
        self.assertEqual(self.dress.with_context(location=self.store.location_id.id).qty_available, 2)
        with self.assertRaisesRegex(UserError, "already over"):
            hold.action_ocd_refuse()
        # Another hold is possible now
        self.assertEqual(self._hold().state, "requested")

    def test_refused_cancelled_not_bought_free_the_piece(self):
        hold = self._hold()
        hold.action_ocd_refuse()
        self.assertEqual((hold.state, self.told[-1], hold.picking_id.state), ("refused", "refused", "cancel"))
        self.assertEqual(self._free(), 3)
        hold = self._hold()
        hold._ocd_cancel_by_customer()
        self.assertEqual((hold.state, self._free()), ("cancelled", 3))
        hold = self._hold()
        hold.action_ocd_outcome("not_taken")
        self.assertEqual((hold.state, self._free()), ("not_taken", 3))
        with self.assertRaises(UserError):
            self._hold().action_ocd_outcome("lost")

    def test_two_absences_then_unblocked(self):
        for _attempt in range(2):
            self._hold().action_ocd_outcome("no_show")
        self.assertEqual(self.Hold._ocd_absences(self.estelle, self.brenda), 2)
        with self.assertRaisesRegex(UserError, "no longer possible"):
            self._hold()
        self.assertEqual(self._hold(self.fatou).state, "requested", "Another customer still can")
        last = self.Hold.search([("partner_id", "=", self.estelle.id), ("state", "=", "no_show")], limit=1)
        last.action_ocd_unblock()
        self.assertEqual(self.Hold._ocd_absences(self.estelle, self.brenda), 0)
        self.assertEqual(self._hold().state, "requested")

    def test_the_deadline_and_the_time_over(self):
        hold = self._hold()
        # Monday 16 November 2026, 14:00 in Douala: until Tuesday 14:00, the store is open then
        self.assertEqual(hold._ocd_deadline_from(datetime(2026, 11, 16, 13, 0)), datetime(2026, 11, 17, 13, 0))
        # Saturday 21:00: Sunday 21:00 is closed, until the closing on Monday (19:00, 18:00 UTC)
        self.assertEqual(hold._ocd_deadline_from(datetime(2026, 11, 21, 20, 0)), datetime(2026, 11, 23, 18, 0))
        # Monday 05:00: Tuesday 06:00 is before the opening, until the closing that day
        self.assertEqual(hold._ocd_deadline_from(datetime(2026, 11, 16, 5, 0)), datetime(2026, 11, 17, 18, 0))
        self.store.closed_until = date(2026, 11, 17)
        self.assertEqual(hold._ocd_deadline_from(datetime(2026, 11, 16, 13, 0)), datetime(2026, 11, 18, 18, 0))
        self.store.closed_until = False
        hold.deadline = fields.Datetime.now() + timedelta(hours=26)
        self.assertRegex(hold._ocd_deadline_text(), r"^(tomorrow|\w+day \d+ \w+) at \d\d:\d\d$")
        hold.deadline = fields.Datetime.now() - timedelta(minutes=1)
        self.Hold._cron_ocd_holds()
        self.assertEqual((hold.state, self._free()), ("expired", 3))
        self.assertEqual(self.Hold._ocd_absences(self.estelle, self.brenda), 0, "Time over is not an absence")

    def test_only_where_it_is_offered(self):
        home = self.env["ocd.vendor.place"]._ocd_vendor_create(self.fatou, {"name": "Chez Fatou", "kind": "home"})
        self.assertFalse(self.Hold._ocd_offered(home))
        self.assertTrue(self.Hold._ocd_offered(self.store))
        with self.assertRaisesRegex(UserError, "cannot be held"):
            self.Hold._ocd_request(self.store, self.butter, self.estelle)
        self.dress._ocd_set_free_stock(0)
        with self.assertRaisesRegex(UserError, "No piece left"):
            self._hold()
        self.dress._ocd_set_free_stock(3)
        self.brenda._ocd_start_holiday(self.brenda._ocd_today() + timedelta(days=3))
        self.assertFalse(self.Hold._ocd_offered(self.store))
        self.brenda._ocd_end_holiday()
        self.company.ocd_hold_enabled = False
        with self.assertRaisesRegex(UserError, "does not hold pieces"):
            self._hold()

    # === THE PAGES === #

    def test_from_the_product_page_to_the_hold_page(self):
        self.authenticate(None, None)
        page = self.url_open(self.dress.product_tmpl_id.website_url).text
        self.assertIn("Hold it to try", page)
        self.assertIn(f"/ocd/essayer/magasin/{self.store.id}?produit={self.dress.id}", page)
        page = self.url_open(f"/ocd/essayer/magasin/{self.store.id}?produit={self.dress.id}").text
        self.assertIn("Brenda Wax Akwa keeps", page)
        self.assertIn("you pay only if you take it", page)
        self.assertIn('name="phone"', page, "The WhatsApp of an unknown customer")
        self.assertEqual(self.url_open(f"/ocd/essayer/magasin/{self.store.id}?produit={self.butter.id}").status_code, 404)
        form = {"csrf_token": self.csrf_token(), "product_id": self.dress.id, "country_id": self.env.ref("base.cm").id}
        page = self.url_open(f"/ocd/essayer/magasin/{self.store.id}", data={**form, "phone": "12"}).text
        self.assertIn("o_ocd_alert", page, "A number too short")
        response = self.url_open(f"/ocd/essayer/magasin/{self.store.id}", data={**form, "phone": "670 00 00 55"},
                                 allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:300])
        hold = self.Hold.search([("product_id", "=", self.dress.id)], limit=1)
        self.assertEqual((hold.state, hold.partner_id.phone), ("requested", "+237 670000055"))
        self.assertIn(f"/ocd/essayer/{hold.id}?t=", response.headers["Location"])
        url = f"/ocd/essayer/{hold.id}?t={hold.sudo().access_token}"
        page = self.url_open(url).text
        self.assertIn("Held at Brenda Wax Akwa until", page)
        self.assertIn("I no longer come", page)
        self.assertEqual(self.url_open(f"/ocd/essayer/{hold.id}?t=wrong").status_code, 404)
        # Twice: refused with the reason
        page = self.url_open(f"/ocd/essayer/magasin/{self.store.id}", data={**form, "phone": "670 00 00 55"}).text
        self.assertIn("You already hold", page)
        self.url_open(f"/ocd/essayer/{hold.id}/annuler?t={hold.sudo().access_token}", data={"csrf_token": self.csrf_token()})
        self.assertEqual(hold.state, "cancelled")
        self.assertIn("you no longer come", self.url_open(url).text)

    def test_the_vendor_answers_in_my_parcels(self):
        hold = self._hold()
        token = self.brenda._ocd_get_space_token()
        base = f"/ocd/livrer/{token}"
        self.authenticate(None, None)
        page = self.url_open(base).text
        self.assertIn("1 piece held to try", page)
        self.assertIn("To try · 1", page)
        page = self.url_open(f"{base}?vue=essayer").text
        self.assertIn("wants to try it", page)
        self.assertIn("Without an answer, the piece stays held", page)
        page = self.url_open(f"{base}/essai/{hold.id}/accept", data={"csrf_token": self.csrf_token()}).text
        self.assertEqual(hold.state, "accepted")
        self.assertIn("comes to try it", page)
        self.assertIn("How did it go?", page)
        self.url_open(f"{base}/essai/{hold.id}/no_show", data={"csrf_token": self.csrf_token()})
        hold = self._hold()
        page = self.url_open(f"{base}/essai/{hold.id}/no_show", data={"csrf_token": self.csrf_token()}).text
        self.assertIn("can no longer hold pieces at your stores", page)
        self.url_open(f"{base}/essai/{hold.id}/unblock", data={"csrf_token": self.csrf_token()})
        self.assertEqual(self.Hold._ocd_absences(self.estelle, self.brenda), 0)
        # Another vendor cannot answer it
        other = self._hold()
        response = self.url_open(f"/ocd/livrer/{self.fatou._ocd_get_space_token()}/essai/{other.id}/accept",
                                 data={"csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other.state, "requested")
