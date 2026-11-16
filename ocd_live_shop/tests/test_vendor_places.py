from datetime import date, datetime

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import BinaryBytes

from .common import OcdShopCommon
from .test_shop_pages import PNG


@tagged("post_install", "-at_install")
class TestOcdVendorPlaces(OcdShopCommon):
    """The places of the vendors (chantier 17): stores checked by the team, homes shown at once
    (the district only), open or closed at the hour of the store, OCD Business."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": True,
                           "ocd_place_proof_required": True})
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        # Douala: UTC+1
        cls.brenda.country_id = cls.env.ref("base.cm")
        cls.Place = cls.env["ocd.vendor.place"]

    def _store(self, **values):
        place = self.Place._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "city_id": self.akwa.city_id.id, "district_id": self.akwa.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942, "position_accuracy": 15,
            "photo": BinaryBytes(PNG, filename="devanture.png"), **values,
        })
        place._ocd_set_hours(self.company._ocd_place_default_intervals())
        return place

    def test_open_or_closed_at_the_hour_of_the_store(self):
        store = self._store()
        # Monday 16 November 2026, 10:00 in Douala (09:00 UTC)
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 16, 9, 0)), {"open": True, "label": "Open · closes at 19:00"})
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 16, 6, 0))["label"], "Closed · opens at 08:00")
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 16, 19, 30))["label"], "Closed · opens tomorrow at 08:00")
        # Saturday evening: closed on Sunday, open again on Monday
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 21, 19, 30))["label"], "Closed · opens Monday at 08:00")
        store.closed_until = date(2026, 11, 18)
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 16, 9, 0))["label"], "Closed until 18 November")
        # Closed through the 18th: open again on the 19th
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 18, 19, 30))["label"], "Closed until 18 November")
        self.assertEqual(store._ocd_open_state(datetime(2026, 11, 19, 5, 0))["label"], "Closed · opens at 08:00")
        self.assertEqual(store._ocd_hours_lines(), ["Mon.–Sat.: 08:00–19:00", "Sun.: closed"])

    def test_a_store_is_checked_a_home_is_shown_at_once(self):
        store = self._store()
        self.assertEqual(store.state, "to_check")
        self.assertFalse(self.Place._ocd_shown_places(self.brenda))
        home = self.Place._ocd_vendor_create(self.brenda, {"name": "Chez moi", "kind": "home", "district_id": self.akwa.id,
                                                           "city_id": self.akwa.city_id.id, "landmark": "Rue 1.234"})
        self.assertEqual(home.state, "approved", "Only its district is seen")
        self.assertEqual(home._ocd_address_line(), "Akwa, Douala", "Never the landmark of a home")
        store.action_ocd_approve()
        self.assertEqual(self.Place._ocd_shown_places(self.brenda), store | home)
        # The hours change at once; a new address goes back to the check (and is not shown meanwhile)
        store._ocd_vendor_update({"phone": "+237 670000002"})
        self.assertEqual(store.state, "approved")
        store._ocd_vendor_update({"landmark": "Derrière le marché"})
        self.assertEqual(store.state, "to_check")
        self.assertNotIn(store, self.Place._ocd_shown_places(self.brenda))
        # Refused with its reason; corrected, it is sent again with the reason for the team
        reason = self.env.ref("ocd_live_shop.refuse_reason_store_position")
        with self.assertRaises(UserError):
            store.action_ocd_refuse()
        store.action_ocd_refuse(reason)
        self.assertEqual(store._ocd_refusal_text(), reason.message)
        store._ocd_vendor_update({"latitude": 4.0512})
        self.assertEqual((store.state, store.previous_refusal), ("to_check", reason.name))
        item = next(i for i in self.env["ocd.live.verification"]._ocd_store_items() if i["id"] == store.id)
        self.assertIn("Sent again after a refusal", item["detail"])
        self.assertIn("Position taken on the spot, within 15 m", item["detail"])
        self.assertIn("4.051200,9.694200", item["open_url"])
        self.env["ocd.live.verification"].ocd_approve("store", store.id)
        self.assertEqual(store.state, "approved")

    def test_ocd_business_and_the_number_of_places(self):
        self.assertEqual(self.brenda._ocd_places_allowed(), 5, "Offered to all until the launch")
        first = self._store()
        second = self._store(name="Brenda Wax Marché central")
        (first | second).action_ocd_approve()
        self.company.ocd_business_offered_all = False
        self.assertEqual(self.brenda._ocd_places_allowed(), 1)
        self.assertEqual(self.Place._ocd_shown_places(self.brenda), first, "The second one is kept, not shown")
        with self.assertRaises(UserError):
            self._store(name="Brenda Wax Bonapriso")
        self.brenda.ocd_business_until = date(2099, 1, 1)
        self.assertEqual(self.Place._ocd_shown_places(self.brenda), first | second)
        self.brenda.ocd_places_max = 2
        self.assertEqual(self.brenda._ocd_places_left(), 0)
        # The parcels leave from the place chosen, else the only place
        self.assertFalse(self.brenda._ocd_departure_place(), "Two places: the vendor chooses")
        self.brenda.ocd_departure_place_id = second
        self.assertEqual(self.brenda._ocd_departure_place(), second)

    def test_the_visits_of_the_week(self):
        store = self._store()
        Tap = self.env["ocd.vendor.place.tap"]
        Tap.create([{"place_id": store.id, "kind": kind} for kind in ("itinerary", "itinerary", "call")])
        self.assertEqual(store._ocd_week_taps()[store.id], {"itinerary": 2, "call": 1, "whatsapp": 0})
