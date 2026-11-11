from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.fields import Command
from odoo.tests import HttpCase, tagged



@tagged("post_install", "-at_install")
class TestOcdLiveWebsite(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({"ocd_booking_open_date": False, "ocd_min_notice_hours": 2})
        cls.vendor = cls.env["res.partner"].create({
            "name": "Awa Mensah",
            "ocd_is_vendor": True,
            "ocd_business": "Cakes",
            "ocd_vendor_state": "approved",
            "phone": "+228 90 00 00 07",
            "country_id": cls.env.ref("base.tg").id,
        })
        cls.day = fields.Date.today() + timedelta(days=8)
        cls.discovery = cls.env.ref("ocd_live.product_package_discovery").product_variant_id

    def test_booking_pages_day_first(self):
        self.assertEqual(self.company.ocd_booking_flow, "day_first")
        response = self.url_open("/reserver")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/reserver/studio", response.text)
        response = self.url_open("/reserver/studio")
        self.assertIn(f"/reserver/studio/{self.day.isoformat()}", response.text)
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}")
        self.assertIn(f"/reserver/studio/{self.day.isoformat()}/0830", response.text)
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}/0830")
        self.assertIn(f"/reserver/studio/{self.day.isoformat()}/0830/{self.discovery.id}", response.text)
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}/0830/{self.discovery.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn('name="phone"', response.text)

    def test_booking_pages_package_first(self):
        self.company.ocd_booking_flow = "package_first"
        response = self.url_open("/reserver/remote")
        self.assertIn(f"/reserver/remote/paquet/{self.discovery.id}", response.text)
        response = self.url_open(f"/reserver/remote/paquet/{self.discovery.id}")
        self.assertIn(f"/reserver/remote/paquet/{self.discovery.id}/{self.day.isoformat()}", response.text)
        response = self.url_open(f"/reserver/remote/paquet/{self.discovery.id}/{self.day.isoformat()}")
        self.assertIn(f"/reserver/remote/{self.day.isoformat()}/0830/{self.discovery.id}", response.text)

    def test_bad_urls(self):
        self.assertEqual(self.url_open("/reserver/moon").status_code, 404)
        self.assertEqual(self.url_open("/reserver/studio/2020-01-01").status_code, 404)
        self.assertEqual(self.url_open(f"/reserver/studio/{self.day.isoformat()}/0900").status_code, 404)

    def _confirm_form(self, **values):
        return {
            "csrf_token": self.csrf_token(),
            "mode": "studio",
            "day": self.day.isoformat(),
            "hour": "1000",
            "product_id": self.discovery.id,
            "name": "Rose Delices",
            "city": "Lome",
            "category_id": self.env.ref("ocd_live.category_food").id,
            "phone": "90 11 22 33",
            "country_id": self.env.ref("base.tg").id,
            "studio_need": "table",
            "optin": "1",
            **values,
        }

    def test_booking_is_created_and_sent_to_the_payment(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/confirmer", data=self._confirm_form(), allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/ocd/payer/", response.headers["Location"])
        booking = self.env["ocd.live.booking"].search([("partner_id.name", "=", "Rose Delices")])
        self.assertEqual(booking.state, "draft")
        self.assertEqual(booking.studio_need, "table")
        vendor = booking.partner_id
        self.assertTrue(vendor.ocd_is_vendor)
        self.assertEqual(vendor.ocd_vendor_state, "to_check")
        self.assertEqual(vendor.phone, "+228 90112233", "The number gets the dialing code of its country")
        self.assertEqual(vendor.ocd_category_id, self.env.ref("ocd_live.category_food"))
        self.assertTrue(vendor.ocd_whatsapp_optin)
        # Back from the payment page, the same choice keeps the same held slot
        response = self.url_open("/reserver/confirmer", data=self._confirm_form(), allow_redirects=False)
        self.assertEqual(response.headers["Location"], booking.sale_order_id and response.headers["Location"])
        self.assertEqual(self.env["ocd.live.booking"].search_count([("partner_id", "=", vendor.id)]), 1)

    def test_booking_form_errors(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/confirmer", data=self._confirm_form(name="R", phone="123"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-invalid="true"', response.text)
        self.assertEqual(response.text.count('class="o_ocd_error"'), 2)
        self.assertFalse(self.env["ocd.live.booking"].search([("partner_id.name", "=", "R")]))
        # Reloading the page (or the phone reopening the tab) shows the step again, not /reserver/confirmer
        self.assertIn(
            f'data-ocd-url="/reserver/studio/{self.day.isoformat()}/1000/{self.discovery.id}"', response.text
        )

    def test_confirm_and_waiting_list_opened_without_the_form(self):
        for url in ("/reserver/confirmer", "/reserver/attente"):
            response = self.url_open(url, allow_redirects=False)
            self.assertIn(response.status_code, (302, 303), url)
            self.assertTrue(response.headers["Location"].endswith("/reserver"), url)

    def test_hour_no_longer_bookable_goes_back_to_the_hours(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/confirmer", data=self._confirm_form(hour="0900"), allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn(f"/reserver/studio/{self.day.isoformat()}?occupe=1", response.headers["Location"])
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}?occupe=1")
        self.assertIn("This hour can no longer be booked", response.text)
        response = self.url_open("/reserver/confirmer", data=self._confirm_form(day="2020-01-01"), allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith("/reserver/studio"))
        self.assertFalse(self.env["ocd.live.booking"].search([("partner_id.name", "=", "Rose Delices")]))

    def _book(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/confirmer", data=self._confirm_form(), allow_redirects=False)
        booking = self.env["ocd.live.booking"].search([("partner_id.name", "=", "Rose Delices")])
        return booking, response.headers["Location"]

    def test_payment_page_offers_the_providers_of_the_country(self):
        booking, pay_url = self._book()
        order = booking.sale_order_id
        self.assertEqual(self.url_open(f"/ocd/payer/{order.id}?access_token=wrong").status_code, 404)
        # The Mobile Money checked by the team is a provider of Odoo, archived until the team
        # configures it: the page offers what Odoo offers for the country of the vendor.
        provider = self.env.ref("ocd_live.payment_provider_momo_team")
        response = self.url_open(pay_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(f'data-provider-id="{provider.id}"', response.text)
        provider.write({"active": True})
        response = self.url_open(pay_url)
        self.assertIn(f'data-provider-id="{provider.id}"', response.text)
        self.assertIn('name="o_payment_submit_button"', response.text)
        self.assertIn(f"/ocd/payer/{order.id}", response.text, "The vendor comes back to this page after paying")
        provider.available_country_ids = self.env.ref("base.cm")
        response = self.url_open(pay_url)
        self.assertNotIn(f'data-provider-id="{provider.id}"', response.text, "Not offered outside its countries")

    def test_payment_status_and_ticket(self):
        booking, pay_url = self._book()
        order = booking.sale_order_id
        token = order.access_token
        result = self.make_jsonrpc_request(f"/ocd/payer/{order.id}/statut", {"access_token": token})
        self.assertEqual(result["state"], "form")
        # The ticket waits for the payment
        response = self.url_open(f"/ocd/ticket/{booking.id}?access_token={token}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        order.action_confirm()
        self.assertEqual(booking.state, "confirmed")
        result = self.make_jsonrpc_request(f"/ocd/payer/{order.id}/statut", {"access_token": token})
        self.assertEqual(result["state"], "done")
        response = self.url_open(f"/ocd/ticket/{booking.id}?access_token={token}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(booking.ticket_code, response.text)
        self.assertIn(f"/ocd/deplacer/{booking.id}", response.text)
        # The browser of the new vendor keeps its space; another browser needs the token
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/ocd/ticket/{booking.id}?access_token=wrong").status_code, 404)

    def test_move_a_live_from_the_ticket(self):
        booking, _pay_url = self._book()
        order = booking.sale_order_id
        order.action_confirm()
        token = order.access_token
        response = self.url_open(f"/ocd/deplacer/{booking.id}?access_token={token}")
        self.assertEqual(response.status_code, 200)
        new_day = self.day + timedelta(days=1)
        self.assertIn(f"/ocd/deplacer/{booking.id}/{new_day.isoformat()}", response.text)
        response = self.url_open(f"/ocd/deplacer/{booking.id}/{new_day.isoformat()}?access_token={token}")
        self.assertEqual(response.status_code, 200)
        response = self.url_open(f"/ocd/deplacer/{booking.id}/{new_day.isoformat()}?access_token={token}", data={
            "csrf_token": self.csrf_token(), "hour": "1130",
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        local = booking.company_id._ocd_to_local(booking.start_datetime)
        self.assertEqual((local.date(), local.strftime("%H%M")), (new_day, "1130"))
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/ocd/deplacer/{booking.id}?access_token=wrong").status_code, 404)

    def test_wait_for_a_free_hour(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/attente", data={
            "csrf_token": self.csrf_token(),
            "mode": "studio",
            "day": self.day.isoformat(),
            "phone": "90 44 55 66",
            "country_id": self.env.ref("base.tg").id,
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("attente=1", response.headers["Location"])
        entry = self.env["ocd.live.waitlist"].search([("day", "=", self.day)])
        self.assertEqual(entry.partner_id.phone, "+228 90445566")
        self.assertEqual(entry.state, "waiting")

    def test_prices_follow_the_pricelist_of_the_country(self):
        """The packages show the price of the pricelist Odoo gives to the vendor, in its
        currency: Odoo chooses it from the country of the vendor."""
        xaf = self.env.ref("base.XAF")
        xaf.active = True
        self.env["res.config.settings"].create({"group_product_pricelist": True}).execute()
        group = self.env["res.country.group"].create({
            "name": "CEMAC", "country_ids": [(6, 0, self.env.ref("base.cm").ids)],
        })
        self.env["product.pricelist"].create({
            "name": "Cameroon", "currency_id": xaf.id, "country_group_ids": [(6, 0, group.ids)],
        })
        self.vendor.write({"country_id": self.env.ref("base.cm").id, "phone": "+237 670000007"})
        token = self.vendor._ocd_get_space_token()
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{token}")
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}/0830")
        self.assertIn("FCFA", response.text)

    def test_honeypot_stops_the_robots(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/confirmer", data={
            "csrf_token": self.csrf_token(),
            "mode": "studio",
            "day": self.day.isoformat(),
            "hour": "1000",
            "product_id": self.discovery.id,
            "name": "Robot",
            "business": "Spam",
            "phone": "+228 90 11 22 34",
            "website_url": "https://spam.example",
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.env["res.partner"].search([("name", "=", "Robot")]))

    def test_directory_pages(self):
        self.assertEqual(self.url_open("/lives").status_code, 200)
        self.assertEqual(self.url_open("/lives/tg").status_code, 200)
        self.assertEqual(self.url_open("/lives/zz").status_code, 404)

    def test_space_with_the_personal_link(self):
        token = self.vendor._ocd_get_space_token()
        response = self.url_open(f"/ocd/espace/{token}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Awa Mensah", response.text)
        self.assertEqual(self.url_open("/ocd/espace/not-a-valid-token-at-all").status_code, 404)
        self.company.ocd_vendor_login = "whatsapp_code"
        self.assertEqual(self.url_open(f"/ocd/espace/{token}").status_code, 404, "The links stop in code mode")

    def _vendor_account(self):
        self.env["res.users"].create({
            "name": "Awa Mensah",
            "login": "awa-ocd",
            "password": "awa-ocd-2026",
            "partner_id": self.vendor.id,
            "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
        })
        self.authenticate("awa-ocd", "awa-ocd-2026")

    def test_space_of_a_vendor_logged_in_with_an_odoo_account(self):
        # The Odoo account (checked by a password) opens the space: no number, link or code to ask
        self._vendor_account()
        for login in ("link", "whatsapp_code", "password"):
            self.company.ocd_vendor_login = login
            response = self.url_open("/ocd/connexion")
            self.assertTrue(response.url.endswith("/ocd/espace/moi"), login)
            self.assertIn("Awa Mensah", response.text, login)
            # Leaving the space logs out of Odoo (forgetting the number would open it again)
            self.assertIn("/web/session/logout?redirect=/ocd/connexion", response.text, login)

    def test_space_with_a_whatsapp_code(self):
        self.company.ocd_vendor_login = "whatsapp_code"
        self.authenticate(None, None)
        sent = []
        with patch.object(type(self.env["res.partner"]), "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
            response = self.url_open("/ocd/connexion", data={
                "csrf_token": self.csrf_token(), "phone": "90 00 00 07",
            })
        self.assertIn('name="code"', response.text)
        response = self.url_open("/ocd/connexion/code", data={
            "csrf_token": self.csrf_token(), "code": sent[0],
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Awa Mensah", response.text)

    def test_unknown_number_gets_the_same_answer(self):
        self.company.ocd_vendor_login = "whatsapp_code"
        self.authenticate(None, None)
        response = self.url_open("/ocd/connexion", data={
            "csrf_token": self.csrf_token(), "phone": "+228 99 99 99 99",
        })
        self.assertIn('name="code"', response.text)

    def test_voice_of_a_page(self):
        result = self.make_jsonrpc_request("/ocd/voix/day", {"lang": "fr"})
        self.assertEqual(result["speech_code"], "fr-FR")
        self.assertTrue(result["text"])

    def test_place_a_live_with_a_credit(self):
        duo = self.env.ref("ocd_live.product_package_duo").product_variant_id
        order = self.env["sale.order"].create({
            "partner_id": self.vendor.id,
            "order_line": [(0, 0, {"product_id": duo.id, "product_uom_qty": 1})],
        })
        order.action_confirm()
        credit = order.order_line.ocd_credit_ids
        token = self.vendor._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/espace/{token}")
        self.assertIn(f"/ocd/espace/moi/placer/{credit.id}", response.text)
        response = self.url_open(f"/ocd/espace/moi/placer/{credit.id}?mode=remote")
        self.assertEqual(response.status_code, 200)
        day = self.day.isoformat()
        self.assertIn(f"/ocd/espace/moi/placer/{credit.id}/{day}?mode=remote", response.text)
        response = self.url_open(f"/ocd/espace/moi/placer/{credit.id}/{day}?mode=remote")
        self.assertIn('name="hour" value="1300"', response.text)
        response = self.url_open(f"/ocd/espace/moi/placer/{credit.id}/{day}", data={
            "csrf_token": self.csrf_token(), "mode": "remote", "hour": "1300",
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        booking = credit.booking_ids
        self.assertIn(f"/ocd/ticket/{booking.id}", response.headers["Location"])
        self.assertEqual(booking.state, "confirmed")
        self.assertEqual(booking.mode, "remote")
        self.assertEqual(credit.remaining, 1)
        # Another browser cannot place the lives of the vendor
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/ocd/espace/moi/placer/{credit.id}?mode=remote").status_code, 404)

    def test_space_shows_the_lives_and_the_whatsapp_choice(self):
        booking, _pay_url = self._book()
        booking.sale_order_id.action_confirm()
        response = self.url_open("/ocd/espace/moi")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"/ocd/ticket/{booking.id}", response.text)
        self.assertIn(f"/ocd/deplacer/{booking.id}", response.text)
        vendor = booking.partner_id
        self.assertTrue(vendor.ocd_whatsapp_optin)
        self.url_open("/ocd/espace/moi/whatsapp", data={"csrf_token": self.csrf_token()})
        self.assertFalse(vendor.ocd_whatsapp_optin, "The vendor stopped the messages")

    def test_pass_then_link_then_answer(self):
        """A visitor takes the pass, sends the link of the live, then sees the answer."""
        self.authenticate(None, None)
        response = self.url_open("/lives/pass")
        self.assertEqual(response.status_code, 200)
        response = self.url_open("/lives/pass", data={
            "csrf_token": self.csrf_token(),
            "name": "Brenda Wax",
            "phone": "91 22 33 44",
            "country_id": self.env.ref("base.tg").id,
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/ocd/payer/", response.headers["Location"])
        vendor = self.env["res.partner"].search([("name", "=", "Brenda Wax")])
        order = vendor.sale_order_ids
        self.assertEqual(order.order_line.product_id, self.env.ref("ocd_live.product_directory_pass").product_variant_id)
        self.assertEqual(self.url_open("/lives/envoyer", allow_redirects=False).status_code, 303, "The pass is not paid yet")
        order.action_confirm()
        self.assertTrue(vendor.ocd_pass_active)
        self.assertEqual(self.url_open("/lives/envoyer").status_code, 200)
        response = self.url_open("/lives/envoyer", data={
            "csrf_token": self.csrf_token(),
            "url": "www.tiktok.com/@brenda.wax/live",
            "title": "Brenda Wax Lome",
            "country_id": self.env.ref("base.cm").id,
            "category_id": self.env.ref("ocd_live.category_clothes").id,
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        listing = vendor.ocd_listing_ids
        self.assertIn(f"/lives/statut/{listing.id}", response.headers["Location"])
        self.assertEqual(listing.url, "https://www.tiktok.com/@brenda.wax/live")
        self.assertEqual((listing.title, listing.country_id.code), ("Brenda Wax Lome", "CM"))
        self.assertEqual(self.url_open(f"/lives/statut/{listing.id}").status_code, 200)
        result = self.make_jsonrpc_request(f"/lives/statut/{listing.id}/etat", {})
        self.assertEqual(result["state"], "pending")
        listing.write({"state": "to_check"})
        listing.action_publish()
        self.assertIn("Brenda Wax Lome", self.url_open("/lives/cm").text)
        self.url_open(f"/lives/statut/{listing.id}/fin", data={"csrf_token": self.csrf_token()})
        self.assertEqual(listing.state, "ended")
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/lives/statut/{listing.id}").status_code, 404)

    def test_tell_me_when_the_directory_opens(self):
        self.authenticate(None, None)
        response = self.url_open("/lives/prevenir", data={
            "csrf_token": self.csrf_token(), "phone": "90 55 66 77", "country_id": self.env.ref("base.tg").id,
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        alert = self.env["ocd.directory.alert"].search([])
        self.assertEqual(alert.partner_id.phone, "+228 90556677")
        self.assertEqual(alert.state, "waiting")
        with patch.object(type(self.env["ocd.directory.alert"]), "_ocd_send_window_open", lambda alerts: True):
            alert.window_start = fields.Datetime.now()
            self.env["ocd.directory.listing"]._cron_update_windows()
        self.assertEqual(alert.state, "sent")

    def test_price_of_the_hours_is_shown(self):
        from odoo.addons.ocd_live.models.ocd_live_price_rule import RULE_DAY_FIELDS

        days = {field: False for field in RULE_DAY_FIELDS}
        days[RULE_DAY_FIELDS[self.day.weekday()]] = True
        self.env["ocd.live.price.rule"].create({"name": "Evening", "percent": 25, "hour_from": 17.5, **days})
        self.discovery.list_price = 15000
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}")
        self.assertIn("o_ocd_slot_price", response.text)
        self.assertIn("+25", response.text)
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}/1900")
        self.assertIn("18,750", response.text, "The package costs 25 % more at 19:00")
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}/1000")
        self.assertNotIn("18,750", response.text)
