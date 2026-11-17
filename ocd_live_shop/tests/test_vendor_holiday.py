from datetime import timedelta
from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorHoliday(HttpCase, OcdShopCommon):
    """The holiday mode of a vendor (chantier 20, A.5 of the plan of « My products », design
    VacancesProximite): the products stay visible, the orders are paused everywhere, the customers
    who asked are told of the return."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        cls.dress_tmpl = cls.dress.product_tmpl_id
        cls.dress_tmpl.write({"is_published": True, "ocd_review_state": "approved"})
        cls.Alert = cls.env["ocd.boutique.alert"]

    def _leave(self, days=5, note="Bonnes fêtes !"):
        self.brenda._ocd_start_holiday(self.brenda._ocd_today() + timedelta(days=days), note)

    def test_the_orders_are_paused(self):
        self.authenticate(None, None)
        # A cart filled before the holiday
        self.url_open("/ocd/panier/ajouter", data={"csrf_token": self.csrf_token(), "product_template_id": self.dress_tmpl.id})
        self._leave()
        self.assertTrue(self.brenda._ocd_on_holiday())
        self.assertFalse(self.dress._is_add_to_cart_allowed())
        page = self.url_open(self.dress_tmpl.website_url).text
        self.assertIn("Brenda Wax is on holiday", page)
        self.assertIn("Orders paused until", page)
        self.assertIn("« Bonnes fêtes ! »", page)
        self.assertNotIn("o_ocd_variant_add", page, "No button to add to the cart")
        self.assertIn(f'action="/ocd/boutique/{self.brenda.id}/retour"', page)
        response = self.url_open("/ocd/panier/ajouter", data={"csrf_token": self.csrf_token(), "product_template_id": self.dress_tmpl.id},
                                 allow_redirects=False)
        self.assertIn("erreur=", response.headers["Location"])
        # The cart waits for the return: no checkout, no payment
        response = self.url_open("/shop/checkout", allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith("/shop/cart"))
        self.assertIn("Brenda Wax is on holiday until", self.url_open("/shop/cart").text)
        order = self.env["sale.order"].search([("order_line.product_id", "=", self.dress.id)], order="id desc", limit=1)
        self.assertFalse(order._is_cart_ready_for_checkout())
        # The boutique: the products stay visible, with the holiday
        boutique = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn("Robe en wax", boutique)
        self.assertIn("Tell me when they are back", boutique)
        # Back: the orders start again
        self.brenda._ocd_end_holiday()
        self.assertTrue(self.dress._is_add_to_cart_allowed())
        self.assertTrue(order._is_cart_ready_for_checkout())

    def test_a_vendor_in_direct_contact_on_holiday(self):
        self.brenda.ocd_sale_mode = "direct"
        self._leave()
        response = self.url_open(f"/ocd/wa/{self.dress_tmpl.id}", allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith(f"{self.dress_tmpl.website_url}#vacances"),
                        "No WhatsApp to order while the vendor is on holiday")
        self.assertEqual(self.dress_tmpl.ocd_wa_clicks, 0)

    def test_the_customers_are_told_of_the_return(self):
        self._leave(days=3)
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}/retour", data={
            "csrf_token": self.csrf_token(), "country_id": self.env.ref("base.cm").id, "phone": "6 70 00 00 09",
            "produit": self.dress_tmpl.id,
        }, allow_redirects=False)
        self.assertIn(f"{self.dress_tmpl.website_url}?retour=1", response.headers["Location"])
        back = self.Alert.search([("vendor_id", "=", self.brenda.id), ("kind", "=", "back")])
        self.assertEqual((back.state, back.partner_id.phone), ("waiting", "+237 670000009"))
        self.assertIn("Noted: we write to you on WhatsApp when Brenda is back.",
                      self.url_open(f"{self.dress_tmpl.website_url}?retour=1").text)
        # The same contact also waits for the next live: both are kept
        live = self.Alert._ocd_register(self.brenda, partner=back.partner_id)
        self.assertEqual(live.kind, "live")
        self.assertEqual(self.Alert._ocd_register(self.brenda, partner=back.partner_id, kind="back"), back)
        sent = []
        with patch.object(type(self.Alert), "_ocd_send_vendor_back", lambda alerts: sent.extend(alerts.ids)):
            self.env["res.partner"]._cron_holiday_back()
            self.assertFalse(sent, "Still on holiday")
            # The day of the return
            self.brenda.ocd_holiday_until = self.brenda._ocd_today()
            self.env["res.partner"]._cron_holiday_back()
        self.assertEqual(sent, back.ids)
        self.assertEqual((back.state, live.state), ("sent", "waiting"))
        self.assertFalse(self.brenda.ocd_holiday_until)

    def test_the_page_of_the_vendor(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn('href="/ocd/espace/moi/vacances"', page)
        today = self.brenda._ocd_today()
        for day, error in ((today, "tomorrow at the earliest"), (today + timedelta(days=61), "60 days at most")):
            page = self.url_open("/ocd/espace/moi/vacances", data={"csrf_token": self.csrf_token(), "retour_le": str(day)}).text
            self.assertIn(error, page)
        self.assertFalse(self.brenda.ocd_holiday_until)
        response = self.url_open("/ocd/espace/moi/vacances", data={
            "csrf_token": self.csrf_token(), "retour_le": str(today + timedelta(days=10)), "mot": "Nouvelle collection au retour",
        }, allow_redirects=False)
        self.assertIn("parti=1", response.headers["Location"])
        self.assertEqual(self.brenda.ocd_holiday_note, "Nouvelle collection au retour")
        self.assertIn("On holiday until", self.url_open("/ocd/espace/moi").text)
        self.assertIn("Come back now", self.url_open("/ocd/espace/moi/vacances").text)
        self.url_open("/ocd/espace/moi/vacances/fin", data={"csrf_token": self.csrf_token()})
        self.assertFalse(self.brenda._ocd_on_holiday())

    def test_back_in_stock_waits_for_the_return(self):
        self.dress_tmpl.is_storable = True
        alert = self.env["ocd.stock.alert"]._ocd_register(self.dress, phone="+237 670000009")
        self._leave()
        self.dress._ocd_change_stock(2)
        self.assertFalse(self.env["ocd.stock.alert"]._ocd_available(self.dress), "The orders are paused")
        self.env["ocd.stock.alert"]._ocd_send_back()
        self.assertEqual(alert.state, "waiting")
        self.brenda._ocd_end_holiday()
        self.assertTrue(self.env["ocd.stock.alert"]._ocd_available(self.dress))
