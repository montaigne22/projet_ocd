from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live import page_cache
from odoo.addons.ocd_live.tests.test_card_media import png

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
        # The product page offers WhatsApp (the product is not sold on the website)
        self.assertIn(self.cake.website_url, response.text)
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

    def test_boutique_tells_the_next_live_and_the_old_form_follows(self):
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/boutique/{self.awa.id}")
        self.assertIn("No live planned for now", response.text)
        self.assertIn("Direct contact with the vendor", response.text)
        self.assertIn(f"/ocd/boutique/{self.awa.id}/ecrire", response.text)
        self.assertIn(f'href="/ocd/suivre/{self.awa.id}?depuis=', response.text)
        # The form « Tell me on WhatsApp » of a page kept by a browser: the lives are followed
        response = self.url_open(f"/ocd/boutique/{self.awa.id}/prevenir", data={
            "csrf_token": self.csrf_token(),
            "country_id": self.env.ref("base.tg").id,
            "phone": "90 11 22 33",
        })
        self.assertIn("You follow Awa: a WhatsApp at each live.", response.text)
        follower = self.env["ocd.vendor.follower"].search([("vendor_id", "=", self.awa.id)])
        self.assertEqual((follower.lives, follower.news), (True, False), "Never the news without asking")
        self.assertEqual(follower.partner_id.phone, "+228 90112233")
        # A wrong number is said on the page
        response = self.url_open(f"/ocd/boutique/{self.awa.id}/prevenir", data={
            "csrf_token": self.csrf_token(),
            "country_id": self.env.ref("base.tg").id,
            "phone": "12",
        })
        self.assertIn("You are told on WhatsApp when it starts", response.text, "This browser follows already")

    def test_followers_are_told_when_the_live_starts(self):
        Follower = self.env["ocd.vendor.follower"]
        follower = Follower._ocd_follow(self.awa, Follower._ocd_contact("+228 90112233"))
        follower.followed_at = fields.Datetime.now() - timedelta(days=1)
        told = []
        with patch.object(type(Follower), "_ocd_tell_live", lambda followers, live: told.append((followers, live))):
            self.env["ocd.boutique.alert"]._ocd_send_due()
            self.assertFalse(told, "No live yet")
            live = self._live_now(self.awa)
            self.env["ocd.boutique.alert"]._ocd_send_due()
            self.assertEqual(told, [(follower, live)])
            self.assertTrue(live.ocd_followers_told_at)
            self.env["ocd.boutique.alert"]._ocd_send_due()
            self.assertEqual(len(told), 1, "Once per live")

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
        # Sold only while in stock, as the shop of Odoo does
        self.dress.product_tmpl_id.write({"is_storable": True, "allow_out_of_stock_order": False})
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

    def test_tour_of_the_courier(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        token = self.courier._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/livrer/{token}")
        self.assertIn("My tour", response.text)
        self.assertIn("Pick up at Brenda Wax", response.text)
        self.assertIn("Deliver to Estelle Ngono", response.text)
        self.assertIn("First pick the parcel up at Brenda Wax.", response.text)
        self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/pickup", data={"csrf_token": self.csrf_token()})
        response = self.url_open(f"/ocd/livrer/{token}")
        self.assertNotIn("Pick up at Brenda Wax", response.text)
        self.assertIn("I leave to deliver", response.text)
        # The courier ends the service: no new parcel for them
        self.assertTrue(self.courier.ocd_courier_available)
        self.url_open(f"/ocd/livrer/{token}/service", data={"csrf_token": self.csrf_token()})
        self.assertFalse(self.courier.ocd_courier_available)
        # A vendor has no service to end
        brenda_token = self.brenda._ocd_get_space_token()
        response = self.url_open(f"/ocd/livrer/{brenda_token}/service", data={"csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 404)

    def test_vendor_sees_the_courier_and_the_delivered_parcels(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        token = self.brenda._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/livrer/{token}")
        self.assertIn("Hello Brenda", response.text)
        self.assertIn("For Estelle Ngono", response.text)
        self.assertIn("Junior, OCD courier, picks it up", response.text)
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        response = self.url_open(f"/ocd/livrer/{token}?vue=livres")
        self.assertIn("Estelle Ngono", response.text)
        self.assertIn("Code checked", response.text)
        self.assertIn("Delivered · 1", response.text)

    def test_courier_resumes_after_a_problem(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        token = self.courier._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/problem", data={
            "csrf_token": self.csrf_token(), "reason": "absent",
        })
        self.assertEqual(parcel.ocd_stage, "problem")
        self.assertIn("Reported: customer absent.", response.text)
        self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/retry", data={"csrf_token": self.csrf_token()})
        self.assertEqual(parcel.ocd_stage, "picked")

    # === PUBLIC PAGES KEPT IN MEMORY (ocd_live.page_cache) === #

    def _keep_pages(self):
        """Keep the public pages in memory during this test (off during the other tests)."""
        patcher = patch.object(page_cache, "IN_TESTS", True)
        patcher.start()
        self.addCleanup(patcher.stop)
        page_cache.clear()
        self.addCleanup(page_cache.clear)

    def _origin(self, path, **session):
        """Where the page `path` comes from for a new visitor (hit: from memory, miss: built and
        kept, pass: built for this visitor)."""
        self.authenticate(None, None, session_extra=session)
        response = self.url_open(path)
        self.assertEqual(response.status_code, 200)
        return response.headers.get(page_cache.HEADER)

    def test_visits_of_a_live_counted_from_memory(self):
        """During the live, the boutique comes from memory for the next visitors: each new
        browser is still counted once, for the control room."""
        self._keep_pages()
        booking = self._live_now(self.brenda, live_url="https://www.tiktok.com/@brenda.wax/live")
        path = f"/ocd/boutique/{self.brenda.id}"
        self.assertEqual(self._origin(path), "miss")
        self.assertEqual(self._origin(path), "hit")
        self.assertEqual(self.url_open(path).headers.get(page_cache.HEADER), "hit")  # the same browser again
        booking.invalidate_recordset(["ocd_visit_count"])
        self.assertEqual(booking.ocd_visit_count, 2, "Two browsers")
        # The product on screen: one question of the boutique for all its visitors
        self.authenticate(None, None)
        for origin in ("miss", "hit"):
            response = self.url_open(path + "/live", json={"jsonrpc": "2.0", "method": "call", "params": {}})
            self.assertEqual(response.headers.get(page_cache.HEADER), origin)

    def test_shop_pages_kept_except_for_a_customer_with_a_cart(self):
        self._keep_pages()
        self.dress.product_tmpl_id.image_1920 = BinaryBytes(png())
        product_url = self.dress.product_tmpl_id.website_url
        for path in ("/shop", product_url):
            self.assertEqual(self._origin(path), "miss", path)
            self.assertEqual(self._origin(path), "hit", path)
        self.assertEqual(self._origin("/shop", sale_order_id=10**9), "pass", "The cart is in the header")
        self.assertEqual(self._origin(f"{product_url}?search=robe"), "pass")
        # The photos of the cards: with their version, kept a year
        response = self.url_open("/shop")
        self.assertIn(self.dress.product_tmpl_id._ocd_image_url("image_512"), response.text)
