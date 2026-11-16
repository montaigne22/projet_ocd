import re
from datetime import date, datetime

from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
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


@tagged("post_install", "-at_install")
class TestOcdVendorPlacesPages(HttpCase, OcdShopCommon):
    """« My stores » from the phone of the vendor (designs MesMagasins and MonMagasin)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_vendor_login": "link", "ocd_business_offered_all": True, "ocd_place_check": True,
                           "ocd_place_proof_required": True})
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        cls.brenda.write({"country_id": cls.env.ref("base.cm").id, "city_id": cls.akwa.city_id.id, "phone": "+237 670000001"})

    def _login(self, vendor):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{vendor._ocd_get_space_token()}")

    def _form(self, **values):
        return {
            "csrf_token": self.csrf_token(), "kind": "store", "name": "Brenda Wax Akwa", "city_id": self.akwa.city_id.id,
            "district_id": self.akwa.id, "landmark": "En face de la pharmacie du Port",
            **{f"open_{day}": "1" for day in range(6)}, **{f"from_{day}": "08:00" for day in range(7)},
            **{f"to_{day}": "19:00" for day in range(7)}, **values,
        }

    def test_a_store_from_the_phone(self):
        self._login(self.brenda)
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn('href="/ocd/espace/moi/magasins"', page)
        self.assertIn("No place yet", self.url_open("/ocd/espace/moi/magasins").text)
        page = self.url_open("/ocd/espace/moi/magasins/nouveau").text
        token = re.search(r'name="form_token" value="([0-9a-f]{32})"', page).group(1)
        self.assertIn('value="08:00"', page, "The hours proposed by the settings")
        # A store needs its front and its position (setting)
        page = self.url_open("/ocd/espace/moi/magasins/nouveau", data=self._form(form_token=token)).text
        self.assertIn("Add a photo of the front, with its sign.", page)
        self.assertIn("Take the position inside your store.", page)
        # Wrong hours, wrong phone, a position too vague
        page = self.url_open("/ocd/espace/moi/magasins/nouveau", data=self._form(
            form_token=token, from_2="19:00", to_2="08:00", phone="12", position_taken="1", latitude="4.05",
            longitude="9.69", accuracy="900",
        ), files={"photo": ("devanture.png", PNG, "image/png")}).text
        self.assertIn("the store opens before it closes", page)
        self.assertIn("This number is not a number of Cameroon", page)
        self.assertIn("The position is not precise enough (within 900 m)", page)
        self.assertIn('name="photo_kept"', page, "The front is kept for the next try")
        kept = re.search(r'name="photo_kept"[^>]*value="(\d+:[^"]+)"', page).group(1)
        form = self._form(form_token=token, phone="670 00 00 02", position_taken="1", latitude="4.0511",
                          longitude="9.6942", accuracy="15", photo_kept=kept)
        response = self.url_open("/ocd/espace/moi/magasins/nouveau", data=form, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        place = self.env["ocd.vendor.place"].search([("vendor_id", "=", self.brenda.id)])
        self.assertEqual((place.state, place.phone, place.position_accuracy), ("to_check", "+237 670000002", 15))
        self.assertTrue(place.photo)
        self.assertEqual(place._ocd_hours_lines(), ["Mon.–Sat.: 08:00–19:00", "Sun.: closed"])
        # Sent twice: one place
        self.url_open("/ocd/espace/moi/magasins/nouveau", data=form)
        self.assertEqual(self.env["ocd.vendor.place"].search_count([("vendor_id", "=", self.brenda.id)]), 1)
        page = self.url_open("/ocd/espace/moi/magasins").text
        self.assertIn("The team checks it", page)
        # The front: to its vendor only until the team puts it online
        photo = f"/ocd/magasin/{place.id}/photo"
        self.assertEqual(self.url_open(photo).status_code, 200)
        self.authenticate(None, None)
        self.assertEqual(self.url_open(photo).status_code, 404)
        place.action_ocd_approve()
        self.assertEqual(self.url_open(photo).status_code, 200)
        # The phone changes at once, the landmark goes back to the check
        self._login(self.brenda)
        edit = f"/ocd/espace/moi/magasins/{place.id}"
        self.assertIn("Change the place", self.url_open(edit).text)
        self.url_open(edit, data=self._form(phone="670 00 00 03"))
        self.assertEqual((place.state, place.phone), ("approved", "+237 670000003"))
        self.url_open(edit, data=self._form(landmark="Derrière le marché"))
        self.assertEqual(place.state, "to_check")
        # Another vendor cannot open it
        self._login(self.fatou)
        self.assertEqual(self.url_open(edit).status_code, 404)

    def test_a_home_and_the_place_of_the_parcels(self):
        self._login(self.brenda)
        self.url_open("/ocd/espace/moi/magasins/nouveau", data=self._form(kind="home", name="", landmark="Rue 1.234"))
        home = self.env["ocd.vendor.place"].search([("vendor_id", "=", self.brenda.id), ("kind", "=", "home")])
        self.assertEqual((home.state, home.name), ("approved", "My home"), "A home is shown at once (its district only)")
        store = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "district_id": self.akwa.id, "city_id": self.akwa.city_id.id,
        })
        page = self.url_open("/ocd/espace/moi/magasins").text
        self.assertIn("My parcels leave from", page, "Brenda is sold by OCD: a courier picks her parcels up")
        self.url_open("/ocd/espace/moi/magasins/depart", data={"csrf_token": self.csrf_token(), "place_id": store.id})
        self.assertEqual(self.brenda.ocd_departure_place_id, store)
        self.url_open(f"/ocd/espace/moi/magasins/{store.id}/retirer", data={"csrf_token": self.csrf_token()})
        self.assertFalse(store.active)
        self.assertFalse(self.brenda.ocd_departure_place_id, "No longer the place of the parcels")

    def test_the_customers_see_the_stores(self):
        self.brenda.write({"delivery_landmark": "Maison bleue derrière l'école", "ocd_sale_mode": "direct"})
        Place = self.env["ocd.vendor.place"]
        store = Place._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "district_id": self.akwa.id, "city_id": self.akwa.city_id.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
            "phone": "+237 670000009", "photo": BinaryBytes(PNG, filename="devanture.png"),
        })
        store._ocd_set_hours(self.company._ocd_place_default_intervals())
        home = Place._ocd_vendor_create(self.brenda, {"name": "Chez moi", "kind": "home", "district_id": self.akwa.id,
                                                      "city_id": self.akwa.city_id.id, "landmark": "Porte verte"})
        self.authenticate(None, None)
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertNotIn("Brenda Wax Akwa", page, "Not checked yet")
        self.assertNotIn("Maison bleue", page, "Never the landmark of the vendor")
        self.assertNotIn("Porte verte", page, "Never the landmark of a home")
        self.assertIn("By appointment: write before you come.", page)
        store.action_ocd_approve()
        self.dress.product_tmpl_id.is_published = True
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn("1 store in Douala", page)
        self.assertIn("En face de la pharmacie du Port", page)
        self.assertIn("https://www.google.com/maps/dir/?api=1&amp;destination=4.051100,9.694200", page)
        self.assertIn('href="tel:+237670000009"', page)
        self.assertIn(f'data-tap="/ocd/magasin/{store.id}/visite/itinerary"', page)
        self.assertIn(f"/ocd/magasin/{store.id}/photo", page)
        self.assertIn("Also in store: Akwa", self.url_open(self.dress.product_tmpl_id.website_url).text)
        # The visits: once per visitor every 10 minutes, never for a place not shown
        visit = f"/ocd/magasin/{store.id}/visite/itinerary"
        self.assertEqual(self.url_open(visit, data={"t": "1"}).status_code, 204)
        self.url_open(visit, data={"t": "1"})
        self.url_open(f"/ocd/magasin/{store.id}/visite/call", data={"t": "1"})
        self.url_open(f"/ocd/magasin/{store.id}/visite/hack", data={"t": "1"})
        self.assertEqual(store._ocd_week_taps()[store.id], {"itinerary": 1, "call": 1, "whatsapp": 0})
        store.action_ocd_refuse(self.env.ref("ocd_live_shop.refuse_reason_store_front"))
        self.url_open(f"/ocd/magasin/{store.id}/visite/whatsapp", data={"t": "1"})
        self.assertEqual(store._ocd_week_taps()[store.id]["whatsapp"], 0)
