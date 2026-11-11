import re
from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdCourierLogin(HttpCase, OcdShopCommon):
    """The courier gives its number and receives its link or a code on WhatsApp, as the vendors
    do; only a contact the team made a courier; the phone remembers it until it logs out."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cameroon = cls.env.ref("base.cm")
        cls.courier.write({"phone": "+237 650 11 22 33", "country_id": cls.cameroon.id})
        cls.Partner = type(cls.env["res.partner"])

    def _post(self, url, **data):
        return self.url_open(url, data={"csrf_token": self.csrf_token(), **data})

    def _ask(self, url="/ocd/livrer", phone="650 11 22 33"):
        return self._post(url, phone=phone, country_id=self.cameroon.id)

    def test_courier_receives_its_link_with_its_number(self):
        self.company.ocd_vendor_login = "link"
        self.authenticate(None, None)
        self.assertIn('action="/ocd/livrer"', self.url_open("/ocd/livrer").text)
        with patch.object(self.Partner, "_ocd_send_delivery_link", autospec=True, return_value=True) as send:
            response = self._ask()
            self.assertIn("o_ocd_ok_big", response.text)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[0], self.courier)
            self.assertIn(f"/ocd/livrer/{self.courier._ocd_get_space_token()}", send.call_args.args[1])
            # Asked again at once: no second message (one a minute at most)
            self._ask()
            self.assertEqual(send.call_count, 1)
            # A contact that is not a courier: the same answer, nothing sent
            self.courier.ocd_is_courier = False
            response = self._ask()
            self.assertIn("o_ocd_ok_big", response.text)
            self.assertEqual(send.call_count, 1)

    def test_courier_logs_in_with_a_code_and_logs_out(self):
        self.company.ocd_vendor_login = "whatsapp_code"
        self.authenticate(None, None)
        # In the code mode, the personal link does not open the app: the page of the number
        response = self.url_open(f"/ocd/livrer/{self.courier._ocd_get_space_token()}")
        self.assertTrue(response.url.endswith("/ocd/livrer"))
        self.assertIn('name="phone"', response.text)
        sent = []
        with patch.object(self.Partner, "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
            response = self._ask()
        self.assertIn('action="/ocd/livrer/code"', response.text)
        self.assertEqual(len(sent), 1)
        response = self._post("/ocd/livrer/code", code="000000" if sent[0] != "000000" else "111111")
        self.assertIn("o_ocd_error", response.text)
        response = self._post("/ocd/livrer/code", code=sent[0])
        self.assertTrue(response.url.endswith("/ocd/livrer/moi"))
        self.assertIn("My tour", response.text)
        self.assertIn('action="/ocd/livrer/deconnexion"', response.text)
        # The phone remembers the courier, even when the session of Odoo is lost (ended after 7
        # days without a change, or replaced): the cookie of the phone opens the app again
        self.assertIn("My tour", self.url_open("/ocd/livrer").text)
        self.opener.cookies.set("session_id", None)
        page = self.url_open("/ocd/livrer/moi")
        self.assertTrue(page.url.endswith("/ocd/livrer/moi"))
        self.assertIn("My tour", page.text)
        # A link loaded in advance by the browser (prefetch) logs nobody out
        self.url_open("/ocd/livrer/deconnexion")
        self.assertIn("My tour", self.url_open("/ocd/livrer/moi").text)
        # Log out (a form): the number is asked again, on this phone too
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        response = self.url_open("/ocd/livrer/deconnexion", data={"csrf_token": token})
        self.assertTrue(response.url.endswith("/ocd/livrer"))
        self.assertIn('name="phone"', response.text)
        self.assertTrue(self.url_open("/ocd/livrer/moi").url.endswith("/ocd/livrer"))
        self.opener.cookies.set("session_id", None)
        self.assertTrue(self.url_open("/ocd/livrer/moi").url.endswith("/ocd/livrer"))

    def test_password_mode_gives_a_code_to_the_couriers(self):
        self.company.ocd_vendor_login = "password"
        self.authenticate(None, None)
        sent = []
        with patch.object(self.Partner, "_ocd_deliver_login_code", lambda partner, code: sent.append(code) or True):
            response = self._ask()
        self.assertIn('action="/ocd/livrer/code"', response.text)
        self.assertEqual(len(sent), 1)
        self.assertIn("/web/login?redirect=/ocd/livrer/moi", self.url_open("/ocd/livrer").text)

    def test_new_personal_link_ends_the_open_phones(self):
        self.company.ocd_vendor_login = "link"
        self.authenticate(None, None)
        token = self.courier._ocd_get_space_token()
        self.assertIn("My tour", self.url_open(f"/ocd/livrer/{token}").text)
        self.assertIn("My tour", self.url_open("/ocd/livrer/moi").text)
        self.courier.action_ocd_reset_space_link()
        self.assertTrue(self.url_open("/ocd/livrer/moi").url.endswith("/ocd/livrer"))
        self.opener.cookies.set("session_id", None)
        self.assertTrue(self.url_open("/ocd/livrer/moi").url.endswith("/ocd/livrer"), "Not by the cookie either")
        self.assertEqual(self.url_open(f"/ocd/livrer/{token}").status_code, 404)
        # No more a courier: the new link opens nothing either
        new_token = self.courier._ocd_get_space_token()
        self.courier.ocd_is_courier = False
        self.assertEqual(self.url_open(f"/ocd/livrer/{new_token}").status_code, 404)

    def test_courier_on_the_login_page_of_the_vendors(self):
        self.company.ocd_vendor_login = "link"
        self.authenticate(None, None)
        with patch.object(self.Partner, "_ocd_send_delivery_link", autospec=True, return_value=True) as delivery, \
                patch.object(self.Partner, "_ocd_send_space_link", autospec=True, return_value=True) as space:
            response = self._ask("/ocd/connexion")
        self.assertIn("o_ocd_ok_big", response.text)
        self.assertEqual(delivery.call_count, 1)
        space.assert_not_called()

    def test_team_account_sends_nothing(self):
        self.company.ocd_vendor_login = "link"
        self.authenticate("admin", "admin")
        with patch.object(self.Partner, "_ocd_send_delivery_link", autospec=True, return_value=True) as send:
            response = self._ask()
        send.assert_not_called()
        self.assertIn("o_ocd_team_notice", response.text)
