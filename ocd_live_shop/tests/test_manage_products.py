from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from .common import OcdShopCommon
from .test_shop_pages import PNG


@tagged("post_install", "-at_install")
class TestOcdManageProducts(HttpCase, OcdShopCommon):
    """Manage the products on sale (chantier 19, step 2 of the plan of « My products », design
    GererProduits): take a product off sale and put it back, change it while the version of today
    stays on sale, several photos, a draft kept in the phone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        Product = cls.env["product.template"]
        cls.dress_tmpl = cls.dress.product_tmpl_id
        cls.dress_tmpl.write({
            "ocd_review_state": "approved", "is_published": True, "list_price": 15000, "is_storable": True,
            "image_1920": BinaryBytes(PNG, filename="robe.png"),
        })
        cls.other = Product.create({
            "name": "Karite", "ocd_vendor_id": cls.fatou.id, "ocd_review_state": "approved", "is_published": True,
        })

    def _login(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        return self.csrf_token()

    def _post(self, path, **data):
        return self.url_open(path, data={"csrf_token": self.csrf_token(), **data}, allow_redirects=False)

    def test_take_off_sale_and_put_back(self):
        self._login()
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn(f'action="/ocd/espace/moi/produits/{self.dress_tmpl.id}/retirer"', page)
        alert = self.env["ocd.stock.alert"]._ocd_register(self.dress, phone="+237 670000009")
        response = self._post(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/retirer")
        self.assertIn("retire=1", response.headers["Location"])
        self.assertFalse(self.dress_tmpl.is_published)
        self.assertTrue(self.dress_tmpl.ocd_vendor_retired)
        self.assertTrue(self.dress_tmpl.active, "Never deleted: the past orders keep it")
        page = self.url_open("/ocd/espace/moi/produits?retire=1").text
        self.assertIn("Taken off sale: it no longer shows in your boutique.", page)
        self.assertRegex(page, rf'id="produit-{self.dress_tmpl.id}" data-status="retired"')
        self.assertIn(f'action="/ocd/espace/moi/produits/{self.dress_tmpl.id}/remettre"', page)
        self.assertNotIn("Robe en wax", self.url_open(f"/ocd/boutique/{self.brenda.id}").text)
        # The customer waiting for it is not told while it is off sale
        self.dress._ocd_change_stock(2)
        self.env["ocd.stock.alert"]._ocd_send_back()
        self.assertEqual(alert.state, "waiting")
        # Back on sale with one tap
        response = self._post(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/remettre")
        self.assertIn("remis=1", response.headers["Location"])
        self.assertTrue(self.dress_tmpl.is_published)
        self.assertFalse(self.dress_tmpl.ocd_vendor_retired)
        self.assertIn("Back on sale: it shows again in your boutique.", self.url_open("/ocd/espace/moi/produits?remis=1").text)

    def test_only_what_the_vendor_took_off(self):
        self._login()
        # Hidden by the team: the vendor cannot put it back
        self.dress_tmpl.is_published = False
        self.assertFalse(self.dress_tmpl._ocd_vendor_can_retire())
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertRegex(page, rf'id="produit-{self.dress_tmpl.id}" data-status="hidden"')
        self._post(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/remettre")
        self.assertFalse(self.dress_tmpl.is_published)
        # Not the products of another vendor
        self.assertEqual(self._post(f"/ocd/espace/moi/produits/{self.other.id}/retirer").status_code, 404)
        self.assertTrue(self.other.is_published)
