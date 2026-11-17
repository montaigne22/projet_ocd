from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .test_delivery_rates import OcdRatesCommon


@tagged("post_install", "-at_install")
class TestOcdStorePickup(HttpCase, OcdRatesCommon):
    """Pick up in a store (chantier 20, A.1 and S.5 of the plan of « My products », design
    RetraitMagasin): free, in a store that has the whole parcel; handed over at the counter once
    paid, with the code of the customer; cancelled when not picked up in time."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                           "ocd_place_proof_required": False, "ocd_store_pickup": True, "ocd_collect_days": 3})
        cls.dress.is_storable = True
        cls.store = cls.env["ocd.vendor.place"]._ocd_vendor_create(cls.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": cls.akwa.id, "city_id": cls.douala.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
        })
        cls.store._ocd_set_hours(cls.company._ocd_place_default_intervals())
        cls.dress._ocd_change_stock(5)
        cls.company.ocd_vendor_login = "link"
        (cls.dress.product_tmpl_id | cls.butter.product_tmpl_id).write({"is_published": True})

    def _collect_order(self, lines=None, stores=None):
        order = self._cart(self.estelle, lines or [(self.dress, 1)])
        order._ocd_set_collect_places(stores if stores is not None else self.store)
        rate = self.carrier_ocd.rate_shipment(order)
        self.assertTrue(rate["success"], rate.get("error_message"))
        order.set_delivery_line(self.carrier_ocd, rate["price"])
        order.action_confirm()
        return order

    def test_free_in_a_store_that_has_the_parcel(self):
        order = self._cart(self.estelle, [(self.dress, 1), (self.butter, 1)])
        self.assertEqual(order._ocd_collect_options(self.brenda), [(self.store, True)])
        self.assertEqual(order._ocd_collect_options(self.fatou), [], "No store: no pickup")
        self.assertEqual(self.carrier_ocd.rate_shipment(order)["price"], 1800)
        order._ocd_set_collect_places(self.store)
        self.assertEqual(self.carrier_ocd.rate_shipment(order)["price"], 800, "Only the parcel of Fatou is delivered")
        self.assertFalse(order._ocd_collect_only())
        order.set_delivery_line(self.carrier_ocd, 800)
        line = order.ocd_delivery_line_ids.filtered(lambda l: l.vendor_id == self.brenda)
        self.assertEqual((line.operator, line.pickup_place_id, line.amount, line.allow_cod), ("store", self.store, 0, True))
        order.action_confirm()
        parcel = self._parcel(order, self.brenda)
        self.assertTrue(parcel.ocd_collect)
        self.assertEqual((parcel.ocd_delivery_mode, parcel.ocd_courier_id, parcel.ocd_pickup_place_id),
                         ("vendor", self.brenda, self.store))
        self.assertEqual(parcel.ocd_fee_amount, 0)
        self.assertEqual(parcel.ocd_cod_state, "to_collect")
        self.assertFalse(self._parcel(order, self.fatou).ocd_collect)
        # The setting off: no pickup
        self.company.ocd_store_pickup = False
        self.assertEqual(self._cart(self.estelle, [(self.dress, 1)])._ocd_collect_options(self.brenda), [])

    def test_ready_paid_at_the_counter_then_the_code(self):
        order = self._collect_order()
        parcel = self._parcel(order, self.brenda)
        events = []
        with patch.object(type(parcel), "_ocd_notify_customer", lambda pickings, event: events.append(event)):
            parcel.action_ocd_collect_ready()
        self.assertEqual(events, ["collect_ready"])
        self.assertEqual(parcel.ocd_stage, "ready")
        self.assertRegex(parcel.sudo().ocd_delivery_code, r"^\d{4}$")
        self.assertGreater(parcel.ocd_collect_deadline, fields.Datetime.now() + timedelta(days=2))
        code = parcel.sudo().ocd_delivery_code
        with self.assertRaisesRegex(UserError, "Collect the payment first"):
            parcel._ocd_check_code(code)
        # A vendor who does not collect at the door: Mobile Money on the phone only
        self.assertEqual(parcel._ocd_allowed_cod_methods(self.brenda), [])
        self.brenda.ocd_vendor_collects = True
        self.assertIn("cash", parcel._ocd_allowed_cod_methods(self.brenda))
        parcel._ocd_collect("cash", self.brenda)
        self.assertEqual(parcel._ocd_check_code("0000" if code != "0000" else "1111"), (False, 2))
        self.assertEqual(parcel._ocd_check_code(code), (True, 0))
        self.assertEqual((parcel.ocd_stage, parcel.state), ("delivered", "done"))

    def test_the_deadline_the_reminder_and_the_cancel(self):
        order = self._collect_order([(self.dress, 2)])
        parcel = self._parcel(order, self.brenda)
        # Ready on Monday 16 November 2026 at 10:00 in Douala: until the closing on Thursday
        start = datetime(2026, 11, 16, 9, 0)
        self.assertEqual(parcel._ocd_collect_deadline_from(start), datetime(2026, 11, 19, 18, 0),
                         "Thursday 19:00 in Douala (18:00 UTC)")
        # Closed until Thursday: the next day open
        self.store.closed_until = "2026-11-19"
        self.assertEqual(parcel._ocd_collect_deadline_from(start), datetime(2026, 11, 20, 18, 0))
        self.store.closed_until = False
        parcel.action_ocd_collect_ready()
        free_before = self.dress._ocd_free_qty()
        events = []
        with patch.object(type(parcel), "_ocd_notify_customer", lambda pickings, event: events.append(event)):
            parcel.ocd_collect_deadline = fields.Datetime.now() + timedelta(hours=10)
            self.env["stock.picking"]._cron_ocd_collect()
            self.assertEqual(events, ["collect_reminder"])
            self.env["stock.picking"]._cron_ocd_collect()
            self.assertEqual(events, ["collect_reminder"], "Reminded once")
            parcel.ocd_collect_deadline = fields.Datetime.now() - timedelta(minutes=1)
            self.env["stock.picking"]._cron_ocd_collect()
        self.assertEqual(events, ["collect_reminder", "collect_expired"])
        self.assertEqual((parcel.ocd_stage, parcel.state), ("returned", "cancel"))
        self.assertEqual(self.dress._ocd_free_qty(), free_before + 2, "The pieces are back in the store")

    def test_only_a_store_that_has_the_whole_parcel(self):
        bonapriso = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Bonapriso", "kind": "store", "district_id": self.env.ref("delivery_cameroon.district_douala_bonapriso").id,
            "city_id": self.douala.id,
        })
        order = self._cart(self.estelle, [(self.dress, 2)])
        self.assertEqual(order._ocd_collect_options(self.brenda), [(self.store, True), (bonapriso, False)])
        with self.assertRaises(UserError):
            order._ocd_set_collect_places(bonapriso)
        # The pieces sent there: it has them now, and serves the parcel
        self.env["stock.picking"]._ocd_transfer({self.dress: 2}, self.store.location_id, bonapriso.location_id)
        order = self._collect_order([(self.dress, 2)], stores=bonapriso)
        parcel = self._parcel(order, self.brenda)
        self.assertEqual((parcel.ocd_pickup_place_id, parcel.location_id), (bonapriso, bonapriso.location_id))
        self.assertEqual(parcel.state, "assigned")
        # A home is never a store to pick up in
        home = self.env["ocd.vendor.place"]._ocd_vendor_create(self.fatou, {"name": "Chez Fatou", "kind": "home"})
        self.assertEqual(self._cart(self.estelle, [(self.butter, 1)])._ocd_collect_options(self.fatou), [])
        self.assertTrue(home)

    # === THE PAGES === #

    def _fill_cart(self, products):
        self.authenticate(None, None)
        for product in products:
            self.url_open("/ocd/panier/ajouter", data={
                "csrf_token": self.csrf_token(), "product_template_id": product.product_tmpl_id.id, "quantity": 1,
            })
        return self.env["sale.order"].sudo().search(
            [("order_line.product_id", "=", products[0].id), ("state", "=", "draft")], order="id desc", limit=1
        )

    def _enable_counter_payment(self):
        cod = self.env["payment.provider"].with_context(active_test=False).search(
            [("custom_mode", "=", "cash_on_delivery"), ("company_id", "=", self.company.id)], limit=1)
        if not cod:
            return False
        cod.write({"active": True, "is_published": True})
        cod.payment_method_ids.active = True
        return cod

    def test_the_customer_picks_it_up_without_an_address(self):
        order = self._fill_cart([self.dress])
        key = str(self.brenda.id)
        page = self.url_open("/shop/checkout").text
        self.assertIn("How do you get your order?", page)
        self.assertIn("I come and get it", page)
        self.assertIn("Brenda Wax Akwa", page)
        self.assertIn("Has your whole order", page)
        # The price follows the choice: free, and no address needed
        result = self.make_jsonrpc_request("/ocd/livraison/tarif", {
            "country_id": self.cameroon.id, "city_id": False, "district_id": False, "collect": {key: self.store.id},
        })
        self.assertTrue(result["collect_only"])
        self.assertEqual(result["method"]["fee"], "Free")
        self.assertEqual(result["method"]["rows"][0]["sub"], "Picked up at Brenda Wax Akwa")
        result = self.make_jsonrpc_request("/ocd/livraison/tarif", {
            "country_id": self.cameroon.id, "city_id": self.douala.id, "district_id": self.akwa.id, "collect": {key: 0},
        })
        self.assertFalse(result["collect_only"])
        self.assertNotIn(result["home"][key]["home_fee"], ("", "Free"), "The price of « Delivered to me »")
        # Two stores have the dress: the store has to be chosen
        bonapriso = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Bonapriso", "kind": "store", "city_id": self.douala.id,
            "district_id": self.env.ref("delivery_cameroon.district_douala_bonapriso").id,
        })
        self.env["stock.picking"]._ocd_transfer({self.dress: 1}, self.store.location_id, bonapriso.location_id)
        form = {
            "csrf_token": self.csrf_token(), "name": "Estelle Ngono", "country_id": self.cameroon.id,
            "delivery_country_id": self.cameroon.id, "phone": "670 00 00 97", f"recevoir_{key}": "retrait",
        }
        page = self.url_open("/ocd/livraison", data=form).text
        self.assertIn("Choose the store where you pick it up.", page)
        response = self.url_open("/ocd/livraison", data={**form, f"magasin_{key}": self.store.id}, allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:500])
        self.assertTrue(response.headers["Location"].endswith("/shop/payment"))
        self.assertEqual(order.ocd_collect_place_ids, self.store)
        self.assertEqual((order.carrier_id, order.amount_delivery), (self.carrier_ocd, 0))
        self.assertFalse(order.partner_shipping_id.delivery_landmark, "No address asked")
        cod = self._enable_counter_payment()
        page = self.url_open("/shop/payment").text
        self.assertIn("Picked up at Brenda Wax Akwa", page)
        if cod:
            self.assertIn("Pay at the counter", page)
            self.assertIn("Your code is accepted once the money is received.", page)
        # Back to « Delivered to me »: the address is asked again
        page = self.url_open("/ocd/livraison", data={**form, f"recevoir_{key}": "livraison"}).text
        self.assertIn("Give a well-known place near your home", page)

    def test_the_tracking_page_and_the_counter(self):
        order = self._collect_order()
        parcel = self._parcel(order, self.brenda)
        url = f"/ocd/suivi/{order.id}?access_token={order._portal_ensure_token()}"
        token = self.brenda._ocd_get_space_token()
        self.authenticate(None, None)
        page = self.url_open(url).text
        self.assertIn("Picked up at the store, with your code", page)
        self.assertIn("The store writes to you on WhatsApp when it is ready.", page)
        self.assertIn("to pay at the counter", page)
        # The vendor: « It is ready », then the money and the code at the counter
        page = self.url_open(f"/ocd/livrer/{token}?vue=magasin").text
        self.assertIn("comes to pick it up", page)
        self.assertIn("Picked up at the store · 1", page)
        self.assertIn("To collect at the counter", page)
        page = self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/ready", data={"csrf_token": self.csrf_token()}).text
        self.assertIn("receives the code on WhatsApp", page)
        self.assertEqual(parcel.ocd_stage, "ready")
        self.assertIn("Not picked up before", page)
        self.assertNotIn("A problem?", page)
        page = self.url_open(url).text
        self.assertIn("Ready at the store", page)
        self.assertIn("Your pickup code", page)
        self.assertIn(parcel.sudo().ocd_delivery_code, page)
        self.assertIn("Pick it up before", page)
        self.assertIn("Itinerary", page)
        # The code before the money: refused
        code = parcel.sudo().ocd_delivery_code
        page = self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/code", data={"csrf_token": self.csrf_token(), "code": code}).text
        self.assertIn("Collect the payment first", page)
        self.brenda.ocd_vendor_collects = True
        self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/collect", data={"csrf_token": self.csrf_token(), "method": "cash"})
        self.assertEqual(parcel.ocd_cod_state, "collected")
        page = self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/code", data={"csrf_token": self.csrf_token(), "code": code}).text
        self.assertIn("in cash: the commission of OCD is withheld from your next payout", page)
        self.assertEqual(parcel.ocd_stage, "delivered")
        self.assertIn("Code checked.", self.url_open(url).text)

    def test_no_courier_for_a_parcel_picked_up(self):
        parcel = self._parcel(self._collect_order(), self.brenda)
        with self.assertRaises(UserError):
            parcel._ocd_assign_courier(self.courier)
        self.assertEqual(parcel.ocd_courier_id, self.brenda)
