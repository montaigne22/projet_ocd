
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from .common import OcdShopCommon
from .test_shop_pages import PNG


@tagged("post_install", "-at_install")
class TestOcdProductReview(HttpCase, OcdShopCommon):
    """A product refused by the team says why to its vendor, who corrects it and sends it again."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        cls.blurry = cls.env.ref("ocd_live_shop.refuse_reason_product_photo")
        cls.skirt = cls.env["product.template"].create({
            "name": "Jupe wax", "list_price": 8000, "ocd_vendor_id": cls.brenda.id,
            "ocd_review_state": "to_check", "is_published": False, "image_1920": BinaryBytes(PNG, filename="jupe.png"),
        })

    def test_a_refusal_always_says_why(self):
        with self.assertRaises(UserError):
            self.skirt.action_ocd_refuse()
        # From the form: the reason chosen on it
        self.skirt.ocd_refuse_reason_id = self.blurry
        self.skirt.action_ocd_refuse()
        self.assertEqual(self.skirt.ocd_review_state, "refused")
        self.assertEqual(self.skirt._ocd_refusal_text(), self.blurry.message)
        self.assertFalse(self.skirt.is_published)

    def test_the_vendor_corrects_and_sends_again(self):
        self.skirt.action_ocd_refuse(self.blurry)
        self.skirt._ocd_vendor_correct({"name": "Jupe wax rouge"})
        self.assertEqual(self.skirt.ocd_review_state, "to_check")
        self.assertFalse(self.skirt.ocd_refuse_reason_id)
        self.assertEqual(self.skirt.ocd_previous_refusal, self.blurry.name)
        item = next(i for i in self.env["ocd.live.verification"]._ocd_product_items() if i["id"] == self.skirt.id)
        self.assertIn(f"Sent again after a refusal: {self.blurry.name}.", item["detail"], "The team sees what to check")
        self.skirt.action_ocd_approve()
        self.assertFalse(self.skirt.ocd_previous_refusal)
        # A product on sale is not corrected this way
        with self.assertRaises(UserError):
            self.skirt._ocd_vendor_correct({"name": "Autre"})

    def test_the_page_to_correct_a_product(self):
        self.skirt.action_ocd_refuse(self.blurry)
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn(self.blurry.message, page)
        self.assertIn(f"/ocd/espace/moi/produits/{self.skirt.id}/modifier", page)
        self.assertIn("Correct and send again", page)
        # The vendor sees the photo the team refused (its public address gives the default
        # image while the product is not online)
        photo = f"/ocd/espace/moi/produits/{self.skirt.id}/photo/image_128"
        self.assertIn(photo, page)
        response = self.url_open(photo)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("image/"))
        self.assertIn("private", response.headers.get("Cache-Control", ""))
        self.assertEqual(self.url_open(f"/ocd/espace/moi/produits/{self.skirt.id}/photo/image_1920").status_code, 404)
        url = f"/ocd/espace/moi/produits/{self.skirt.id}/modifier"
        page = self.url_open(url).text
        self.assertIn("Correct the product", page)
        self.assertIn("Refused by the team:", page)
        self.assertIn('value="Jupe wax"', page)
        self.assertIn('value="8000"', page)
        self.assertIn('data-has-photo="1"', page, "The photo is kept when none is sent")
        self.assertNotIn('name="quantity"', page, "The stock is changed from the list")
        # A wrong price: refused, nothing changed
        page = self.url_open(url, data={"csrf_token": self.csrf_token(), "name": "Jupe", "price": "8000-9000"}).text
        self.assertIn("Write one price, without cents or dash, for example 3000.", page)
        self.assertEqual(self.skirt.name, "Jupe wax")
        # Corrected without a new photo: sent again, the photo kept
        response = self.url_open(url, data={"csrf_token": self.csrf_token(), "name": "Jupe wax rouge", "price": "8 500"},
                                 allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("envoye=1", response.headers["Location"])
        self.assertEqual(self.skirt.ocd_review_state, "to_check")
        self.assertEqual((self.skirt.name, self.skirt.list_price), ("Jupe wax rouge", 8500))
        self.assertTrue(self.skirt.image_128)
        # Another vendor cannot open it; a product on sale is changed while it stays on sale (chantier 19)
        self.url_open(f"/ocd/espace/{self.fatou._ocd_get_space_token()}")
        self.assertEqual(self.url_open(url).status_code, 404)
        self.assertEqual(self.url_open(photo).status_code, 404, "Not the photo of another vendor")
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        self.skirt.action_ocd_approve()
        response = self.url_open(url, allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn("the product stays on sale as it is today", response.text)
