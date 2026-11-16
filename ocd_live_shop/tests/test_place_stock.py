import importlib.util

from odoo import Command
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

    def _stores_in_two_cities(self):
        bastos = self.env.ref("delivery_cameroon.district_yaounde_bastos")
        douala = self._place(self.brenda, "Brenda Wax Akwa", self.akwa)
        yaounde = self._place(self.brenda, "Brenda Wax Bastos", bastos)
        return douala, yaounde

    def test_the_store_of_the_city_of_the_customer_serves(self):
        douala, yaounde = self._stores_in_two_cities()
        self.brenda.ocd_departure_place_id = yaounde
        self.dress._ocd_change_stock(2, douala.location_id)
        self.dress._ocd_change_stock(2, yaounde.location_id)
        parcel = self._parcel(self._order(self.estelle, [(self.dress, 1)]), self.brenda)
        self.assertEqual(len(parcel), 1)
        self.assertEqual((parcel.location_id, parcel.ocd_pickup_place_id), (douala.location_id, douala),
                         "Estelle lives in Douala: the store of Douala, not the one the parcels leave from")
        self.assertEqual(parcel.state, "assigned")
        self.assertEqual(self._free(douala.location_id), 1)

    def test_another_store_that_has_everything(self):
        douala, yaounde = self._stores_in_two_cities()
        self.dress._ocd_change_stock(3, yaounde.location_id)
        quote = self._order_quote()
        self.assertEqual(quote["origin"].name, "Yaoundé", "The price is counted from the store that has the pieces")
        parcel = self._parcel(self._order(self.estelle, [(self.dress, 2)]), self.brenda)
        self.assertEqual((parcel.ocd_pickup_place_id, parcel.state), (yaounde, "assigned"))
        self.assertEqual(self._free(yaounde.location_id), 1)

    def _order_quote(self):
        order = self.env["sale.order"].create({
            "partner_id": self.estelle.id,
            "order_line": [Command.create({"product_id": self.dress.id, "product_uom_qty": 2})],
        })
        return next(q for q in order._ocd_delivery_quotes() if q["vendor"] == self.brenda)

    def test_a_parcel_per_store(self):
        douala, yaounde = self._stores_in_two_cities()
        bag = self._product("Sac en raphia", 8000, self.brenda)
        bag.is_storable = True
        self.dress._ocd_change_stock(1, douala.location_id)
        bag._ocd_change_stock(1, yaounde.location_id)
        order = self._order(self.estelle, [(self.dress, 1), (bag, 1)])
        parcels = self._parcel(order, self.brenda).sorted("id")
        self.assertEqual(len(parcels), 2, "No store has both: a parcel per store, each with its code")
        self.assertEqual(parcels.mapped("ocd_pickup_place_id"), douala | yaounde)
        self.assertEqual(parcels[0].move_ids.product_id, self.dress)
        self.assertEqual(parcels[1].move_ids.product_id, bag)
        self.assertTrue(all(p.state == "assigned" and p.ocd_is_parcel for p in parcels))
        self.assertEqual(parcels[1].ocd_fee_amount, 0, "One delivery paid: on the first parcel only")
        self.assertEqual(parcels[0].ocd_fee_amount, order._ocd_parcel_delivery(self.brenda)[1] or 0)
