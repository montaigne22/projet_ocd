import importlib.util

from odoo.modules.module import get_module_path
from odoo.tests import tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdPlaceStock(OcdShopCommon):
    """The stock of the places of a vendor (chantier 18): a location per place inside the stock of
    the shop, the pieces of the vendor in their first place, a place removed gives its pieces
    back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False})
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        cls.bonapriso = cls.env.ref("delivery_cameroon.district_douala_bonapriso")
        cls.dress.is_storable = True
        cls.root = cls.env["product.product"]._ocd_stock_root()
        cls.Place = cls.env["ocd.vendor.place"]

    def _place(self, vendor, name, district):
        return self.Place._ocd_vendor_create(vendor, {
            "name": name, "kind": "store", "district_id": district.id, "city_id": district.city_id.id,
        })

    def _free(self, location, exact=True):
        return self.brenda._ocd_free_pieces(location, exact=exact).get(self.dress, 0)

    def test_the_first_place_receives_the_pieces(self):
        self.dress._ocd_set_free_stock(5)
        self.assertEqual(self._free(self.root), 5, "No place yet: in the stock of the shop")
        akwa = self._place(self.brenda, "Brenda Wax Akwa", self.akwa)
        self.assertTrue(akwa.location_id)
        self.assertEqual(akwa.location_id.location_id, self.root, "Inside the stock of the shop")
        self.assertEqual((self._free(akwa.location_id), self._free(self.root)), (5, 0))
        self.assertEqual(self.dress._ocd_free_qty(), 5, "The total and the website count every place")
        transfer = self.env["stock.picking"].search([("location_dest_id", "=", akwa.location_id.id)])
        self.assertEqual((transfer.state, transfer.picking_type_code), ("done", "internal"), "Traced as a transfer")
        self.assertEqual(akwa.ocd_stock_count, 5)
        # One place: the stock of the vendor shows as before
        self.assertFalse(self.brenda._ocd_stock_per_place())
        self.assertFalse(self.dress.product_tmpl_id.ocd_stock_by_place)

    def test_two_places_and_the_place_without_name(self):
        self.dress._ocd_set_free_stock(5)
        akwa = self._place(self.brenda, "Brenda Wax Akwa", self.akwa)
        bonapriso = self._place(self.brenda, "Brenda Wax Bonapriso", self.bonapriso)
        self.assertTrue(self.brenda._ocd_stock_per_place())
        self.assertEqual(self._free(bonapriso.location_id), 0, "The second place starts empty")
        self.assertEqual(self.dress.product_tmpl_id.ocd_stock_by_place, "Brenda Wax Akwa: 5 · Brenda Wax Bonapriso: 0")
        # A piece added without a place goes to the place the parcels leave from
        self.brenda.ocd_departure_place_id = bonapriso
        self.dress._ocd_change_stock(2)
        self.assertEqual((self._free(akwa.location_id), self._free(bonapriso.location_id)), (5, 2))
        self.assertEqual(self.dress._ocd_free_qty(), 7)
        # The name of the place follows on its location
        bonapriso.name = "Brenda Wax Bonapriso 2"
        self.assertEqual(bonapriso.location_id.name, "Brenda Wax · Brenda Wax Bonapriso 2")

    def test_a_place_removed_gives_its_pieces_back(self):
        self.brenda.ocd_delivery_mode = "pickup"
        self.dress._ocd_set_free_stock(5)
        akwa = self._place(self.brenda, "Brenda Wax Akwa", self.akwa)
        bonapriso = self._place(self.brenda, "Brenda Wax Bonapriso", self.bonapriso)
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = self._parcel(order, self.brenda)
        self.assertEqual(parcel.state, "assigned", "The piece of the order is kept")
        akwa.active = False
        self.assertEqual(self._free(bonapriso.location_id), 4, "The free pieces go to the other place")
        self.assertEqual(parcel.state, "assigned", "The piece of the order stays kept")
        self.assertEqual(self.dress._ocd_free_qty(), 4)
        # The last place removed: the pieces go back to the stock of the shop
        bonapriso.active = False
        self.assertEqual(self._free(self.root), 4)

    def test_the_products_in_the_ocd_stock_stay_there(self):
        self.brenda.ocd_delivery_mode = "stock"
        self.dress._ocd_set_free_stock(3)
        akwa = self._place(self.brenda, "Brenda Wax Akwa", self.akwa)
        self.assertFalse(akwa.location_id)
        self.assertEqual(self._free(self.root), 3)
        self.assertEqual(self.dress._ocd_stock_location(), self.root)

    def test_the_places_added_before_the_stock_per_place(self):
        """The update to the stock per place: the main place of each vendor receives the pieces
        they had, the other places get their location."""
        self.brenda.ocd_delivery_mode = "stock"
        self.dress._ocd_set_free_stock(4)
        akwa = self._place(self.brenda, "Brenda Wax Akwa", self.akwa)
        bonapriso = self._place(self.brenda, "Brenda Wax Bonapriso", self.bonapriso)
        self.brenda.write({"ocd_delivery_mode": "pickup", "ocd_departure_place_id": bonapriso.id})
        path = f"{get_module_path('ocd_live_shop')}/migrations/20.0.1.13.0/post-migration.py"
        spec = importlib.util.spec_from_file_location("ocd_stock_per_place", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, "20.0.1.12.0")
        self.assertTrue(akwa.location_id and bonapriso.location_id)
        self.assertEqual((self._free(bonapriso.location_id), self._free(akwa.location_id), self._free(self.root)), (4, 0, 0),
                         "The place the parcels leave from receives the pieces")
