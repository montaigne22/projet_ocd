from urllib.parse import urlencode

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdTrust(HttpCase, OcdShopCommon):
    """The trust of the customers (chantier 2, design GarantieAvis): the reviews of the buyers
    (one per parcel delivered), the verified vendor, the guarantee of OCD Live, report a product
    or a vendor to the team."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_vendor_login": "link", "ocd_return_days": 30})
        for product in (cls.dress, cls.butter):
            product.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        cls.Review = cls.env["ocd.vendor.review"]
        cls.Verification = cls.env["ocd.live.verification"]

    def _delivered(self, customer, lines, vendor):
        order = self._order(customer, lines)
        parcel = self._parcel(order, vendor)
        parcel.write({"ocd_stage": "delivered", "ocd_delivered_at": fields.Datetime.now()})
        return order, parcel

    def _post(self, url, **data):
        return self.url_open(url, data={"csrf_token": self.csrf_token(), **data})

    # === THE REVIEWS === #

    def test_a_review_per_parcel_once_delivered(self):
        order = self._order(self.estelle, [(self.dress, 1), (self.butter, 1)])
        parcel = self._parcel(order, self.brenda)
        with self.assertRaisesRegex(UserError, "once the parcel is delivered"):
            self.Review._ocd_give(parcel, 5)
        parcel.write({"ocd_stage": "delivered", "ocd_delivered_at": fields.Datetime.now()})
        review = self.Review._ocd_give(parcel, 4, "  Très belle   qualité  ")
        self.assertEqual((review.vendor_id, review.partner_id, review.stars, review.comment),
                         (self.brenda, self.estelle, 4, "Très belle qualité"))
        self.assertEqual(review.author_name, "Estelle N.")
        self.assertEqual(review.product_ids, self.dress.product_tmpl_id)
        # Changed: still one review for the parcel; WhatsApp keeps the word
        self.assertEqual(self.Review._ocd_give(parcel, 5, "Parfait"), review)
        order._ocd_review_parcels(3, "whatsapp")
        self.assertEqual((review.stars, review.comment, review.source), (3, "Parfait", "whatsapp"))
        with self.assertRaisesRegex(UserError, "1 to 5"):
            self.Review._ocd_give(parcel, 6)
        # The note shows from 3 reviews
        self.assertEqual(self.Review._ocd_summary(self.brenda)["line"], "New vendor")
        self.assertEqual(self.Review._ocd_card_line(self.brenda.id), "")
        for stars in (5, 5):
            self.Review._ocd_give(self._delivered(self.herve, [(self.dress, 1)], self.brenda)[1], stars)
        summary = self.Review._ocd_summary(self.brenda)
        self.assertEqual((summary["note"], summary["count"]), ("4.3", 3))
        self.assertEqual(self.Review._ocd_card_line(self.brenda.id), "4.3 (3)")
        self.assertEqual(self.Review._ocd_author("+237 670000000"), "A buyer")

    def test_the_buyer_gives_it_on_the_page_of_the_order(self):
        order, parcel = self._delivered(self.estelle, [(self.dress, 1)], self.brenda)
        self.authenticate(None, None)
        base = f"/ocd/suivi/{order.id}"
        token = urlencode({"access_token": order._portal_ensure_token()})
        page = self.url_open(f"{base}?{token}").text
        self.assertIn("Your review of Brenda Wax", page)
        self.assertIn("never your number", page)
        response = self._post(f"{base}/avis/{parcel.id}?{token}", stars="5", comment="Livrée le lendemain")
        self.assertIn(f"avis={parcel.id}", response.url)
        self.assertIn("Thank you: ★★★★★ sent.", response.text)
        self.assertIn("Change my review", response.text)
        review = self.Review.search([("picking_id", "=", parcel.id)])
        self.assertEqual((review.stars, review.comment), (5, "Livrée le lendemain"))
        # A parcel of another order: not found
        other_order, other = self._delivered(self.herve, [(self.dress, 1)], self.brenda)
        self.assertEqual(self._post(f"{base}/avis/{other.id}?{token}", stars="1").status_code, 404)
        # The boutique shows the review, its page lists them all
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn("Reviews of the buyers", page)
        self.assertIn("Livrée le lendemain", page)
        self.assertIn("Verified purchase", page)
        self.assertIn("New vendor", page, "The note waits for 3 reviews")
        self.assertIn("Estelle N.", self.url_open(f"/ocd/boutique/{self.brenda.id}/avis").text)

    def test_the_vendor_reports_a_review_the_team_decides(self):
        review = self.Review._ocd_give(self._delivered(self.estelle, [(self.dress, 1)], self.brenda)[1], 1, "Arnaque")
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn("My reviews", page)
        page = self.url_open("/ocd/espace/moi/avis").text
        self.assertIn("Arnaque", page)
        self.assertIn("Report this review", page)
        response = self._post(f"/ocd/espace/moi/avis/{review.id}/signaler", note="Cette personne n'a jamais commandé")
        self.assertIn("Reported: the team looks at it.", response.text)
        self.assertEqual(review.state, "reported")
        items = {item["key"]: item for column in self.Verification._ocd_columns() for item in column["items"]}
        self.assertIn(f"review_{review.id}", items)
        self.Verification.ocd_approve("review", review.id, {"state": "hidden"})
        self.assertEqual(review.state, "hidden")
        self.assertEqual(self.Review._ocd_stats([self.brenda.id]), {}, "A hidden review counts no more")
        # Another vendor's review: not found
        other = self.Review._ocd_give(self._delivered(self.herve, [(self.butter, 1)], self.fatou)[1], 2)
        self.assertEqual(self._post(f"/ocd/espace/moi/avis/{other.id}/signaler", note="x").status_code, 404)

    def test_my_products_show_the_note_of_each_product(self):
        self.Review._ocd_give(self._delivered(self.estelle, [(self.dress, 1)], self.brenda)[1], 4)
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        self.assertIn("★ 4.0 · 1 review", self.url_open("/ocd/espace/moi/produits").text)

    # === VERIFIED VENDOR, GUARANTEE === #

    def test_verified_vendor(self):
        self.brenda.ocd_verified = True
        self.assertTrue(self.brenda.ocd_verified_at)
        self.assertEqual(self.brenda.ocd_verified_by_id, self.env.user)
        self.authenticate(None, None)
        self.assertIn("Verified vendor", self.url_open(f"/ocd/boutique/{self.brenda.id}").text)
        self.assertIn("Verified vendor", self.url_open(self.dress.product_tmpl_id.website_url).text)
        self.brenda.ocd_verified = False
        self.assertFalse(self.brenda.ocd_verified_at)
        # Checked when the team validates a new vendor
        newcomer = self.env["res.partner"].create({"name": "Nadia Sow", "ocd_is_vendor": True})
        choices = {choice["name"]: choice for choice in self.Verification._ocd_vendor_choices(newcomer)}
        self.assertEqual(choices["ocd_verified"]["value"], "")
        self.Verification.ocd_approve("vendor", newcomer.id, {"ocd_verified": "1", "ocd_sale_mode": "ocd"})
        self.assertTrue(newcomer.ocd_verified)
        self.assertEqual(newcomer.ocd_vendor_state, "approved")

    def test_the_guarantee_of_ocd_live(self):
        self.authenticate(None, None)
        page = self.url_open(self.dress.product_tmpl_id.website_url).text
        self.assertIn("OCD Live guarantee", page)
        self.assertIn("Return possible for 30 days.", page)
        self.assertIn('href="/ocd/garantie"', page)
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn("is paid after the delivery, when you give your code", page)
        self.fatou.ocd_sale_mode = "direct"
        self.assertIn("outside the OCD Live guarantee", self.url_open(f"/ocd/boutique/{self.fatou.id}").text)
        page = self.url_open("/ocd/garantie").text
        self.assertIn("The vendor is paid after", page)
        self.assertIn("For 30 days after the delivery", page)

    # === REPORT === #

    def test_report_a_product_then_the_team_removes_it(self):
        product = self.dress.product_tmpl_id
        self.authenticate(None, None)
        self.assertIn(f"/ocd/signaler?produit={product.id}", self.url_open(product.website_url).text)
        page = self.url_open(f"/ocd/signaler?produit={product.id}").text
        self.assertIn("Report Robe en wax", page)
        self.assertIn("Fake, or copy of a brand", page)
        response = self._post("/ocd/signaler", produit=product.id, reason="other")
        self.assertIn("Tell us what is wrong.", response.text)
        response = self._post("/ocd/signaler", produit=product.id, reason="fake", note="Copie d'une marque",
                              phone="6 70 00 00 21", country_id=self.env.ref("base.cm").id)
        self.assertIn("the team of OCD Live looks at it within 24 hours", response.text)
        report = self.env["ocd.report"].search([("product_id", "=", product.id)])
        self.assertEqual((report.reason, report.vendor_id, report.partner_id.phone), ("fake", self.brenda, "+237 670000021"))
        response = self._post("/ocd/signaler", produit=product.id, reason="fake", phone="6 70 00 00 21",
                              country_id=self.env.ref("base.cm").id)
        self.assertIn("You already reported it today", response.text)
        # Without a number: once a day per device
        self._post("/ocd/signaler", produit=product.id, reason="misleading")
        response = self._post("/ocd/signaler", produit=product.id, reason="misleading")
        self.assertIn("You already reported it today", response.text)
        items = {item["key"]: item for column in self.Verification._ocd_columns() for item in column["items"]}
        item = items[f"report_product_{product.id}"]
        self.assertEqual(item["tag"], "2 reports")
        self.assertIn("Copie d'une marque", item["detail"])
        reason = self.env["ocd.listing.refuse.reason"].search([("applies_to", "=", "product")], limit=1)
        self.Verification.ocd_refuse("report_product", product.id, reason.id)
        self.assertEqual((product.ocd_review_state, product.is_published), ("refused", False))
        self.assertEqual(set(self.env["ocd.report"].search([("product_id", "=", product.id)]).mapped("state")), {"done"})

    def test_report_a_vendor_the_team_saw_it(self):
        self.authenticate(None, None)
        self.assertIn(f"/ocd/signaler?vendeur={self.fatou.id}", self.url_open(f"/ocd/boutique/{self.fatou.id}").text)
        self._post("/ocd/signaler", vendeur=self.fatou.id, reason="scam", note="Jamais livré")
        items = {item["key"]: item for column in self.Verification._ocd_columns() for item in column["items"]}
        self.assertEqual(items[f"report_vendor_{self.fatou.id}"]["reasons"], [], "Nothing to refuse: seen")
        self.assertEqual(self.fatou.ocd_report_count, 1)
        self.Verification.ocd_approve("report_vendor", self.fatou.id)
        self.assertEqual(self.env["ocd.report"].search([("vendor_id", "=", self.fatou.id)]).state, "dismissed")
        self.assertEqual(self.url_open("/ocd/signaler?vendeur=999999").status_code, 404)
