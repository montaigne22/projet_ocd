from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .common import OcdExpressCommon


class OcdExpressRelayCommon(OcdExpressCommon):
    """The relay point « Chez Mama Ngo » in Akwa (chantier 10), the rate « relay point » of
    Douala at 500 F against 1 000 F at the door."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cm = cls.env.ref("base.cm")
        cls.company.write({
            "ocd_relay_enabled": True, "ocd_relay_fee": 150, "ocd_relay_days": 7, "ocd_relay_reminder_days": 2,
            "ocd_relay_capacity": 25,
        })
        cls.env["ocd.delivery.rate"].create({
            "operator": "relay", "origin_city_id": cls.douala.id, "country_id": cm.id,
            "city_ids": [Command.set(cls.douala.ids)], "price": 500,
        })
        cls.mama = cls.env["res.partner"].create({
            "name": "Mama Ngo", "phone": "+237 677330011", "ocd_is_relay": True, "ocd_payout_frequency": "monthly",
            "country_id": cm.id,
        })
        cls.relay = cls.env["ocd.vendor.place"].create({
            "name": "Chez Mama Ngo", "vendor_id": cls.mama.id, "kind": "store", "city_id": cls.douala.id,
            "district_id": cls.akwa.id, "landmark": "Rue Joss", "relay": True, "relay_capacity": 25,
            "state": "approved",
        })
        cls.relay._ocd_set_hours(cls.company._ocd_place_default_intervals())

    def _receive(self, parcel):
        with patch.object(type(parcel), "_ocd_relay_notify", lambda pickings, event: None):
            self.relay._ocd_relay_receive(parcel)


@tagged("post_install", "-at_install")
class TestOcdExpressRelay(OcdExpressRelayCommon):

    def test_a_parcel_sent_to_a_relay_point(self):
        parcel = self._create(relay=self.relay, district=False, landmark="")
        self.assertEqual(parcel.ocd_relay_id, self.relay)
        self.assertEqual(parcel.ocd_express_fee, 500, "The price of the relay points, not the 1 000 F at the door")
        self.assertEqual(parcel.partner_id.district_id, self.akwa)
        self._pick(parcel)
        parcel.action_ocd_leave()
        self.assertFalse(parcel._ocd_express_relay_points(), "The courier left: no other relay point")
        self._receive(parcel)
        self.assertEqual(parcel.ocd_stage, "at_relay")
        # Paid on the phone at the counter, then the code
        parcel._ocd_collect("online", parcel.ocd_courier_id, reference="CP-12")
        delivered, _left = self.relay._ocd_relay_hand_over(parcel, parcel.sudo().ocd_delivery_code)
        self.assertTrue(delivered)
        self.assertEqual(parcel.ocd_stage, "delivered")
        earning = parcel.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_relay_kind == "earning")
        self.assertEqual((earning.partner_id, earning.amount_total), (self.mama, 150))
        self.assertEqual(self._moves(parcel, "fees").amount_total, 725, "500 F of relay point, 1.5 % of 15 000 F")

    def test_no_relay_price_from_another_city(self):
        self.afi.write({"city_id": self.yaounde.id, "district_id": False})
        with self.assertRaises(UserError):
            self._create(relay=self.relay, district=False)
        self.relay.relay_open = False
        self.afi.write({"city_id": self.douala.id, "district_id": self.akwa.id})
        with self.assertRaises(UserError):
            self._create(relay=self.relay, district=False)

    def test_the_customer_chooses_a_relay_point(self):
        parcel = self._create(fee_by="customer")
        self.assertEqual((parcel.ocd_express_fee, parcel.ocd_relay_id), (1000, self.relay.browse()))
        self.assertEqual(parcel._ocd_express_relay_points(), self.relay)
        parcel._ocd_express_to_relay(self.relay)
        self.assertEqual((parcel.ocd_express_fee, parcel.ocd_relay_id), (500, self.relay))
        self.assertEqual(parcel.ocd_cod_state, "to_collect")
        self.relay.relay_open = False
        other = self._create()
        with self.assertRaises(UserError):
            other._ocd_express_to_relay(self.relay)

    def test_not_picked_up_goes_back_to_the_sender(self):
        parcel = self._create(relay=self.relay, district=False)
        self._pick(parcel)
        parcel.action_ocd_leave()
        self._receive(parcel)
        parcel.ocd_relay_deadline = fields.Datetime.now()
        self.env["stock.picking"]._cron_ocd_relay()
        self.assertEqual((parcel.ocd_stage, parcel.ocd_express_return_state), ("returned", "to_return"))
        self.assertTrue(parcel.ocd_relay_back, "The courier takes it back at the relay point first")
        parcel._ocd_relay_take_back(parcel.ocd_courier_id)
        self.assertFalse(parcel.ocd_relay_back)

    def test_lost_at_the_relay_point_paid_back_to_the_sender(self):
        parcel = self._create(relay=self.relay, district=False, prepaid=True, value=80000)
        self._pick(parcel)
        parcel.action_ocd_leave()
        self._receive(parcel)
        parcel.action_ocd_relay_lost()
        self.assertTrue(parcel.ocd_express_lost)
        self.assertEqual(parcel.ocd_stage, "cancelled")
        lost = self._moves(parcel, "lost")
        self.assertEqual(lost.amount_total, 50000, "At most the amount of the settings")
        loss = parcel.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_relay_kind == "loss")
        self.assertEqual((loss.partner_id, loss.amount_total), (self.mama, 50000))


@tagged("post_install", "-at_install")
class TestOcdExpressRelayPages(HttpCase, OcdExpressRelayCommon):

    def test_the_customer_picks_it_up_at_a_relay_point(self):
        parcel = self._create(fee_by="customer")
        path = parcel._ocd_tracking_path()
        self.authenticate(None, None)
        page = self.url_open(f"/{path}").text
        for text in ("Not there? I pick it up at a relay point", "Chez Mama Ngo", "Delivery at a relay point"):
            self.assertIn(text, page)
        page = self.url_open(f"/{path}/relais", data={"csrf_token": self.csrf_token(), "relay_id": self.relay.id}).text
        self.assertIn("your parcel waits for you at the relay point Chez Mama Ngo", page)
        self.assertEqual(parcel.ocd_relay_id, self.relay)
        self._pick(parcel)
        parcel.action_ocd_leave()
        page = self.url_open(f"/{path}").text
        self.assertIn("On its way to the relay point Chez Mama Ngo", page)
        self.assertNotIn(parcel.sudo().ocd_delivery_code, page, "The code comes with the relay point")
        self._receive(parcel)
        page = self.url_open(f"/{path}").text
        for text in ("Waits for you at the relay point", "Pick it up before", parcel.sudo().ocd_delivery_code,
                     "o_ocd_ex_relay_qr", "Itinerary"):
            self.assertIn(text, page)

    def test_the_sender_sends_to_a_relay_point(self):
        self.authenticate(None, None)
        Partner = type(self.env["res.partner"])
        with patch.object(Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            self.url_open("/express/connexion", data={
                "csrf_token": self.csrf_token(), "phone": "670112233", "country_id": self.env.ref("base.cm").id})
            self.url_open("/express/code", data={"csrf_token": self.csrf_token(), "code": "123456"})
        page = self.url_open("/express/colis/nouveau").text
        self.assertIn("At a relay point (cheaper)", page)
        self.assertIn(f'value="r{self.relay.id}"', page)
        self.url_open("/express/colis/nouveau", data={
            "csrf_token": self.csrf_token(), "name": "Grace Mbia", "phone": "691234567",
            "country_id": self.env.ref("base.cm").id, "place": f"r{self.relay.id}", "content": "2 robes wax",
            "prepaid": "0", "amount": "15 000", "fee_by": "sender", "can_open": "1", "consent": "1", "dropoff": "0",
        })
        parcel = self.env["stock.picking"].search([("ocd_express_sender_id", "=", self.afi.id)])
        self.assertEqual((parcel.ocd_relay_id, parcel.ocd_express_fee), (self.relay, 500))
        self._pick(parcel)
        parcel.action_ocd_leave()
        self._receive(parcel)
        page = self.url_open("/express/envois").text
        self.assertIn("At the relay point", page)
