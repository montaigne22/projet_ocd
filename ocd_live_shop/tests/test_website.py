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

    def _live_now(self, vendor, **values):
        """A confirmed live of `vendor` running now, written directly (no slot of the studio
        is needed for the pages)."""
        now = fields.Datetime.now()
        later = self.company._ocd_local_today() + timedelta(days=30)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": vendor.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "remote",
        })
        booking.write({"state": "confirmed", **values})
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [now - timedelta(minutes=18), now + timedelta(minutes=72), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        return booking

    def test_boutique_shows_the_live_and_the_product_on_screen(self):
        self._live_now(
            self.brenda,
            live_url="https://www.tiktok.com/@brenda.wax/live",
            current_product_tmpl_id=self.dress.product_tmpl_id.id,
        )
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}")
        self.assertIn("Live now", response.text)
        self.assertIn("For 18 min, on TikTok", response.text)
        self.assertIn("https://www.tiktok.com/@brenda.wax/live", response.text)
        self.assertIn("On screen now", response.text)
        self.assertIn("Sold and delivered by OCD Live", response.text)

    def test_boutique_tells_the_next_live_and_registers_an_alert(self):
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/boutique/{self.awa.id}")
        self.assertIn("No live planned for now", response.text)
        self.assertIn("Direct contact with the vendor", response.text)
        self.assertIn(f"/ocd/boutique/{self.awa.id}/ecrire", response.text)
        response = self.url_open(f"/ocd/boutique/{self.awa.id}/prevenir", data={
            "csrf_token": self.csrf_token(),
            "country_id": self.env.ref("base.tg").id,
            "phone": "90 11 22 33",
        })
        self.assertIn("goes live", response.text)
        alert = self.env["ocd.boutique.alert"].search([("vendor_id", "=", self.awa.id)])
        self.assertEqual(alert.state, "waiting")
        self.assertEqual(alert.partner_id.phone, "+228 90112233")
        # The same number twice: one alert
        self.url_open(f"/ocd/boutique/{self.awa.id}/prevenir", data={
            "csrf_token": self.csrf_token(),
            "country_id": self.env.ref("base.tg").id,
            "phone": "90 11 22 33",
        })
        self.assertEqual(self.env["ocd.boutique.alert"].search_count([("vendor_id", "=", self.awa.id)]), 1)
        # A wrong number is said on the page
        response = self.url_open(f"/ocd/boutique/{self.awa.id}/prevenir", data={
            "csrf_token": self.csrf_token(),
            "country_id": self.env.ref("base.tg").id,
            "phone": "12",
        })
        self.assertIn('class="o_ocd_alert"', response.text)

    def test_alert_is_sent_when_the_live_starts(self):
        alert = self.env["ocd.boutique.alert"]._ocd_register(self.awa, phone="+228 90112233")
        self.env["ocd.boutique.alert"]._ocd_send_due()
        self.assertEqual(alert.state, "waiting", "No live yet")
        live = self._live_now(self.awa)
        self.env["ocd.boutique.alert"]._ocd_send_due()
        self.assertEqual(alert.state, "sent")
        self.assertEqual(alert.booking_id, live)

    def test_whatsapp_of_a_vendor_in_direct_contact(self):
        response = self.url_open(f"/ocd/boutique/{self.awa.id}/ecrire", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].startswith("https://wa.me/22890000007?text="))

    def test_replay_with_the_moments(self):
        booking = self._live_now(self.brenda, replay_url="https://www.youtube.com/watch?v=abc")
        # The live is over: two days ago
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = start_datetime - interval '2 days', "
            "end_datetime = end_datetime - interval '2 days' WHERE id = %s",
            [booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        self.env["ocd.live.moment"].create({
            "booking_id": booking.id, "product_tmpl_id": self.dress.product_tmpl_id.id, "offset_seconds": 125,
        })
        booking.replay_published = True
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}")
        self.assertIn(f"/ocd/boutique/{self.brenda.id}/replay", response.text.replace("&amp;", "&"))
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}/replay")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Robe en wax", response.text)
        self.assertIn("https://www.youtube.com/watch?v=abc&amp;t=125s", response.text)
        self.assertIn("Video published on YouTube", response.text)

    def test_stock_of_the_products(self):
        self.dress.product_tmpl_id.is_storable = True
        robe = self.dress.product_tmpl_id
        self.assertTrue(robe.is_published)
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}")
        self.assertIn("Sold out", response.text)
        self.env["stock.quant"]._update_available_quantity(
            self.dress, self.env.ref("stock.warehouse0").lot_stock_id, 2
        )
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}")
        self.assertIn("Only 2 left", response.text)
        self.assertNotIn("Sold out", response.text)
