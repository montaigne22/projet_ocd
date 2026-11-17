from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from ..models.vendor_nearby import distance_km, read_position
from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorNearby(HttpCase, OcdShopCommon):
    """The vendors near me (chantier 20, A.3 of the plan of « My products », design
    VacancesProximite): the shop and the lives of a country filtered by city and district, or
    from the nearest with the position of the phone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                           "ocd_place_proof_required": False})
        cls.Place = cls.env["ocd.vendor.place"]
        cls.douala = cls.akwa.city_id
        cls.deido = cls.env.ref("delivery_cameroon.district_douala_deido")
        cls.bastos = cls.env.ref("delivery_cameroon.district_yaounde_bastos")
        cls.paul = cls.env["res.partner"].create({
            "name": "Paul Mode", "ocd_is_vendor": True, "ocd_vendor_state": "approved", "ocd_sale_mode": "ocd",
            "ocd_delivery_mode": "pickup",
        })
        # Brenda: a store in Akwa with its position; Fatou: from home in Deido; Paul: a store in Yaounde
        cls.akwa_store = cls._place(cls.brenda, "Brenda Wax Akwa", cls.akwa, 4.0511, 9.6942)
        cls._place(cls.fatou, "Chez Fatou", cls.deido, kind="home")
        cls._place(cls.paul, "Paul Mode Bastos", cls.bastos, 3.8880, 11.5130)
        cls.coat = cls._product("Veste", 20000, cls.paul)
        for product in (cls.dress, cls.butter, cls.coat):
            product.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})

    @classmethod
    def _place(cls, vendor, name, district, lat=None, lon=None, kind="store"):
        values = {"name": name, "kind": kind, "district_id": district.id, "city_id": district.city_id.id}
        if lat is not None:
            values.update({"latitude": lat, "longitude": lon, "position_accuracy": 15})
        return cls.Place._ocd_vendor_create(vendor, values)

    def test_the_distance_and_the_order(self):
        self.assertAlmostEqual(distance_km(4.0511, 9.6942, 3.8880, 11.5130), 202, delta=3, msg="Douala to Yaounde")
        self.assertIsNone(read_position("north", "9.7"))
        self.assertIsNone(read_position("95", "9.7"))
        self.assertEqual(read_position("4.05", "9.70"), (4.05, 9.70))
        vendors = self.brenda | self.fatou | self.paul
        ranked = vendors._ocd_by_distance(4.05, 9.70)
        self.assertEqual([row[0] for row in ranked], [self.brenda, self.fatou, self.paul],
                         "The store near, then the vendor of the city without a position, then the far store")
        self.assertLess(ranked[0][1], 1)
        self.assertIsNone(ranked[1][1], "A home never shows its position")
        self.assertEqual(self.env["res.partner"]._ocd_distance_text(ranked[0][1]), "700 m")
        self.assertEqual(self.env["res.partner"]._ocd_distance_text(2.14), "2.1 km")
        # Near Yaounde: Paul first
        self.assertEqual(vendors._ocd_by_distance(3.87, 11.52)[0][0], self.paul)
        self.assertEqual(vendors._ocd_in_area(self.douala), self.brenda | self.fatou)
        self.assertEqual(vendors._ocd_in_area(self.douala, self.deido), self.fatou)

    def test_the_shop_by_city_and_from_the_nearest(self):
        self.authenticate(None, None)
        page = self.url_open("/shop").text
        self.assertIn('class="o_ocd_where"', page)
        self.assertIn(f'<option value="{self.douala.id}"', page)
        page = self.url_open(f"/shop?ville={self.douala.id}").text
        self.assertIn("Robe en wax", page)
        self.assertIn("Beurre de karite", page)
        self.assertNotIn("Veste", page)
        self.assertIn(f'<option value="{self.deido.id}"', page, "The districts of the city chosen")
        page = self.url_open(f"/shop?ville={self.douala.id}&quartier={self.deido.id}").text
        self.assertIn("Beurre de karite", page)
        self.assertNotIn("Robe en wax", page)
        # A district of another city is left aside
        page = self.url_open(f"/shop?ville={self.douala.id}&quartier={self.bastos.id}").text
        self.assertIn("Robe en wax", page)
        # From the nearest: the distances on the cards, the farthest last
        page = self.url_open("/shop?pres=1&lat=4.05&lon=9.70").text
        self.assertLess(page.index("Robe en wax"), page.index("Beurre de karite"))
        self.assertLess(page.index("Beurre de karite"), page.index("Veste"))
        self.assertIn("Akwa · 700 m", page)
        self.assertIn("it is not kept", page)
        self.assertIn("pres=1", page, "The categories keep the position")

    def test_the_lives_of_a_country_by_city(self):
        cameroon = self.env.ref("base.cm")
        Listing = self.env["ocd.directory.listing"]
        now = fields.Datetime.now()
        for vendor in (self.brenda, self.paul):
            Listing.create({
                "partner_id": vendor.id, "title": vendor.name, "url": f"https://www.tiktok.com/@{vendor.id}/live",
                "country_id": cameroon.id, "state": "published", "window_start": now - timedelta(hours=1),
                "window_end": now + timedelta(hours=1), "checked_at": now,
            })
        self.authenticate(None, None)
        page = self.url_open("/lives/cm").text
        self.assertIn("Paul Mode", page)
        self.assertIn("1 store · Akwa", page, "Where the vendor sells")
        page = self.url_open(f"/lives/cm?ville={self.douala.id}").text
        self.assertIn("Brenda Wax", page)
        self.assertNotIn("Paul Mode", page)
        # On holiday: said in the row
        self.brenda._ocd_start_holiday(self.brenda._ocd_today() + timedelta(days=4))
        self.assertIn("On holiday until", self.url_open("/lives/cm").text)
