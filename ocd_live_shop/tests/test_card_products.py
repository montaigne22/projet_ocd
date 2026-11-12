import base64

from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import BinaryBytes

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestOcdCardProducts(TransactionCase):
    """The card of a vendor in the feed: the carousel of its products, a tap opens one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({
            "name": "Ama Pagnes", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id,
        })

        def product(name, **vals):
            return cls.env["product.template"].create({
                "name": name, "list_price": 5000, "type": "consu", "ocd_vendor_id": cls.vendor.id,
                "is_published": True, "ocd_review_state": "approved", "image_1920": BinaryBytes(PNG),
                "taxes_id": [Command.clear()], **vals,
            })

        cls.sold_out = product("Pagne hollandais", is_storable=True, allow_out_of_stock_order=False)
        cls.dress = product("Robe wax")
        product("Brouillon", is_published=False)
        product("A verifier", ocd_review_state="to_check", is_published=False)
        product("Sans photo", image_1920=False)

    def test_carousel_of_the_products(self):
        vendor = self.vendor
        media = vendor._ocd_card_media()
        self.assertEqual(media["kind"], "products", "Automatic: its products when it has no video")
        self.assertEqual(
            [slide["name"] for slide in media["slides"]], ["Robe wax", "Pagne hollandais"],
            "Published, checked, with a photo; the sold out ones last",
        )
        dress, pagne = media["slides"]
        self.assertTrue(pagne["out"])
        self.assertFalse(dress["out"])
        self.assertEqual(dress["url"], self.dress.website_url, "A tap opens the product")
        self.assertEqual(dress["image"], f"/web/image/product.template/{self.dress.id}/image_512")
        self.assertIn("5", dress["price"])
        choices = vendor._ocd_card_choices()
        self.assertEqual([row["value"] for row in choices], ["auto", "video", "products", "image"])
        self.assertTrue(next(row for row in choices if row["value"] == "products")["ready"])
        vendor.ocd_card_media = "image"
        image = vendor._ocd_card_media()
        self.assertEqual(image["kind"], "image", "No image of its own: the photo of a product")
        self.assertTrue(image["image"].startswith("/web/image/product.template/"))
