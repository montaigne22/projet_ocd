from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdShopWebsite(HttpCase, OcdShopCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dress.product_tmpl_id.is_published = True
        cls.awa = cls.env["res.partner"].create({
            "name": "Awa Mensah",
            "ocd_is_vendor": True,
            "ocd_vendor_state": "approved",
            "ocd_sale_mode": "direct",
            "phone": "+228 90 00 00 07",
        })
        cls.cake = cls.env["product.template"].create({
            "name": "Gateau ananas",
            "list_price": 5000,
            "ocd_vendor_id": cls.awa.id,
            "is_published": True,
        })

    def test_boutique_of_a_vendor_sold_by_ocd(self):
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Robe en wax", response.text)
        self.assertIn(self.dress.product_tmpl_id.website_url, response.text)

    def test_boutique_in_direct_contact(self):
        response = self.url_open(f"/ocd/boutique/{self.awa.id}")
        self.assertIn(f"/ocd/wa/{self.cake.id}", response.text)
        response = self.url_open(f"/ocd/wa/{self.cake.id}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].startswith("https://wa.me/22890000007?text="))
        self.assertEqual(self.cake.ocd_wa_clicks, 1)

    def test_unapproved_vendor_has_no_boutique(self):
        self.awa.ocd_vendor_state = "to_check"
        self.assertEqual(self.url_open(f"/ocd/boutique/{self.awa.id}").status_code, 404)

    def test_vendor_prepares_and_courier_delivers(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        brenda_token = self.brenda._ocd_get_space_token()
        junior_token = self.courier._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/livrer/{brenda_token}")
        self.assertIn("Estelle Ngono", response.text)
        self.url_open(f"/ocd/livrer/{brenda_token}/colis/{parcel.id}/ready", data={"csrf_token": self.csrf_token()})
        self.assertEqual(parcel.ocd_stage, "ready")
        response = self.url_open(f"/ocd/livrer/{junior_token}")
        self.assertIn("Estelle Ngono", response.text)
        self.url_open(f"/ocd/livrer/{junior_token}/colis/{parcel.id}/pickup", data={"csrf_token": self.csrf_token()})
        self.url_open(f"/ocd/livrer/{junior_token}/colis/{parcel.id}/leave", data={"csrf_token": self.csrf_token()})
        self.assertEqual(parcel.ocd_stage, "on_the_way")
        self.url_open(f"/ocd/livrer/{junior_token}/colis/{parcel.id}/collect", data={
            "csrf_token": self.csrf_token(), "method": "cash",
        })
        self.assertEqual(parcel.ocd_cod_state, "collected")
        response = self.url_open(f"/ocd/livrer/{junior_token}/colis/{parcel.id}/code", data={
            "csrf_token": self.csrf_token(), "code": "nope",
        })
        self.assertIn("Attempts left: 2", response.text)
        self.assertEqual(parcel.ocd_code_attempts, 1, "The wrong attempt is saved")
        self.url_open(f"/ocd/livrer/{junior_token}/colis/{parcel.id}/code", data={
            "csrf_token": self.csrf_token(), "code": parcel.sudo().ocd_delivery_code,
        })
        self.assertEqual(parcel.ocd_stage, "delivered")

    def test_nobody_touches_the_parcels_of_others(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        other_token = self.courier_west._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/livrer/{other_token}/colis/{parcel.id}/pickup", data={"csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(parcel.ocd_stage, "to_prepare")
        self.assertEqual(self.url_open("/ocd/livrer/not-a-valid-token-at-all").status_code, 404)

    def test_customer_sees_the_code_on_the_order_page(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        response = self.url_open(order.get_portal_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"Code: {parcel.sudo().ocd_delivery_code}", response.text)

    def test_product_on_screen_during_the_live(self):
        now = fields.Datetime.now()
        self.company.ocd_booking_open_date = False
        today = self.company._ocd_local_today()
        current = [s for s in self.company._ocd_slot_starts(today) if s <= now < s + timedelta(hours=1.5)]
        if not current:
            self.skipTest("No slot of the studio covers the time of the test run")
        booking = self.env["ocd.live.booking"].create({
            "partner_id": self.brenda.id, "start_datetime": current[0], "mode": "studio",
        })
        booking._ocd_confirm()
        booking.current_product_tmpl_id = self.dress.product_tmpl_id
        result = self.make_jsonrpc_request(f"/ocd/boutique/{self.brenda.id}/live", {})
        self.assertEqual(result["id"], self.dress.product_tmpl_id.id)
        self.assertEqual(result["name"], "Robe en wax")
