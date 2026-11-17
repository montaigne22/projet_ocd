import json
import re
from html import unescape

from odoo import Command
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdStoreAvailability(HttpCase, OcdShopCommon):
    """What the customers see of the stock of each store (chantier 18, S.3 of the plan of « My
    products »): « Available », « Available · only 2 left » or « Sold out » store by store, never
    the exact count of a store; « Tell me when it is back » says in which stores it came back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False})
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        cls.bonapriso = cls.env.ref("delivery_cameroon.district_douala_bonapriso")
        colour = cls.env["product.attribute"].create({"name": "Couleur", "display_type": "color", "value_ids": [
            Command.create({"name": "Bleu", "html_color": "#2F6FB8"}), Command.create({"name": "Rouge", "html_color": "#C4162A"}),
        ]})
        size = cls.env["product.attribute"].create({"name": "Taille", "value_ids": [
            Command.create({"name": "S"}), Command.create({"name": "M"}),
        ]})
        cls.shirt = cls.env["product.template"].create({
            "name": "Chemise wax", "list_price": 9000, "ocd_vendor_id": cls.brenda.id, "is_storable": True,
            "allow_out_of_stock_order": False, "is_published": True, "ocd_review_state": "approved",
            "taxes_id": [Command.clear()],
            "attribute_line_ids": [
                Command.create({"attribute_id": colour.id, "value_ids": [Command.set(colour.value_ids.ids)]}),
                Command.create({"attribute_id": size.id, "value_ids": [Command.set(size.value_ids.ids)]}),
            ],
        })

    def _place(self, name, district, kind="store"):
        return self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": name, "kind": kind, "district_id": district.id, "city_id": district.city_id.id,
        })

    def _variant(self, colour, size):
        return self.shirt.product_variant_ids.filtered(
            lambda v: set(v.product_template_attribute_value_ids.mapped("name")) == {colour, size}
        )

    def _page(self, variant):
        values = ",".join(map(str, sorted(variant.product_template_attribute_value_ids.ids)))
        return self.url_open(f"{self.shirt.website_url}?v={values}").text

    def _data(self, html):
        return json.loads(unescape(re.search(r'data-variants="([^"]+)"', html).group(1)))

    def test_the_stock_of_each_store_on_the_page_of_the_product(self):
        akwa = self._place("Brenda Wax Akwa", self.akwa)
        bonapriso = self._place("Brenda Wax Bonapriso", self.bonapriso)
        home = self._place("Chez moi", self.akwa, kind="home")
        blue_m, red_m, blue_s = self._variant("Bleu", "M"), self._variant("Rouge", "M"), self._variant("Bleu", "S")
        blue_m._ocd_change_stock(2, akwa.location_id)
        blue_m._ocd_change_stock(7, bonapriso.location_id)
        red_m._ocd_change_stock(5, bonapriso.location_id)
        red_m._ocd_change_stock(3, home.location_id)
        page = self._page(blue_m)
        self.assertIn("In their stores", page)
        self.assertIn("Bleu, M", page)
        self.assertIn("Brenda Wax Akwa", page)
        self.assertIn("Available · only 2 left", page)
        self.assertIn("Directions and hours", page)
        self.assertIn(f'href="/ocd/boutique/{self.brenda.id}#magasins"', page)
        self.assertIn("Or have it delivered to you.", page)
        self.assertNotIn("Also in store", page, "The stores show the stock instead")
        self.assertNotIn("Chez moi", page, "A home is not a store")
        # The page changes the stores with the colour and the size: never more than « 4 », the
        # customer never learns the exact count of a store
        stores = {variant["id"]: variant["stores"] for variant in self._data(page)["variants"]}
        self.assertEqual(stores[blue_m.id], [2, 4])
        self.assertEqual(stores[red_m.id], [0, 4], "The pieces of the home are not in a store")
        self.assertEqual(stores[blue_s.id], [0, 0])
        # Sold out everywhere: « Tell me when it is back » says it, the stores are hidden
        self.assertIn("o_ocd_product_store_stock d-none", self._page(blue_s))

    def test_one_store_and_a_home(self):
        akwa = self._place("Brenda Wax Akwa", self.akwa)
        self._place("Chez moi", self.akwa, kind="home")
        self._variant("Bleu", "M")._ocd_change_stock(1, akwa.location_id)
        page = self._page(self._variant("Bleu", "M"))
        self.assertIn("In their store", page)
        self.assertNotIn("In their stores", page)
        self.assertIn("Available · only 1 left", page)

    def test_one_place_the_stores_without_their_stock(self):
        self._place("Brenda Wax Akwa", self.akwa)
        self._variant("Bleu", "M")._ocd_change_stock(2)
        self.company.ocd_hold_enabled = False
        page = self._page(self._variant("Bleu", "M"))
        self.assertIn("Also in store: Akwa", page, "One place: as before (chantier 17)")
        self.assertNotIn("o_ocd_product_store_stock", page)
        self.assertIsNone(self._data(page)["variants"][0]["stores"])
        # A piece can be held there to try (chantier 20): the store shows the stock of the choice
        self.company.ocd_hold_enabled = True
        page = self._page(self._variant("Bleu", "M"))
        self.assertIn("o_ocd_product_store_stock", page)
        self.assertIn("Hold it to try", page)
        self.assertNotIn("Also in store: Akwa", page)

    def test_tell_me_where_it_came_back(self):
        akwa = self._place("Brenda Wax Akwa", self.akwa)
        bonapriso = self._place("Brenda Wax Bonapriso", self.bonapriso)
        home = self._place("Chez moi", self.akwa, kind="home")
        red_m = self._variant("Rouge", "M")
        alert = self.env["ocd.stock.alert"]._ocd_register(red_m, phone="+237 670000009")
        self.assertEqual(alert._ocd_back_in_stores(), "")
        red_m._ocd_change_stock(2, home.location_id)
        self.assertEqual(alert._ocd_back_in_stores(), "", "Back at home only: no store to name")
        red_m._ocd_change_stock(1, bonapriso.location_id)
        red_m._ocd_change_stock(1, akwa.location_id)
        self.assertEqual(alert._ocd_back_in_stores(), "Brenda Wax Akwa, Brenda Wax Bonapriso")
        # A store removed is no longer named (its pieces go to the main place)
        bonapriso.active = False
        self.assertEqual(alert._ocd_back_in_stores(), "Brenda Wax Akwa")
