from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged

from odoo.addons.ocd_live.models.res_partner import ResPartner


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

    def test_booking_is_created_and_sent_to_the_payment(self):
        self.authenticate(None, None)
        response = self.url_open("/reserver/confirmer", data={
            "csrf_token": self.csrf_token(),
            "mode": "studio",
            "day": self.day.isoformat(),
            "hour": "1000",
            "product_id": self.discovery.id,
            "name": "Rose Delices",
            "business": "Cakes and juices",
            "phone": "+228 90 11 22 33",
            "country_id": self.env.ref("base.tg").id,
            "studio_need": "table",
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/my/orders/", response.headers["Location"])
        booking = self.env["ocd.live.booking"].search([("partner_id.name", "=", "Rose Delices")])
        self.assertEqual(booking.state, "draft")
        self.assertEqual(booking.studio_need, "table")
        self.assertTrue(booking.partner_id.ocd_is_vendor)
        self.assertEqual(booking.partner_id.ocd_vendor_state, "to_check")

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

    def test_space_with_a_whatsapp_code(self):
        self.company.ocd_vendor_login = "whatsapp_code"
        self.authenticate(None, None)
        sent = []
        with patch.object(ResPartner, "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
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
        start = self.env.company._ocd_slot_starts(self.day)[3]
        response = self.url_open(f"/ocd/espace/moi/placer/{credit.id}", data={
            "csrf_token": self.csrf_token(),
            "mode": "remote",
            "start": fields.Datetime.to_string(start),
        })
        self.assertEqual(response.status_code, 200)
        booking = credit.booking_ids
        self.assertEqual(booking.state, "confirmed")
        self.assertEqual(booking.mode, "remote")
        self.assertEqual(credit.remaining, 1)
