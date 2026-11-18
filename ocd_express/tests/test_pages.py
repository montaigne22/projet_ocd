from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import OcdExpressCommon


@tagged("post_install", "-at_install")
class TestOcdExpressPages(HttpCase, OcdExpressCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cameroon = cls.env.ref("base.cm")

    def _login(self, phone="670112233"):
        self.authenticate(None, None)
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            page = self.url_open("/express/connexion", data={
                "csrf_token": self.csrf_token(), "phone": phone, "country_id": self.cameroon.id,
            }).text
            self.assertIn('name="code"', page)
            return self.url_open("/express/code", data={"csrf_token": self.csrf_token(), "code": "123456"})

    def test_the_page_and_the_request(self):
        self.authenticate(None, None)
        page = self.url_open("/express").text
        for text in ("We deliver your parcels", "Delivery in Douala", "Collecting at the door",
                     "Ask to send my parcels"):
            self.assertIn(text, page)
        self.assertIn("/express/connexion", self.url_open("/express/envois").url, "Not logged in")
        page = self.url_open("/express/demande").text
        self.assertIn('name="district_id"', page)
        page = self.url_open("/express/demande", data={
            "csrf_token": self.csrf_token(), "name": "Chez Nadine", "phone": "677000111", "country_id": self.cameroon.id,
            "district_id": self.akwa.id, "landmark": "Marche", "social": "@chez.nadine",
        }).text
        self.assertIn("Request sent", page)
        nadine = self.env["res.partner"].search([("name", "=", "Chez Nadine")])
        self.assertEqual(nadine.ocd_express_state, "requested")

    def test_create_a_parcel_and_follow_it(self):
        response = self._login()
        self.assertIn("/express/envois", response.url)
        self.assertIn("My parcels", response.text)
        page = self.url_open("/express/colis/nouveau").text
        for text in ('name="consent"', 'name="place"', "Create the parcel", "You receive"):
            self.assertIn(text, page)
        # Without the consent of the customer: refused, what was typed stays
        page = self.url_open("/express/colis/nouveau", data={
            "csrf_token": self.csrf_token(), "name": "Grace Mbia", "phone": "691234567", "country_id": self.cameroon.id,
            "place": f"d{self.makepe.id}", "content": "2 robes wax", "prepaid": "0", "amount": "15 000",
            "fee_by": "sender", "can_open": "1", "dropoff": "0",
        }).text
        self.assertIn("Tick that your customer agrees", page)
        self.assertIn("Grace Mbia", page)
        response = self.url_open("/express/colis/nouveau", data={
            "csrf_token": self.csrf_token(), "name": "Grace Mbia", "phone": "691234567", "country_id": self.cameroon.id,
            "place": f"d{self.makepe.id}", "content": "2 robes wax", "prepaid": "0", "amount": "15 000",
            "fee_by": "sender", "can_open": "1", "consent": "1", "dropoff": "0",
        })
        parcel = self.env["stock.picking"].search([("ocd_express_sender_id", "=", self.afi.id)])
        self.assertEqual(len(parcel), 1)
        self.assertIn(f"/express/colis/{parcel.id}", response.url)
        for text in ("Parcel created", parcel.name, "Print the label", "Cancel the parcel"):
            self.assertIn(text, response.text)
        self.assertIn(parcel.name, self.url_open(f"/express/colis/{parcel.id}/etiquette").text)
        self.assertIn(parcel.name, self.url_open("/express/envois").text)
        # Another sender never sees it
        other = self.env["res.partner"].create({"name": "Kossi", "phone": "+237 677999000", "ocd_express_state": "active"})
        self._login("677999000")
        self.assertEqual(self.url_open(f"/express/colis/{parcel.id}").status_code, 404)
        self.assertNotIn(parcel.name, self.url_open("/express/envois").text)
        self.assertTrue(other)
        # The page of the customer, opened from the message
        self.authenticate(None, None)
        path = parcel._ocd_tracking_path()
        self.assertEqual(self.url_open(f"/express/suivi/{parcel.id}/wrong").status_code, 404)
        page = self.url_open(f"/{path}").text
        for text in ("Parcel of Mode Afi", "To pay at the door", "I confirm", "Not there?", "not for me"):
            self.assertIn(text, page)
        self.assertNotIn(parcel.sudo().ocd_delivery_code or "no code yet", page)
        page = self.url_open(f"/{path}/confirmer", data={"csrf_token": self.csrf_token()}).text
        self.assertIn("the courier knows you are there", page)
        self.assertEqual(parcel.ocd_express_confirm, "confirmed")
        self.url_open(f"/{path}/position", data={"csrf_token": self.csrf_token(), "latitude": "4.05", "longitude": "9.7"})
        self.assertAlmostEqual(parcel.ocd_express_latitude, 4.05)
        # On the way: the code is on the page, never in the message
        self._pick(parcel)
        parcel.action_ocd_leave()
        page = self.url_open(f"/{path}").text
        self.assertIn(parcel.sudo().ocd_delivery_code, page)

    def test_my_money(self):
        parcel = self._create()
        self._deliver(parcel, method="online")
        self._login()
        page = self.url_open("/express/argent").text
        for text in ("My money", "13", "My payout number", "Change the number"):
            self.assertIn(text, page)
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            page = self.url_open("/express/argent/numero", data={
                "csrf_token": self.csrf_token(), "phone": "690000999", "country_id": self.cameroon.id}).text
            self.assertIn('name="code"', page)
            page = self.url_open("/express/argent/numero", data={"csrf_token": self.csrf_token(), "code": "000000"}).text
            self.assertIn("Wrong or expired code", page)
            page = self.url_open("/express/argent/numero", data={"csrf_token": self.csrf_token(), "code": "123456"}).text
        self.assertIn("Payout number changed", page)
        self.assertIn("690000999", self.afi.ocd_payout_momo.replace(" ", ""))
        self.assertTrue(self.afi._ocd_express_momo_held())

    def test_the_tour_of_the_courier(self):
        self.authenticate(None, None)
        self.company.ocd_vendor_login = "link"
        parcels = self._create() | self._create(name="Paul Eto'o", phone="+237 699000011")
        pickup = parcels.ocd_express_pickup_id
        pickup.date = self.company._ocd_local_today()
        base = f"/ocd/livrer/{self.courier._ocd_get_space_token()}"
        page = self.url_open(base).text
        for text in ("Pick up at Mode Afi", "2 parcels", "I took the ticked parcels", "The sender is absent"):
            self.assertIn(text, page)
        first, second = parcels.sorted("id")
        self.url_open(f"{base}/express/ramassage/{pickup.id}/fait", data={
            "csrf_token": self.csrf_token(), "taken": [str(first.id)], f"reason_{second.id}": "Mal ferme",
        })
        self.assertEqual(first.ocd_stage, "picked")
        self.assertEqual(second.ocd_express_not_taken, "Mal ferme")
        page = self.url_open(base).text
        self.assertIn("Deliver to Grace Mbia", page)
        self.assertNotIn("Mobile Money declared", page)
        # A return given back against the code of the sender
        first._ocd_return()
        page = self.url_open(base).text
        self.assertIn("Give back to Mode Afi", page)
        page = self.url_open(f"{base}/express/retour/{first.id}", data={"csrf_token": self.csrf_token(), "code": "x"}).text
        self.assertIn("Attempts left: 2", page)
        self.url_open(f"{base}/express/retour/{first.id}", data={
            "csrf_token": self.csrf_token(), "code": first._ocd_express_return_code()})
        self.assertEqual(first.ocd_express_return_state, "handed_back")
