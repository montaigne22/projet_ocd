from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdLowStock(HttpCase, OcdShopCommon):
    """Low stock alert (chantier 21, 3.4 of the plan of « My products », design StockBas): once
    per passage under the threshold, after a sale; « My products » says it, with a filter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_low_stock_threshold": 2, "ocd_vendor_login": "link"})
        cls.dress.product_tmpl_id.write({"is_storable": True, "allow_out_of_stock_order": False,
                                         "is_published": True, "ocd_review_state": "approved"})
        cls.dress._ocd_change_stock(4)

    def setUp(self):
        super().setUp()
        self.told = []
        patcher = patch.object(type(self.env["product.product"]), "_ocd_low_stock_notify",
                               lambda variants, pieces: self.told.append((variants, pieces)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_once_per_passage_under_the_threshold(self):
        self._order(self.estelle, [(self.dress, 1)])
        self.assertEqual(self.told, [], "3 left: above the threshold")
        self._order(self.estelle, [(self.dress, 1)])
        self.assertEqual(self.told, [(self.dress, 2)])
        self._order(self.estelle, [(self.dress, 1)])
        self.assertEqual(len(self.told), 1, "Already under: told once")
        self._order(self.estelle, [(self.dress, 1)])
        self.assertEqual(len(self.told), 1, "None left: the shop says « Sold out »")
        # Back above the threshold, then under again: told again
        self.dress._ocd_change_stock(5)
        self._order(self.estelle, [(self.dress, 3)])
        self.assertEqual(self.told[-1], (self.dress, 2))
        # The threshold of the vendor, then none
        self.dress._ocd_change_stock(5)
        self.brenda.ocd_low_stock_threshold = 5
        self._order(self.estelle, [(self.dress, 3)])
        self.assertEqual(self.told[-1], (self.dress, 4))
        self.brenda.ocd_low_stock_threshold = 0
        self.company.ocd_low_stock_threshold = 0
        self.dress._ocd_change_stock(5)
        count = len(self.told)
        self._order(self.estelle, [(self.dress, 8)])
        self.assertEqual(len(self.told), count, "0: no alert")
        # A product whose stock does not limit the sales: never
        self.company.ocd_low_stock_threshold = 2
        self.butter.product_tmpl_id.write({"is_storable": True, "allow_out_of_stock_order": True})
        self._order(self.estelle, [(self.butter, 1)])
        self.assertEqual(len(self.told), count)

    def test_my_products_says_it_with_a_filter(self):
        for index in range(4):
            product = self._product(f"Pagne {index}", 5000, self.brenda)
            product.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        self._order(self.estelle, [(self.dress, 2)])
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn("Low stock · only 2 left", page)
        self.assertIn('data-state="low"', page)
        self.assertIn('data-low="1"', page)
        page = self.url_open("/ocd/espace/moi/produits?etat=low").text
        self.assertEqual(page.count('data-low="1"'), 1)
