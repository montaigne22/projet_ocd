from datetime import date, timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_delivery_rates import OcdRatesCommon


class OcdRelayCommon(OcdRatesCommon):
    """A relay point in Akwa held by a partner of OCD Live (Mama Ngo), the rate « relay point »
    of Douala at 500 F; Junior, the courier of Akwa, takes the parcels there."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            "ocd_relay_enabled": True, "ocd_relay_fee": 150, "ocd_relay_days": 7, "ocd_relay_reminder_days": 2,
            "ocd_relay_capacity": 25, "ocd_relay_vendor_stores": True, "ocd_relay_pause_after": 2,
            "ocd_studio_tz": "Africa/Douala",
        })
        cls.relay_rate = cls.Rate.create({
            "operator": "relay", "origin_city_id": cls.douala.id, "country_id": cls.cameroon.id,
            "city_ids": [Command.set(cls.douala.ids)], "price": 500,
        })
        cls.mama = cls.env["res.partner"].create({
            "name": "Mama Ngo", "phone": "+237 677330011", "ocd_is_relay": True, "ocd_payout_frequency": "monthly",
            "ocd_payout_momo": "+237 677330011", "country_id": cls.cameroon.id,
        })
        cls.relay = cls.env["ocd.vendor.place"].create({
            "name": "Chez Mama Ngo", "vendor_id": cls.mama.id, "kind": "store", "city_id": cls.douala.id,
            "district_id": cls.akwa.id, "landmark": "Rue Joss, face à la boulangerie", "relay": True,
            "relay_capacity": 25, "state": "approved",
        })
        cls.relay._ocd_set_hours(cls.company._ocd_place_default_intervals())
        (cls.dress.product_tmpl_id | cls.butter.product_tmpl_id).write({"is_published": True})

    def _relay_order(self, lines=None, customer=None):
        order = self._cart(customer or self.estelle, lines or [(self.dress, 1)])
        order._ocd_set_relay(self.relay)
        rate = self.carrier_ocd.rate_shipment(order)
        self.assertTrue(rate["success"], rate.get("error_message"))
        order.set_delivery_line(self.carrier_ocd, rate["price"])
        order.action_confirm()
        return order

    def _to_relay(self, parcel):
        """Prepared by Brenda, picked up and taken to the relay point by Junior."""
        parcel.action_ocd_ready()
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()

    def _at_relay(self, order=None):
        order = order or self._relay_order()
        parcel = self._parcel(order, self.brenda)
        self._to_relay(parcel)
        with patch.object(type(parcel), "_ocd_relay_notify", lambda pickings, event: None):
            self.relay._ocd_relay_receive(parcel)
        return parcel


@tagged("post_install", "-at_install")
class TestOcdRelayPoints(OcdRelayCommon):

    def test_the_price_of_a_relay_point_and_who_can_go(self):
        order = self._cart(self.estelle, [(self.dress, 1)])
        self.assertEqual(order._ocd_relay_points(self.douala, self.akwa), self.relay)
        quotes = order._ocd_delivery_quotes(relay=self.relay)
        self.assertEqual([(q["operator"], q["price"], q["error"]) for q in quotes], [("relay", 500, False)])
        self.assertEqual(self._quote(self.brenda, self.estelle)["price"], 1000, "At the door: the rate of the courier")
        # Fatou delivers herself: an order with her parcel goes to no relay point
        both = self._cart(self.estelle, [(self.dress, 1), (self.butter, 1)])
        self.assertFalse(both._ocd_relay_points(self.douala, self.akwa))
        with self.assertRaises(UserError):
            both._ocd_set_relay(self.relay)
        # Another city: none
        self.assertFalse(order._ocd_relay_points(self.yaounde))

    def test_to_the_relay_point_then_handed_over_with_the_code(self):
        order = self._relay_order()
        self.assertEqual(order._ocd_delivery_fee(), 500)
        line = order.ocd_delivery_line_ids
        self.assertEqual((line.operator, line.relay_place_id, line.amount), ("relay", self.relay, 500))
        self.assertFalse(order._needs_customer_address(), "Name and WhatsApp only")
        parcel = self._parcel(order, self.brenda)
        self.assertEqual((parcel.ocd_relay_id, parcel.ocd_delivery_mode, parcel.ocd_courier_id),
                         (self.relay, "pickup", self.courier))
        self.assertEqual(parcel.ocd_fee_amount, 500)
        incoming = []
        with patch.object(type(self.relay), "_ocd_relay_notify_incoming",
                          lambda place, parcels: incoming.append((place, place._ocd_relay_incoming_count()))):
            self._to_relay(parcel)
        self.assertEqual(incoming, [(self.relay, 1)], "The relay point is told once")
        self.relay.invalidate_recordset(["relay_coming_count"])
        self.assertEqual(self.relay.relay_coming_count, 1)
        events = []
        with patch.object(type(parcel), "_ocd_relay_notify", lambda pickings, event: events.append(event)):
            self.relay._ocd_relay_receive(parcel)
        self.assertEqual(events, ["relay_arrived"])
        self.assertEqual(parcel.ocd_stage, "at_relay")
        self.assertGreater(parcel.ocd_relay_deadline, fields.Datetime.now() + timedelta(days=6))
        self.relay.invalidate_recordset(["relay_held_count", "relay_coming_count"])
        self.assertEqual((self.relay.relay_held_count, self.relay.relay_coming_count), (1, 0))
        code = parcel.sudo().ocd_delivery_code
        self.assertRegex(code, r"^\d{4}$")
        # To pay at the counter: on the phone of the customer only, then the code
        self.assertEqual(parcel._ocd_allowed_cod_methods(self.mama), ["online"])
        with self.assertRaisesRegex(UserError, "Collect the payment first"):
            self.relay._ocd_relay_hand_over(parcel, code)
        parcel._ocd_collect("online", self.courier, reference="CP-1")
        self.assertEqual(self.relay._ocd_relay_hand_over(parcel, "0000" if code != "0000" else "1111"), (False, 2))
        found, read = self.relay._ocd_relay_parcel_by_qr(parcel._ocd_relay_qr_text())
        self.assertEqual((found, read), (parcel, code), "The QR of the customer gives the parcel and its code")
        self.assertEqual(self.relay._ocd_relay_hand_over(parcel, code), (True, 0))
        self.assertEqual((parcel.ocd_stage, parcel.state), ("delivered", "done"))
        earning = parcel.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_relay_kind == "earning")
        self.assertEqual((earning.partner_id, earning.amount_total), (self.mama, 150))
        self.assertTrue(parcel.ocd_vendor_bill_ids.filtered(lambda m: m.partner_id == self.brenda),
                        "Brenda is paid as for a parcel delivered at the door")
        self.relay.invalidate_recordset(["relay_month_amount", "relay_given_count"])
        self.assertEqual((self.relay.relay_month_amount, self.relay.relay_given_count), (150, 1))

    def test_a_parcel_damaged_stays_with_the_courier(self):
        order = self._relay_order()
        parcel = self._parcel(order, self.brenda)
        self._to_relay(parcel)
        received = self.relay._ocd_relay_receive(parcel, refused={parcel: "Carton ouvert"})
        self.assertFalse(received)
        self.assertEqual((parcel.ocd_stage, parcel.ocd_problem_reason), ("problem", "damaged"))
        other = self._relay_order(customer=self.herve)
        with self.assertRaises(UserError):
            self.relay._ocd_relay_receive(self._parcel(other, self.brenda))

    def test_a_reminder_then_back_and_taken_back(self):
        parcel = self._at_relay()
        events = []
        Picking = type(parcel)
        with patch.object(Picking, "_ocd_relay_notify", lambda pickings, event: events.append(event)), \
                patch.object(Picking, "_ocd_notify_customer", lambda pickings, event: events.append(event)):
            parcel.ocd_relay_deadline = fields.Datetime.now() + timedelta(days=1)
            self.env["stock.picking"]._cron_ocd_relay()
            self.assertEqual(events, ["relay_reminder"])
            self.env["stock.picking"]._cron_ocd_relay()
            self.assertEqual(events, ["relay_reminder"], "Once")
            parcel.ocd_relay_deadline = fields.Datetime.now() - timedelta(minutes=1)
            self.env["stock.picking"]._cron_ocd_relay()
        self.assertEqual(events, ["relay_reminder", "relay_expired"])
        self.assertEqual((parcel.ocd_stage, parcel.ocd_relay_back), ("returned", True))
        self.assertEqual(self.relay._ocd_relay_parcels("back"), parcel, "It waits for the courier")
        self.relay.invalidate_recordset(["relay_held_count"])
        self.assertEqual(self.relay.relay_held_count, 1, "It still takes a place")
        parcel._ocd_relay_take_back(self.courier)
        self.assertFalse(parcel.ocd_relay_back)
        self.assertTrue(parcel.ocd_relay_taken_back_at)
        self.assertFalse(parcel.ocd_vendor_bill_ids.filtered("ocd_relay_kind"), "Nothing earned for a parcel taken back")
        with self.assertRaises(UserError):
            parcel._ocd_relay_take_back(self.courier)

    def test_full_on_holiday_closed_or_paused_is_not_offered(self):
        self.assertTrue(self.relay._ocd_relay_available())
        self.relay.relay_capacity = 1
        self._at_relay()
        self.relay.invalidate_recordset(["relay_held_count"])
        self.assertFalse(self.relay._ocd_relay_available(), "Full")
        self.relay.relay_capacity = 25
        self.relay._ocd_relay_set_open(False)
        self.assertFalse(self.relay._ocd_relay_available(), "On holiday")
        self.relay._ocd_relay_set_open(True)
        self.relay.closed_until = self.company._ocd_local_today()
        self.assertFalse(self.relay._ocd_relay_available(), "Closed today")
        self.relay.closed_until = False
        with self.assertRaises(UserError):
            self._cart(self.estelle, [(self.dress, 1)])._ocd_set_relay(self.relay.copy({"state": "to_check"}))
        # The store of a vendor as a relay point (A.6): only when the team allows it
        store = self.relay.copy({"vendor_id": self.brenda.id, "name": "Brenda Wax Akwa", "state": "approved"})
        self.assertTrue(store._ocd_relay_available())
        self.company.ocd_relay_vendor_stores = False
        self.assertFalse(store._ocd_relay_available())

    def test_lost_paid_back_then_paused_after_two(self):
        first = self._at_relay()
        second = self._at_relay(self._relay_order(customer=self.herve))
        first.action_ocd_relay_lost()
        loss = first.ocd_vendor_bill_ids.filtered(lambda m: m.ocd_relay_kind == "loss")
        self.assertEqual((loss.partner_id, loss.move_type, loss.amount_total), (self.mama, "in_refund", 12500))
        self.assertEqual(first.ocd_stage, "cancelled")
        self.assertTrue(first.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref("ocd_live_shop.mail_activity_type_refund")))
        self.assertTrue(self.relay.relay_open, "One loss: still open")
        second.action_ocd_relay_lost()
        self.assertFalse(self.relay.relay_open, "Paused after two losses")
        self.assertTrue(self.relay.relay_pause_note)
        with self.assertRaises(UserError):
            self.relay._ocd_relay_set_open(True)
        self.relay.action_ocd_relay_resume()
        self.assertTrue(self.relay.relay_open)

    def test_paid_every_month_never_what_it_owes(self):
        Payout = self.env["ocd.payout"]
        parcel = self._at_relay()
        parcel._ocd_collect("online", self.courier, reference="CP-2")
        self.relay._ocd_relay_hand_over(parcel, parcel.sudo().ocd_delivery_code)
        self.company.ocd_payout_min_amount = 100
        self.assertFalse(Payout._ocd_prepare(vendors=self.mama, day=date(2026, 12, 2)), "Not the 1st of the month")
        payout = Payout._ocd_prepare(vendors=self.mama, day=date(2026, 12, 1))
        self.assertEqual(payout.amount, 150)
        lost = self._at_relay(self._relay_order(customer=self.herve))
        lost.action_ocd_relay_lost()
        self.assertFalse(Payout._ocd_prepare(vendors=self.mama, day=date(2027, 1, 1)), "It owes OCD: it waits")

    def test_a_shop_asks_to_become_a_relay_point(self):
        place = self.env["ocd.vendor.place"]._ocd_relay_request(
            "Boutique Ebène", "Linda Ebène", "+237 677330099", self.cameroon, self.makepe, "Marché Makepe", "Pagnes")
        self.assertEqual((place.relay, place.state, place.kind, place.district_id), (True, "to_check", "store", self.makepe))
        holder = place.vendor_id
        self.assertTrue(holder.ocd_is_relay)
        self.assertEqual(holder.ocd_payout_frequency, "monthly")
        self.assertEqual(self.env["res.partner"]._ocd_find_relay_by_phone("677330099"), holder)
        self.assertFalse(place._ocd_relay_available(), "Not before the visit of the team")
        with self.assertRaises(UserError):
            self.env["ocd.vendor.place"]._ocd_relay_request("", "", "+237 677330098", self.cameroon, self.makepe, "", "")
