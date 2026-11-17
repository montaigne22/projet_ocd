from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from .common import OcdShopCommon
from .test_product_media import other_png
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

    # === CHANGE A PRODUCT ON SALE (2.1) === #

    def _change(self, **values):
        data = {"name": self.dress_tmpl.name, "price": "15000", **values}
        return self._post(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier", **data)

    def test_the_new_name_is_checked_while_the_product_stays_on_sale(self):
        self._login()
        page = self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text
        self.assertIn("the product stays on sale as it is today", page)
        self.assertNotIn('id="mp-photo"', page, "The photos of a product on sale are changed apart")
        response = self._change(name="Robe en wax, col rond")
        self.assertIn("modifie=verification", response.headers["Location"])
        self.assertEqual(self.dress_tmpl.name, "Robe en wax", "The version of today stays on sale")
        self.assertEqual((self.dress_tmpl.ocd_change_state, self.dress_tmpl.ocd_change_name), ("to_check", "Robe en wax, col rond"))
        self.assertTrue(self.dress_tmpl.is_published)
        page = self.url_open("/ocd/espace/moi/produits?modifie=verification").text
        self.assertIn("Noted: the team checks your change.", page)
        self.assertIn("Change being checked: new name. The version of today stays on sale.", page)
        # The edit page shows the name waiting
        self.assertIn('value="Robe en wax, col rond"', self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text)
        # The team sees before and now, and accepts
        Verification = self.env["ocd.live.verification"]
        item = next(i for i in Verification._ocd_change_items() if i["id"] == self.dress_tmpl.id)
        self.assertEqual(item["changes"], [{"label": "Name", "before": "Robe en wax", "now": "Robe en wax, col rond"}])
        Verification.ocd_approve("product_change", self.dress_tmpl.id)
        self.assertEqual(self.dress_tmpl.name, "Robe en wax, col rond")
        self.assertEqual(self.dress_tmpl.ocd_change_state, "approved")
        self.assertFalse(self.dress_tmpl.ocd_change_name)
        self.assertFalse(any(i["id"] == self.dress_tmpl.id for i in Verification._ocd_change_items()))

    def test_a_change_refused_is_corrected(self):
        self._login()
        self._change(name="Robe")
        reason = self.env.ref("ocd_live_shop.refuse_reason_product_photo")
        self.env["ocd.live.verification"].ocd_refuse("product_change", self.dress_tmpl.id, reason.id)
        self.assertEqual((self.dress_tmpl.ocd_change_state, self.dress_tmpl.name), ("refused", "Robe en wax"))
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn("Change refused: «", page)
        self.assertIn("The version before stays on sale.", page)
        self.assertIn("Correct and send again", page)
        self.assertIn("Change refused by the team:", self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text)
        # Sent again: checked again
        self._change(name="Robe longue")
        self.assertEqual((self.dress_tmpl.ocd_change_state, self.dress_tmpl.ocd_change_name), ("to_check", "Robe longue"))
        self.assertFalse(self.dress_tmpl.ocd_change_reason_id)
        # Back to the name on sale: nothing left to check
        self._change(name="Robe en wax")
        self.assertFalse(self.dress_tmpl.ocd_change_state)
        self.assertFalse(self.dress_tmpl.ocd_change_name)

    def test_the_price_at_once_a_big_change_confirmed(self):
        self._login()
        lines = self.dress_tmpl.ocd_price_ids
        # A small change: at once, no question, nothing to check
        response = self._change(price="14000")
        self.assertIn("modifie=1&prix=1", response.headers["Location"])
        self.assertEqual(self.dress_tmpl.list_price, 14000)
        self.assertFalse(self.dress_tmpl.ocd_change_state)
        line = self.dress_tmpl.ocd_price_ids - lines
        self.assertEqual((line.previous_price, line.price, line.gap, line.source, line.confirmed), (15000, 14000, -7, "vendor", False))
        # A big change: the vendor confirms it first
        response = self._change(price="1400")
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.text, r"You go from .+ to .+, is that right\?")
        self.assertRegex(response.text, r'name="prix_confirme"[^>]*value="1400"')
        self.assertEqual(self.dress_tmpl.list_price, 14000, "Not changed before the answer")
        self._change(price="1400", prix_confirme="1400")
        self.assertEqual(self.dress_tmpl.list_price, 1400)
        line = self.dress_tmpl.ocd_price_ids[:1]
        self.assertEqual((line.gap, line.confirmed, line.big_gap), (-90, True, True))
        # A confirmation of another price asks again
        response = self._change(price="140", prix_confirme="1400")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.dress_tmpl.list_price, 1400)
        # The team sees the price with the change of the name
        self._change(name="Robe en wax bleue", price="1500")
        rows = next(i for i in self.env["ocd.live.verification"]._ocd_change_items() if i["id"] == self.dress_tmpl.id)["changes"]
        self.assertEqual([row["label"] for row in rows], ["Name", "Price"])
        self.assertIn("already on sale", rows[1]["now"])
        # Changed by the team in the back office: in the history too
        self.dress_tmpl.list_price = 1600
        self.dress_tmpl.invalidate_recordset(["ocd_price_ids"])
        self.assertEqual(self.dress_tmpl.ocd_price_ids.filtered(lambda line: line.price == 1600).source, "team")

    def test_the_setting_of_the_price_to_confirm(self):
        self._login()
        self.company.ocd_price_gap_confirm = 0
        self._change(price="100")
        self.assertEqual(self.dress_tmpl.list_price, 100, "0: never asked")

    # === SEVERAL PHOTOS (2.6) === #

    def _add_photo(self, colour="red"):
        return self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/photos", data={"csrf_token": self.csrf_token()},
                             files={"photo": ("photo.png", other_png(colour), "image/png")}, allow_redirects=False)

    def _photo_action(self, key, what):
        return self._post(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/photos/{key}/{what}")

    def test_a_new_photo_is_checked_while_the_product_stays_on_sale(self):
        self._login()
        page = self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text
        self.assertIn(f'action="/ocd/espace/moi/produits/{self.dress_tmpl.id}/photos"', page)
        self.assertIn("· 1 of 8 ·", page)
        response = self._add_photo()
        self.assertTrue(response.headers["Location"].endswith("/modifier#photos"))
        image = self.dress_tmpl.product_template_image_ids.filtered(lambda i: i.ocd_review_state == "to_check")
        self.assertEqual(len(image), 1)
        self.assertEqual(self.dress_tmpl._ocd_vendor_images()[-1], image, "After the photos already there")
        self.assertEqual(self.dress_tmpl.ocd_change_state, "to_check")
        self.assertEqual(self.dress_tmpl._ocd_page_photos()[1], [], "Not shown before the check")
        page = self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text
        self.assertIn("New · being checked", page)
        self.assertEqual(self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/photos/{image.id}").status_code, 200)
        self.assertIn("Change being checked: new photos.", self.url_open("/ocd/espace/moi/produits").text)
        rows = next(i for i in self.env["ocd.live.verification"]._ocd_change_items() if i["id"] == self.dress_tmpl.id)["changes"]
        self.assertEqual(rows[0]["label"], "Photos")
        self.assertEqual([photo["new"] for photo in rows[0]["now_photos"]], [False, True])
        self.env["ocd.live.verification"].ocd_approve("product_change", self.dress_tmpl.id)
        self.assertEqual(image.ocd_review_state, "approved")
        self.assertEqual(len(self.dress_tmpl._ocd_page_photos()[1]), 1, "Shown once checked")
        # Moved before the main one: it becomes the photo of the cards
        main = self.dress_tmpl.image_1920.content
        self._photo_action(image.id, "avant")
        self.assertEqual(self.dress_tmpl._ocd_vendor_images()[0], image)
        self.assertEqual(self.dress_tmpl.image_1920.content, image.image_1920.content)
        self.assertNotEqual(self.dress_tmpl.image_1920.content, main)
        # The main one removed: the next checked photo takes its place; the last one stays
        self._photo_action("principale", "retirer")
        self.assertFalse(image.exists())
        self.assertEqual(self.dress_tmpl.image_1920.content, main)
        response = self._photo_action("principale", "retirer")
        self.assertIn("photo_erreur=garder", response.headers["Location"])
        self.assertTrue(self.dress_tmpl.image_1920)
        # At most the photos of the setting
        self.company.ocd_product_photos_max = 1
        self.assertIn("photo_erreur=nombre", self._add_photo().headers["Location"])
        # Not the photos of another vendor
        self.assertEqual(self._post(f"/ocd/espace/moi/produits/{self.other.id}/photos/principale/retirer").status_code, 404)

    def test_a_refused_photo_is_removed_or_sent_again(self):
        self._login()
        self._add_photo()
        image = self.dress_tmpl.product_template_image_ids.filtered(lambda i: i.ocd_review_state == "to_check")
        reason = self.env.ref("ocd_live_shop.refuse_reason_product_photo")
        self.env["ocd.live.verification"].ocd_refuse("product_change", self.dress_tmpl.id, reason.id)
        self.assertEqual((image.ocd_review_state, self.dress_tmpl.ocd_change_state), ("refused", "refused"))
        self.assertIn("Refused", self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text)
        # Saved again: back to the check
        self._change()
        self.assertEqual((image.ocd_review_state, self.dress_tmpl.ocd_change_state), ("to_check", "to_check"))
        # Removed: nothing left to check
        self._photo_action(image.id, "retirer")
        self.assertFalse(image.exists())
        self.assertFalse(self.dress_tmpl.ocd_change_state)

    def test_the_new_photo_of_a_colour_is_checked(self):
        colour = self.env["product.attribute"].create({"name": "Couleur", "display_type": "color", "value_ids": [
            Command.create({"name": "Bleu", "html_color": "#2F6FB8"}),
        ]})
        self.dress_tmpl.attribute_line_ids = [
            Command.create({"attribute_id": colour.id, "value_ids": [Command.set(colour.value_ids.ids)]}),
        ]
        value = self.dress_tmpl.attribute_line_ids.product_template_value_ids
        self._login()
        self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/couleur/{value.id}", data={"csrf_token": self.csrf_token()},
                      files={"photo": ("bleu.png", PNG, "image/png")})
        self.assertFalse(value.ocd_image, "The page keeps the main photo meanwhile")
        self.assertTrue(value.ocd_image_pending)
        self.assertEqual((value.ocd_image_state, self.dress_tmpl.ocd_change_state), ("to_check", "to_check"))
        self.assertIn("Being checked", self.url_open("/ocd/espace/moi/produits").text)
        rows = next(i for i in self.env["ocd.live.verification"]._ocd_change_items() if i["id"] == self.dress_tmpl.id)["changes"]
        self.assertEqual(rows[0]["label"], "Colour Bleu")
        self.env["ocd.live.verification"].ocd_approve("product_change", self.dress_tmpl.id)
        self.assertTrue(value.ocd_image)
        self.assertFalse(value.ocd_image_pending)

    # === A DRAFT KEPT WITHOUT NETWORK (2.7) === #

    def test_a_product_added_without_network_is_kept_in_the_phone(self):
        """The page has what the phone needs (OcdProductDrafts): the form of a new product says
        it can be kept, the list has the place of the products kept. The same form sent again
        when the network is back adds one product only."""
        self._login()
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertRegex(page, r'<form[^>]*action="/ocd/espace/moi/produits"[^>]*data-draft="1"')
        self.assertIn('class="o_ocd_my_drafts"', page)
        self.assertIn("No network.", page)
        self.assertNotIn('data-draft="1"', self.url_open(f"/ocd/espace/moi/produits/{self.dress_tmpl.id}/modifier").text)
        data = {"csrf_token": self.csrf_token(), "form_token": "a" * 32, "name": "Pagne", "price": "6000", "quantity": "2"}
        files = {"photo": ("pagne.png", PNG, "image/png")}
        for _sending in range(2):
            response = self.url_open("/ocd/espace/moi/produits", data=data, files=files)
            self.assertTrue(response.url.endswith("/ocd/espace/moi/produits?envoye=1"))
        self.assertEqual(self.env["product.template"].search_count([("ocd_vendor_id", "=", self.brenda.id), ("name", "=", "Pagne")]), 1)
