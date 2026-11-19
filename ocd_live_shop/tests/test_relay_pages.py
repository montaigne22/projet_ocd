from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged

from .test_relay_points import OcdRelayCommon


@tagged("post_install", "-at_install")
class TestOcdRelayPages(HttpCase, OcdRelayCommon):
    """The pages of the relay points (chantier 10, design PointsRelais): the choice at the delivery
    step, the tracking page, « My relay point », the stop of the courier, « My stores », the page
    to become a relay point."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"

    def _fill_cart(self):
        self.authenticate(None, None)
        self.url_open("/ocd/panier/ajouter", data={
            "csrf_token": self.csrf_token(), "product_template_id": self.dress.product_tmpl_id.id, "quantity": 1,
        })
        return self.env["sale.order"].sudo().search(
            [("order_line.product_id", "=", self.dress.id), ("state", "=", "draft")], order="id desc", limit=1)

    def _login_relay(self):
        self.authenticate(None, None)
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            page = self.url_open("/ocd/point-relais/connexion", data={
                "csrf_token": self.csrf_token(), "phone": "677330011", "country_id": self.cameroon.id}).text
            self.assertIn('name="code"', page)
            return self.url_open("/ocd/point-relais/code", data={"csrf_token": self.csrf_token(), "code": "123456"})

    def test_the_customer_chooses_a_relay_point(self):
        order = self._fill_cart()
        page = self.url_open("/shop/checkout").text
        self.assertIn("At a relay point", page, "Shown as soon as the city has relay points")
        result = self.make_jsonrpc_request("/ocd/livraison/tarif", {
            "country_id": self.cameroon.id, "city_id": self.douala.id, "district_id": self.akwa.id,
            "relay_mode": "relais", "relay_id": self.relay.id,
        })
        self.assertTrue(result["relay"]["offered"] and result["relay_on"])
        self.assertEqual([row["name"] for row in result["relay"]["rows"]], ["Chez Mama Ngo"])
        self.assertEqual(result["method"]["name"], "At the relay point Chez Mama Ngo")
        self.assertIn("500", result["method"]["fee"])
        form = {
            "csrf_token": self.csrf_token(), "name": "Estelle Ngono", "country_id": self.cameroon.id,
            "delivery_country_id": self.cameroon.id, "phone": "670 00 00 96", "city_id": self.douala.id,
            "recevoir": "relais",
        }
        # Two relay points: the customer chooses one; no landmark asked
        other = self.relay.copy({"name": "Pressing Le Bon Coin", "state": "approved"})
        page = self.url_open("/ocd/livraison", data=form).text
        self.assertIn("Choose the relay point where you pick it up.", page)
        response = self.url_open("/ocd/livraison", data={**form, "relais": self.relay.id}, allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:300])
        self.assertEqual(order.ocd_relay_id, self.relay)
        self.assertEqual(order.amount_delivery, 500)
        page = self.url_open("/shop/payment").text
        self.assertIn("At the relay point Chez Mama Ngo", page)
        self.assertTrue(other)

    def test_the_page_of_the_customer_at_the_relay_point(self):
        parcel = self._at_relay()
        order = parcel.sale_id
        self.authenticate(None, None)
        page = self.url_open(f"/ocd/suivi/{order.id}?access_token={order._portal_ensure_token()}").text
        for text in ("Waiting for you at the relay point", "Chez Mama Ngo", parcel.sudo().ocd_delivery_code,
                     "Pick it up before", "o_ocd_tracking_qr", "Someone else may pick it up for you"):
            self.assertIn(text, page)

    def test_the_relay_point_receives_then_hands_over(self):
        order = self._relay_order()
        parcel = self._parcel(order, self.brenda)
        self._to_relay(parcel)
        response = self._login_relay()
        self.assertIn("/ocd/point-relais", response.url)
        self.assertIn("My relay point", response.text)
        self.assertIn("arrives with your parcels", response.text)
        page = self.url_open("/ocd/point-relais/recevoir").text
        self.assertIn(order.name, page)
        page = self.url_open("/ocd/point-relais/recevoir", data={"csrf_token": self.csrf_token(), "recu": [str(parcel.id)]}).text
        self.assertIn("You received 1 parcel", page)
        self.assertEqual(parcel.ocd_stage, "at_relay")
        # To pay on the phone at the counter, then the code
        page = self.url_open(f"/ocd/point-relais/remettre?colis={parcel.id}").text
        self.assertIn("To pay at the counter", page)
        code = parcel.sudo().ocd_delivery_code
        page = self.url_open("/ocd/point-relais/remettre", data={
            "csrf_token": self.csrf_token(), "colis": parcel.id, "code": code}).text
        self.assertIn("First the payment on the phone of the customer", page)
        parcel._ocd_collect("online", self.courier, reference="CP-9")
        page = self.url_open("/ocd/point-relais/remettre", data={
            "csrf_token": self.csrf_token(), "colis": parcel.id, "code": "0000" if code != "0000" else "1111"}).text
        self.assertIn("Attempts left: 2", page)
        page = self.url_open("/ocd/point-relais/remettre", data={
            "csrf_token": self.csrf_token(), "qr": parcel._ocd_relay_qr_text()}).text
        self.assertIn("Handed over to Estelle N.", page)
        self.assertEqual(parcel.ocd_stage, "delivered")
        # On holiday: no new parcel
        self.url_open("/ocd/point-relais/conge", data={"csrf_token": self.csrf_token(), "recevoir": "0"})
        self.assertFalse(self.relay.relay_open)
        self.authenticate(None, None)
        self.assertIn("/ocd/point-relais/connexion", self.url_open("/ocd/point-relais").url, "Only for the relay point")

    def test_the_courier_drops_then_takes_back(self):
        order = self._relay_order()
        parcel = self._parcel(order, self.brenda)
        parcel.action_ocd_ready()
        parcel.action_ocd_pick_up()
        self.authenticate(None, None)
        base = f"/ocd/livrer/{self.courier._ocd_get_space_token()}"
        page = self.url_open(base).text
        self.assertIn("Relay point Chez Mama Ngo", page)
        self.assertIn("I leave for the relay point", page)
        self.url_open(f"{base}/relais/{self.relay.id}/partir", data={"csrf_token": self.csrf_token()})
        self.assertEqual(parcel.ocd_stage, "on_the_way")
        with patch.object(type(parcel), "_ocd_relay_notify", lambda pickings, event: None):
            self.relay._ocd_relay_receive(parcel)
        parcel.ocd_relay_deadline = fields.Datetime.now()
        self.env["stock.picking"]._cron_ocd_relay()
        page = self.url_open(base).text
        self.assertIn("Take back: 1 parcels not picked up", page)
        self.url_open(f"{base}/relais/{self.relay.id}/repris", data={"csrf_token": self.csrf_token()})
        self.assertFalse(parcel.ocd_relay_back)

    def test_a_vendor_makes_their_store_a_relay_point(self):
        store = self.env["ocd.vendor.place"].create({
            "name": "Brenda Wax Akwa", "vendor_id": self.brenda.id, "kind": "store", "city_id": self.douala.id,
            "district_id": self.akwa.id, "state": "approved",
        })
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/magasins").text
        self.assertIn("Make it a relay point", page)
        self.url_open(f"/ocd/espace/moi/magasins/{store.id}/relais", data={"csrf_token": self.csrf_token(), "relais": "1"})
        self.assertTrue(store.relay)
        page = self.url_open("/ocd/point-relais").text
        self.assertIn("My relay point", page)
        self.assertIn("Brenda Wax Akwa", page)

    def test_a_shop_asks_then_the_team_opens_it(self):
        self.authenticate(None, None)
        page = self.url_open("/points-relais").text
        self.assertIn("Ask to become a relay point", page)
        page = self.url_open("/points-relais", data={
            "csrf_token": self.csrf_token(), "shop": "Boutique Ebène", "name": "Linda Ebène", "phone": "677330088",
            "country_id": self.cameroon.id, "district_id": self.makepe.id, "landmark": "Marché", "business": "Pagnes",
        }).text
        self.assertIn("Request sent", page)
        place = self.env["ocd.vendor.place"].search([("name", "=", "Boutique Ebène")])
        self.assertEqual((place.relay, place.state), (True, "to_check"))
        Board = self.env["ocd.live.verification"]
        column = next(column for column in Board._ocd_columns() if column["key"] == "relay")
        self.assertIn(f"relay_{place.id}", [item["key"] for item in column["items"]])
        store_column = next(column for column in Board._ocd_columns() if column["key"] == "store")
        self.assertNotIn(f"store_{place.id}", [item["key"] for item in store_column["items"]], "Not a store of a vendor")
        Board.ocd_approve("relay", place.id)
        self.assertEqual((place.state, place.relay_visited), ("approved", True))
        sections = [section["key"] for section in self.env["ocd.live.settings"].get_settings_page()["sections"]]
        self.assertIn("relay", sections)
