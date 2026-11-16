from odoo import Command
from odoo.tests import tagged

from ..models.product_product import MAX_STOCK
from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorStock(OcdShopCommon):
    """The stock a vendor changes from « My products »: the pieces free to sell, the ones
    reserved for the orders kept, each tap added to the stock of the moment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.skirt = cls.env["product.product"].create({
            "name": "Jupe en wax",
            "is_storable": True,
            "list_price": 8000,
            "taxes_id": [Command.clear()],
            "ocd_vendor_id": cls.brenda.id,
        })
        cls.skirt.product_tmpl_id._ocd_set_stock(5)

    def _on_hand(self):
        self.skirt.invalidate_recordset(["qty_available"])
        return self.skirt.qty_available

    def test_the_pieces_of_an_order_are_never_taken_away(self):
        order = self._order(self.estelle, [(self.skirt, 2)])
        moves = order.picking_ids.move_ids.filtered(lambda m: m.product_id == self.skirt)
        self.assertEqual(sum(moves.mapped("quantity")), 2, "The order reserved its 2 pieces")
        self.assertEqual(self.skirt._ocd_free_qty(), 3, "The vendor sees the pieces still free")
        # + adds one piece to the free ones: the 2 of the order stay reserved
        self.assertEqual(self.skirt._ocd_change_stock(1), 4)
        self.assertEqual(self._on_hand(), 6)
        # − past 0 stops at 0: the stock never goes under what the orders hold
        self.assertEqual(self.skirt._ocd_change_stock(-10), 0)
        self.assertEqual(self._on_hand(), 2)
        self.assertEqual(sum(moves.mapped("quantity")), 2, "The order keeps its pieces")
        # Setting the stock sets the free pieces
        self.skirt.product_tmpl_id._ocd_set_stock(7)
        self.assertEqual(self.skirt._ocd_free_qty(), 7)
        self.assertEqual(self._on_hand(), 9)

    def test_a_sale_made_since_the_page_was_shown_is_kept(self):
        # The page showed 5; meanwhile a customer buys 2; then the vendor taps +
        self._order(self.estelle, [(self.skirt, 2)])
        self.skirt.product_tmpl_id._ocd_change_stock(1)
        self.assertEqual(self.skirt._ocd_free_qty(), 4, "5 - 2 sold + 1, not the 6 of the old page")

    def test_the_stock_has_bounds_and_each_change_is_traced(self):
        self.assertEqual(self.skirt._ocd_change_stock(MAX_STOCK * 2), MAX_STOCK)
        self.assertEqual(self.skirt._ocd_change_stock(0), MAX_STOCK, "Nothing to change")
        self.skirt._ocd_change_stock(-MAX_STOCK)
        moves = self.env["stock.move"].search([("product_id", "=", self.skirt.id), ("is_inventory", "=", True)])
        self.assertEqual(len(moves), 3, "The first stock, then the two changes: each one traced")

    def test_the_free_stock_of_all_the_products_in_one_query(self):
        bag = self.env["product.product"].create({
            "name": "Sac en raphia", "is_storable": True, "ocd_vendor_id": self.brenda.id,
        })
        bag._ocd_set_free_stock(3)
        variants = self.skirt | bag | self.dress
        # As many queries for one product as for three: never one per product
        self.env.invalidate_all()
        with self.assertQueryCount(__system__=6):
            self.skirt._ocd_free_qties()
        self.env.invalidate_all()
        with self.assertQueryCount(__system__=6):
            free = variants._ocd_free_qties()
        self.assertEqual(free, {self.skirt.id: 5, bag.id: 3, self.dress.id: 0})
