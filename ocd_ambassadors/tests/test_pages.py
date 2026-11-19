from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import OcdAmbassadorCommon

BROWSER = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36"}
PREVIEW = {"User-Agent": "WhatsApp/2.24.1 A"}


@tagged("post_install", "-at_install")
class TestOcdAmbassadorPages(HttpCase, OcdAmbassadorCommon):
    """The pages of the ambassadors (design Ambassadeurs): become one, the personal link, the
    space, the money, the products, « Share », « My links », the product page, « My figures »."""

    def _patch_code(self):
        Partner = type(self.env["res.partner"])
        return patch.object(Partner, "_ocd_send_login_code", lambda partner: True), \
            patch.object(Partner, "_ocd_check_login_code", lambda partner, code: code == "123456")

    def _login(self, phone="691234567"):
        self.authenticate(None, None)
        send, check = self._patch_code()
        with send, check:
            page = self.url_open("/ambassadeur/connexion", data={
                "csrf_token": self.csrf_token(), "phone": phone, "country_id": self.cameroon.id}).text
            self.assertIn('name="code"', page)
            return self.url_open("/ambassadeur/code", data={"csrf_token": self.csrf_token(), "code": "123456"})

    def test_become_an_ambassador(self):
        self.authenticate(None, None)
        page = self.url_open("/ambassadeurs").text
        for text in ("Share, and earn on each parcel delivered", "600", "Become an ambassador", "The charter"):
            self.assertIn(text, page)
        form = {"csrf_token": self.csrf_token(), "name": "Kevin Tossou", "phone": "655001122",
                "country_id": self.cameroon.id, "momo": ""}
        page = self.url_open("/ambassadeurs", data=form).text
        self.assertIn("Tick that you share honestly", page, "The charter first")
        send, check = self._patch_code()
        with send, check:
            page = self.url_open("/ambassadeurs", data={**form, "charter": "1"}).text
            self.assertIn('name="code"', page)
            kevin = self.env["res.partner"].search([("name", "=", "Kevin Tossou")])
            self.assertEqual((kevin.ocd_ambassador_state, kevin.ocd_payout_momo), ("new", kevin.phone))
            response = self.url_open("/ambassadeur/code", data={"csrf_token": self.csrf_token(), "code": "123456"})
        self.assertIn("/ambassadeur", response.url)
        self.assertEqual(kevin.ocd_ambassador_state, "active", "The code proves the number")
        self.assertIn("My ambassador space", response.text)
        self.assertIn(f"/a/{kevin.ocd_ambassador_code}", response.text)

    def test_the_link_counts_for_the_cart(self):
        product = self.dress.product_tmpl_id
        self.authenticate(None, None)
        response = self.url_open(f"/a/GRACE7/{product.id}", headers=PREVIEW, allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("ocd_reco", response.headers.get("Set-Cookie", ""), "A preview of WhatsApp is no visit")
        response = self.url_open(f"/a/grace7/{product.id}", headers=BROWSER, allow_redirects=False)
        self.assertIn(product.website_url, response.headers["Location"])
        self.assertIn("ocd_reco=", response.headers.get("Set-Cookie", ""))
        self.url_open(f"/a/GRACE7/{product.id}", headers=BROWSER, allow_redirects=False)
        visits = self.env["ocd.vendor.count"]._ocd_totals(
            self.grace, "ambassador_visit", self.company._ocd_local_today(), self.company._ocd_local_today())
        self.assertEqual(visits, 1, "One visit per phone and per day")
        self.url_open("/ocd/panier/ajouter", data={
            "csrf_token": self.csrf_token(), "product_template_id": product.id, "quantity": 1}, headers=BROWSER)
        cart = self.env["sale.order"].search([("order_line.product_id", "=", self.dress.id), ("state", "=", "draft")],
                                             order="id desc", limit=1)
        self.assertEqual(cart.ocd_ambassador_id, self.grace)
        page = self.url_open(product.website_url).text
        self.assertIn("o_ocd_amb_reco", page)
        self.assertIn("recommends this product to you", page)
        # Unknown code, page of another site: the shop, never elsewhere
        response = self.url_open("/a/NOBODY?r=//evil.example.com", headers=BROWSER, allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith("/shop"))

    def test_my_space_my_money_my_products(self):
        order = self._amb_order()
        self._deliver(self._parcel(order, self.brenda))
        own = self._amb_order(customer=self.env["res.partner"].create({"name": "G", "phone": "691234567"}))
        response = self._login()
        self.assertIn("/ambassadeur", response.url)
        page = response.text
        for text in ("My sales", "Robe en wax", "Estelle N.", "Delivered", "Your own purchase does not count"[1:]):
            self.assertIn(text, page)
        page = self.url_open("/ambassadeur/argent").text
        for text in ("My payout number", "6 77 •• •• 18", "Since the start"):
            self.assertIn(text, page)
        self.url_open("/ambassadeur/numero", data={"csrf_token": self.csrf_token(), "phone": "655112233",
                                                    "country_id": self.cameroon.id})
        self.assertIn("655112233", self.grace.ocd_payout_momo.replace(" ", ""))
        self.assertTrue(self.grace.ocd_ambassador_momo_since)
        page = self.url_open("/ambassadeur/produits").text
        self.assertIn("Robe en wax", page)
        self.assertIn("You earn", page)
        product = self.dress.product_tmpl_id
        page = self.url_open(f"/ambassadeur/partager/{product.id}").text
        for text in ("Put it in my WhatsApp status", f"/a/GRACE7/{product.id}", "Send to a contact", "Copy the link"):
            self.assertIn(text, page)
        image = self.url_open(f"/a/GRACE7/{product.id}/image.jpg")
        self.assertEqual(image.headers["Content-Type"], "image/jpeg")
        page = self.url_open(f"/ambassadeur/liens?page=/ocd/boutique/{self.brenda.id}").text
        self.assertIn(f"/a/GRACE7?r=/ocd/boutique/{self.brenda.id}", page)
        page = self.url_open("/ambassadeur/liens?page=https://evil.example.com/x").text
        self.assertIn("Paste the address of a page of OCD Live", page)
        # Log out: the space closes
        self.url_open("/ambassadeur/deconnexion", data={"csrf_token": self.csrf_token()})
        self.assertIn("/ambassadeur/connexion", self.url_open("/ambassadeur").url)
        self.assertTrue(own)

    def test_the_own_visits_of_the_ambassador_do_not_count(self):
        self._login()
        product = self.dress.product_tmpl_id
        response = self.url_open(f"/a/GRACE7/{product.id}", headers=BROWSER, allow_redirects=False)
        self.assertNotIn("ocd_reco", response.headers.get("Set-Cookie", ""))
        visits = self.env["ocd.vendor.count"]._ocd_totals(
            self.grace, "ambassador_visit", self.company._ocd_local_today(), self.company._ocd_local_today())
        self.assertEqual(visits, 0)

    def test_the_team_sees_the_space(self):
        self.authenticate("admin", "admin")
        action = self.grace.with_user(self.env.ref("base.user_admin")).action_ocd_ambassador_view_space()
        response = self.url_open(action["url"])
        self.assertIn("My ambassador space", response.text)
        self.assertEqual(self.url_open(f"/ambassadeur/equipe/{self.grace.id}?signature=wrong").status_code, 404)
