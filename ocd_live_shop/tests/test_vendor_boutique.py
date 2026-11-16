import io
import re

from PIL import Image

from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from .common import OcdShopCommon
from .test_shop_pages import PNG


@tagged("post_install", "-at_install")
class TestOcdVendorBoutique(HttpCase, OcdShopCommon):
    """« My products » helps to sell: what the products brought, the order of the boutique, the
    copies, the filters (chantier 16 of the roadmap)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        Product = cls.env["product.template"]
        cls.products = Product.browse([
            Product.create({
                "name": name, "list_price": 5000, "ocd_vendor_id": cls.brenda.id, "website_sequence": sequence,
                "ocd_review_state": "approved", "is_published": True,
                "image_1920": BinaryBytes(PNG, filename="photo.png"),
            }).id
            for name, sequence in (("Pagne", 10), ("Sac", 20), ("Boubou", 30))
        ])
        cls.pagne, cls.bag, cls.boubou = cls.products
        cls.other = Product.create({"name": "Karite", "ocd_vendor_id": cls.fatou.id, "website_sequence": 15})

    def _order(self, vendor):
        return self.env["product.template"]._ocd_vendor_products(vendor).filtered(lambda p: p in self.products)

    def test_the_order_of_the_boutique(self):
        self.boubou._ocd_move_in_boutique("first")
        self.assertEqual(self._order(self.brenda), self.boubou | self.pagne | self.bag)
        self.assertFalse(self.boubou._ocd_move_in_boutique("up"), "Already first")
        self.bag._ocd_move_in_boutique("up")
        self.assertEqual(self._order(self.brenda), self.boubou | self.bag | self.pagne)
        self.boubou._ocd_move_in_boutique("down")
        self.assertEqual(self._order(self.brenda), self.bag | self.boubou | self.pagne)
        self.assertEqual(self.other.website_sequence, 15, "The products of the other vendors keep their place")
        # The same place number (products made elsewhere): still moved one place
        self.products.website_sequence = 50
        self.pagne._ocd_move_in_boutique("down")
        self.assertEqual(self._order(self.brenda)[1], self.pagne)
        self.assertEqual(len(set(self.products.mapped("website_sequence"))), 3)

    def test_a_copy_is_checked_like_a_new_product(self):
        self.pagne.ocd_wa_clicks = 4
        copy = self.pagne._ocd_vendor_duplicate()
        self.assertEqual(copy.name, "Pagne (copy)")
        self.assertEqual((copy.ocd_review_state, copy.is_published), ("to_check", False))
        self.assertEqual((copy.list_price, copy.ocd_vendor_id), (5000, self.brenda))
        self.assertTrue(copy.image_128, "The photo is copied")
        self.assertEqual(copy.ocd_wa_clicks, 0)
        self.assertEqual(copy._ocd_free_total(), 0, "No stock: the vendor sets it")
        self.assertEqual(self.env["product.template"]._ocd_vendor_products(self.brenda)[0], copy, "First in the boutique")

    def test_my_products_tells_what_the_products_brought(self):
        self.pagne.ocd_wa_clicks = 12
        self.bag.is_storable = True
        for name in ("Estelle", "Herve"):
            customer = self.env["res.partner"].create({"name": name, "phone": "+237 670000111"})
            self.env["ocd.stock.alert"].create({"partner_id": customer.id, "product_id": self.bag.product_variant_id.id})
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn("12 people wrote to you on WhatsApp", page)
        self.assertIn("2 customers wait for it to be back", page)
        self.assertIn(f'href="{self.pagne.website_url}"', page, "See it in my boutique")
        self.assertIn("o_ocd_my_product_share", page)
        self.assertLess(page.index("Pagne"), page.index("Boubou"), "In the order of the boutique")
        self.assertNotIn("o_ocd_my_products_filters", page, "No filter for a short list")

    def test_order_copy_and_filters_from_the_page(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        csrf = self.csrf_token()
        response = self.url_open(f"/ocd/espace/moi/produits/{self.boubou.id}/ordre", data={"csrf_token": csrf, "ou": "first"},
                                 allow_redirects=False)
        self.assertIn(f"ouvert={self.boubou.id}", response.headers["Location"], "Its menu stays open")
        self.assertEqual(self._order(self.brenda)[0], self.boubou)
        response = self.url_open(f"/ocd/espace/moi/produits/{self.pagne.id}/dupliquer", data={"csrf_token": csrf},
                                 allow_redirects=False)
        copy = self.env["product.template"].search([("name", "=", "Pagne (copy)")])
        self.assertTrue(response.headers["Location"].endswith(f"/ocd/espace/moi/produits/{copy.id}/modifier"))
        # 5 products in two states: the filters show
        self.bag.write({"ocd_review_state": "refused", "is_published": False,
                        "ocd_refuse_reason_id": self.env.ref("ocd_live_shop.refuse_reason_product_photo").id})
        self.env["product.template"].create({"name": "Pagne bleu", "ocd_vendor_id": self.brenda.id})
        page = self.url_open("/ocd/espace/moi/produits?etat=refused").text
        self.assertIn("o_ocd_my_products_filters", page)
        self.assertIn('data-state="refused" aria-current="true"', page, "The chosen filter")
        self.assertIn('href="/ocd/espace/moi/produits?etat=refused"', page)
        self.assertRegex(page, rf'id="produit-{self.pagne.id}" data-status="on" hidden="hidden"')
        self.assertRegex(page, rf'id="produit-{self.bag.id}" data-status="refused">')
        # Not the products of another vendor
        response = self.url_open(f"/ocd/espace/moi/produits/{self.other.id}/ordre", data={"csrf_token": csrf, "ou": "first"})
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f"/ocd/espace/moi/produits/{self.other.id}/dupliquer", data={"csrf_token": csrf})
        self.assertEqual(response.status_code, 404)

    def test_the_image_of_a_product_to_share(self):
        stamp = self.pagne._ocd_photo_stamp(self.pagne)
        response = self.url_open(f"/ocd/produit/{self.pagne.id}/partage.jpg?unique={stamp}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/jpeg")
        self.assertIn("immutable", response.headers["Cache-Control"], "Its address changes with the product")
        with Image.open(io.BytesIO(response.content)) as image:
            self.assertEqual(image.size, (1080, 1350), "The size of a WhatsApp status")
        # Drawn once: the second time is kept
        self.assertEqual(self.url_open(f"/ocd/produit/{self.pagne.id}/partage.jpg?unique={stamp}").content, response.content)
        # Only a product on sale
        self.pagne.is_published = False
        self.assertEqual(self.url_open(f"/ocd/produit/{self.pagne.id}/partage.jpg").status_code, 404)
        self.pagne.is_published = True
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn(f'data-image="/ocd/produit/{self.pagne.id}/partage.jpg?unique=', page)

    def test_the_catalogue_for_the_status(self):
        self.company.ocd_vendor_catalogue_items = 2
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        self.assertIn('href="/ocd/espace/moi/catalogue"', self.url_open("/ocd/espace/moi/produits").text)
        page = self.url_open("/ocd/espace/moi/catalogue").text
        images = sorted(set(re.findall(r'src="(/ocd/espace/moi/catalogue/\d+\.jpg\?unique=[^"]+)"', page)))
        self.assertEqual(len(images), 2, "3 products on sale, 2 per image")
        self.assertIn("data-images=", page)
        response = self.url_open(images[1])
        self.assertEqual(response.headers["Content-Type"], "image/jpeg")
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertEqual(self.url_open("/ocd/espace/moi/catalogue/3.jpg").status_code, 404)
        # A product refused or without stock is not in it
        self.bag.write({"is_storable": True, "allow_out_of_stock_order": False})
        page = self.url_open("/ocd/espace/moi/catalogue").text
        self.assertEqual(len(re.findall(r'src="/ocd/espace/moi/catalogue/', page)), 1)
        # Another vendor sees their own (none on sale)
        self.url_open(f"/ocd/espace/{self.fatou._ocd_get_space_token()}")
        self.assertIn("No product on sale yet", self.url_open("/ocd/espace/moi/catalogue").text)
        self.assertEqual(self.url_open(images[0].split("?")[0]).status_code, 404)
