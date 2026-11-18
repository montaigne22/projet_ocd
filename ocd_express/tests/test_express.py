from datetime import date, datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import BinaryBytes

from .common import OcdExpressCommon


@tagged("post_install", "-at_install")
class TestOcdExpressParcel(OcdExpressCommon):

    def test_parcel_created_with_its_price_and_its_pickup(self):
        parcel = self._create()
        self.assertTrue(parcel.name.startswith("EX-"))
        self.assertTrue(parcel.ocd_express and parcel.ocd_is_parcel)
        self.assertEqual(parcel.ocd_stage, "ready")
        self.assertEqual(parcel.ocd_express_fee, 1000)
        self.assertEqual(parcel.ocd_cod_state, "to_collect")
        self.assertEqual(parcel.ocd_cod_amount, 15000, "The sender pays the delivery: the customer pays the goods")
        self.assertEqual(parcel.partner_id.district_id, self.makepe)
        self.assertTrue(parcel.partner_id.ocd_express_recipient)
        self.assertEqual(parcel.ocd_express_pickup_id.sender_id, self.afi)
        self.assertEqual(parcel.ocd_courier_id, self.courier, "The courier of the district of the sender")
        self.assertTrue(parcel.ocd_express_deliver_on)
        self.assertEqual(parcel.move_ids.product_id, self.env.ref("ocd_express.product_express_parcel").product_variant_id)
        second = self._create(name="Paul Eto'o", phone="+237 699000011")
        self.assertEqual(second.ocd_express_pickup_id, parcel.ocd_express_pickup_id, "One passage for the parcels of a sender")

    def test_customer_pays_the_delivery(self):
        parcel = self._create(fee_by="customer")
        self.assertEqual(parcel.ocd_cod_amount, 16000)
        prepaid = self._create(prepaid=True, value=8000, fee_by="customer")
        self.assertEqual(prepaid.ocd_cod_amount, 1000, "Already paid: the customer pays only the delivery")
        self.assertEqual(prepaid.ocd_express_value, 8000)
        free = self._create(prepaid=True, value=8000)
        self.assertEqual(free.ocd_cod_state, "none")

    def test_what_the_sender_types_is_checked(self):
        with self.assertRaises(UserError):
            self._create(consent=False)
        with self.assertRaises(UserError):
            self._create(phone=self.afi.phone)
        with self.assertRaises(UserError):
            self._create(amount=0)
        with self.assertRaises(UserError):
            self._create(content="")
        with self.assertRaises(UserError):
            self._create(district=self.env["res.city.district"], city=self.douala)
        self.afi.ocd_express_state = "suspended"
        with self.assertRaises(UserError):
            self._create()

    def test_another_city_by_travel_agency_paid_in_advance(self):
        with self.assertRaises(UserError):
            self._create(district=self.env["res.city.district"], city=self.yaounde)
        parcel = self._create(district=self.env["res.city.district"], city=self.yaounde, prepaid=True, value=9000)
        self.assertTrue(parcel.ocd_by_agency)
        self.assertEqual(parcel.ocd_express_fee, 2500)
        self.assertEqual(parcel.ocd_cod_state, "none")

    def test_above_the_limit_the_team_checks(self):
        parcel = self._create(amount=60000)
        self.assertEqual(parcel.ocd_express_check, "to_check")
        self.assertEqual(parcel.ocd_stage, "to_prepare")
        self.assertFalse(parcel.ocd_courier_id)
        with self.assertRaises(UserError):
            parcel.action_ocd_leave()
        parcel.action_ocd_express_approve()
        self.assertEqual(parcel.ocd_stage, "ready")
        self.assertEqual(parcel.ocd_courier_id, self.courier)
        refused = self._create(amount=70000, name="Yves Mballa", phone="+237 699000012")
        refused.action_ocd_express_refuse()
        self.assertEqual(refused.ocd_stage, "cancelled")

    def test_identity_checked_above_an_amount_a_day(self):
        self.company.ocd_express_id_daily = 40000
        self._create(amount=30000)
        parcel = self._create(amount=20000, name="Paul Eto'o", phone="+237 699000011")
        self.assertEqual(parcel.ocd_express_check, "to_check")
        self.afi.ocd_express_id_checked = True
        parcel = self._create(amount=20000, name="Linda Ngo", phone="+237 699000013")
        self.assertEqual(parcel.ocd_express_check, "ok")

    def test_waves_of_the_day(self):
        company = self.company
        tuesday = date(2026, 11, 24)
        # Douala is UTC+1: 9:00 local is 8:00 UTC
        self.assertEqual(company._ocd_express_slot(datetime(2026, 11, 24, 8, 0)),
                         (tuesday, "morning", tuesday, "afternoon"))
        self.assertEqual(company._ocd_express_slot(datetime(2026, 11, 24, 12, 0)),
                         (tuesday, "afternoon", tuesday + timedelta(days=1), "morning"))
        self.assertEqual(company._ocd_express_slot(datetime(2026, 11, 24, 16, 0)),
                         (tuesday + timedelta(days=1), "morning", tuesday + timedelta(days=1), "afternoon"))
        saturday_evening = datetime(2026, 11, 28, 17, 0)
        monday = date(2026, 11, 30)
        self.assertEqual(company._ocd_express_slot(saturday_evening), (monday, "morning", monday, "afternoon"),
                         "No pick-up on Sunday")

    def test_a_full_day_moves_to_the_next_wave(self):
        self.company.write({"ocd_express_per_courier": 1, "ocd_express_shop_share": 0})
        couriers = self.env["res.partner"].search_count([("ocd_is_courier", "=", True)])
        first = [self._create(name=f"Client {index}", phone=f"+237 6990001{index:02d}") for index in range(couriers)]
        last = self._create(name="Client last", phone="+237 699000199")
        self.assertTrue(all(parcel.ocd_express_deliver_on == first[0].ocd_express_deliver_on for parcel in first))
        self.assertGreater((last.ocd_express_deliver_on, last.ocd_express_deliver_part),
                           (first[0].ocd_express_deliver_on, first[0].ocd_express_deliver_part))

    def test_sender_changes_or_cancels_before_the_pickup(self):
        parcel = self._create()
        parcel._ocd_express_update(self._data(amount=12000, district=self.akwa))
        self.assertEqual(parcel.ocd_cod_amount, 12000)
        self.assertEqual(parcel.partner_id.district_id, self.akwa)
        parcel._ocd_express_cancel_by_sender()
        self.assertEqual(parcel.ocd_stage, "cancelled")
        picked = self._create(name="Paul Eto'o", phone="+237 699000011")
        self._pick(picked)
        with self.assertRaises(UserError):
            picked._ocd_express_cancel_by_sender()
        with self.assertRaises(UserError):
            picked._ocd_express_update(self._data())

    def test_dropped_at_the_ocd_point(self):
        parcel = self._create(dropoff=True)
        self.assertFalse(parcel.ocd_express_pickup_id)
        self.assertFalse(parcel.ocd_courier_id)
        parcel.action_ocd_express_received()
        self.assertEqual(parcel.ocd_stage, "picked")
        self.assertEqual(parcel.ocd_courier_id, self.courier, "The courier of the district of the customer")


@tagged("post_install", "-at_install")
class TestOcdExpressPickup(OcdExpressCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_express_pickup_free_from = 3

    def test_free_from_three_parcels(self):
        parcels = self._create() | self._create(name="Paul", phone="+237 699000011") \
            | self._create(name="Linda", phone="+237 699000012")
        pickup = parcels.ocd_express_pickup_id
        self.assertEqual(len(pickup), 1)
        pickup._ocd_done(parcels, photo=BinaryBytes(b"photo"))
        self.assertEqual(pickup.state, "done")
        self.assertEqual(pickup.fee, 0)
        self.assertEqual(set(parcels.mapped("ocd_stage")), {"picked"})
        self.assertTrue(self.afi.ocd_express_place_checked)

    def test_small_pickup_is_paid_and_a_parcel_not_taken_waits(self):
        first = self._create()
        second = self._create(name="Paul", phone="+237 699000011")
        pickup = first.ocd_express_pickup_id
        pickup._ocd_done(first, not_taken={second: "Badly closed"})
        self.assertEqual(pickup.fee, 500)
        self.assertEqual(self._moves(first, "pickup").amount_total, 500)
        self.assertEqual(second.ocd_express_not_taken, "Badly closed")
        self.assertEqual(second.ocd_stage, "ready")
        self.assertNotEqual(second.ocd_express_pickup_id, pickup, "The next passage")
        self.assertEqual(second.ocd_express_pickup_id.state, "planned")

    def test_second_missed_pickup_in_a_row_is_paid(self):
        parcel = self._create()
        first = parcel.ocd_express_pickup_id
        first._ocd_missed("Closed")
        self.assertEqual(first.fee, 0)
        second = parcel.ocd_express_pickup_id
        self.assertNotEqual(second, first)
        second._ocd_missed("Closed again")
        self.assertEqual(second.fee, 500)
        self.assertEqual(self._moves(parcel, "pickup").amount_total, 500)

    def test_dispatch_gives_the_passage_to_another_courier(self):
        parcel = self._create()
        parcel.ocd_express_pickup_id.courier_id = self.courier_west
        self.assertEqual(parcel.ocd_courier_id, self.courier_west)


@tagged("post_install", "-at_install")
class TestOcdExpressMoney(OcdExpressCommon):

    def test_cash_counts_once_at_the_cash_desk(self):
        parcel = self._create()
        self._deliver(parcel)
        self.assertEqual(parcel.ocd_stage, "delivered")
        self.assertFalse(self._moves(parcel, "collected") | self._moves(parcel, "fees"), "The cash is still on the courier")
        self.assertEqual(parcel.ocd_express_money_state, "waiting")
        self._remit(self.courier)
        collected = self._moves(parcel, "collected")
        fees = self._moves(parcel, "fees")
        self.assertEqual(collected.amount_total, 15000)
        self.assertEqual(fees.amount_total, 1225, "1 000 F of delivery, 1.5 % of 15 000 F")
        self.assertEqual(self.afi.ocd_express_balance, 13775)
        parcel._ocd_express_settle()
        self.assertEqual(len(self._moves(parcel, "collected") | self._moves(parcel, "fees")), 2, "Once per parcel")

    def test_paid_on_the_phone_counts_at_the_delivery(self):
        parcel = self._create(fee_by="customer")
        self._pick(parcel)
        parcel.action_ocd_leave()
        parcel._ocd_collect("online", parcel.ocd_courier_id, reference="CP-1")
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        self.assertEqual(self._moves(parcel, "collected").amount_total, 15000, "The delivery is the money of OCD")
        self.assertEqual(self._moves(parcel, "fees").amount_total, 225, "Only the collecting")

    def test_collecting_at_least(self):
        parcel = self._create(amount=5000)
        self._deliver(parcel, method="online")
        fees = self._moves(parcel, "fees")
        self.assertEqual(fees.amount_total, 1150, "1 000 F of delivery, 150 F at least to collect")

    def test_already_paid_parcel_leaves_a_debt(self):
        parcel = self._create(prepaid=True, value=8000)
        self._deliver(parcel)
        self.assertFalse(self._moves(parcel, "collected"))
        self.assertEqual(self._moves(parcel, "fees").amount_total, 1000)
        self.assertEqual(self.afi.ocd_express_balance, -1000)

    def test_debt_above_the_limit_blocks_until_paid(self):
        self.company.ocd_express_debt_max = 1500
        for index in range(2):
            self._deliver(self._create(prepaid=True, value=1000, name=f"C{index}", phone=f"+237 69900002{index}"))
        self.assertEqual(self.afi._ocd_express_debt(), 2000)
        with self.assertRaises(UserError):
            self._create(prepaid=True, value=1000)
        self.assertTrue(self._create(fee_by="customer"), "The customer pays the delivery")
        self.afi.action_ocd_express_debt_paid(2000, "OM-1234")
        self.assertEqual(self.afi.ocd_express_balance, 0)
        self.assertTrue(self._create(prepaid=True, value=1000, name="C9", phone="+237 699000029"))

    def test_methods_at_the_door(self):
        parcel = self._create()
        self.assertNotIn("momo_declared", parcel._ocd_allowed_cod_methods(self.courier))
        big = self._create(amount=120000, name="Kossi", phone="+237 699000031")
        big.action_ocd_express_approve()
        self.assertEqual(big._ocd_allowed_cod_methods(self.courier), ["online"])
        self._pick(big)
        big.action_ocd_leave()
        with self.assertRaises(UserError):
            big._ocd_collect("cash", self.courier)

    def test_cash_on_a_courier_is_capped(self):
        self.company.ocd_express_cash_max = 20000
        first = self._create()
        self._pick(first)
        first.action_ocd_leave()
        first._ocd_collect("cash", self.courier)
        second = self._create(name="Paul", phone="+237 699000011", amount=9000)
        self._pick(second)
        second.action_ocd_leave()
        with self.assertRaises(UserError):
            second._ocd_collect("cash", self.courier)
        second._ocd_collect("online", self.courier, reference="CP-2")
        self.assertEqual(second.ocd_cod_state, "collected")

    def test_lost_by_ocd_paid_back_at_most(self):
        parcel = self._create(amount=60000)
        parcel.action_ocd_express_approve()
        self._pick(parcel)
        parcel.action_ocd_express_lost()
        self.assertEqual(self._moves(parcel, "lost").amount_total, 50000)
        self.assertEqual(parcel.ocd_stage, "cancelled")
        self.assertEqual(self.afi.ocd_express_balance, 50000)


@tagged("post_install", "-at_install")
class TestOcdExpressAfterDelivery(OcdExpressCommon):

    def test_returned_against_the_return_code(self):
        parcel = self._create()
        self._pick(parcel)
        parcel.action_ocd_leave()
        parcel._ocd_report_problem("absent")
        self.assertEqual(parcel.ocd_stage, "problem")
        parcel._ocd_express_move_to(self.company._ocd_local_today() + timedelta(days=1), "morning")
        self.assertEqual(parcel.ocd_stage, "picked", "Second passage")
        self.assertEqual(parcel.ocd_express_confirm, "moved")
        parcel.action_ocd_leave()
        parcel._ocd_report_problem("absent")
        self.assertEqual(parcel.ocd_stage, "returned")
        self.assertEqual(parcel.ocd_express_return_state, "to_return")
        code = parcel._ocd_express_return_code()
        self.assertEqual(len(code), 6)
        self.assertEqual(parcel._ocd_express_hand_back("000000" if code != "000000" else "111111", self.courier),
                         (False, 2))
        with self.assertRaises(UserError):
            parcel._ocd_express_hand_back(code, self.courier_west)
        self.assertEqual(parcel._ocd_express_hand_back(code, self.courier), (True, 0))
        self.assertEqual(parcel.ocd_express_return_state, "handed_back")
        self.assertEqual(self._moves(parcel, "return").amount_total, 500)
        self.assertFalse(self._moves(parcel, "fees"), "No delivery for a return")

    def test_return_code_blocked_after_three_wrong_codes(self):
        parcel = self._create()
        self._pick(parcel)
        parcel._ocd_return()
        wrong = "999999" if parcel._ocd_express_return_code() != "999999" else "888888"
        for left in (2, 1, 0):
            self.assertEqual(parcel._ocd_express_hand_back(wrong, self.courier), (False, left))
        with self.assertRaises(UserError):
            parcel._ocd_express_hand_back(parcel._ocd_express_return_code(), self.courier)

    def test_cash_given_back_when_refused_after_paying(self):
        parcel = self._create()
        self._pick(parcel)
        parcel.action_ocd_leave()
        parcel._ocd_collect("cash", self.courier)
        parcel._ocd_report_problem("refused")
        self.assertEqual(parcel.ocd_failed_attempts, 1)
        parcel._ocd_return()
        self.assertEqual(parcel.ocd_cod_state, "to_collect")
        self.assertEqual(self.courier.ocd_cash_on_hand, 0)

    def test_not_for_me(self):
        parcel = self._create()
        parcel._ocd_express_not_for_me()
        self.assertEqual(parcel.ocd_stage, "cancelled", "Not picked up yet: cancelled")
        self.assertTrue(parcel.partner_id.ocd_express_optout)
        other = self._create(phone="+237 691234567", name="Grace")
        self._pick(other)
        other._ocd_express_not_for_me()
        self.assertEqual(other.ocd_express_return_state, "to_return")

    def test_problem_reported_holds_the_money(self):
        parcel = self._create()
        self._deliver(parcel, method="online")
        self.assertTrue(parcel._ocd_express_claim_open())
        with self.assertRaises(UserError):
            parcel._ocd_express_report_claim("")
        parcel._ocd_express_report_claim("Le colis etait vide")
        self.assertEqual(parcel.ocd_express_claim_state, "open")
        Payout = self.env["ocd.payout"]
        tuesday = date(2026, 11, 24)
        self.assertFalse(Payout._ocd_prepare(vendors=self.afi, day=tuesday), "The money of the parcel waits")
        parcel.action_ocd_express_claim_customer()
        self.assertEqual(parcel.ocd_express_claim_state, "customer_right")
        self.assertEqual(self._moves(parcel, "claim").amount_total, 15000)
        self.assertEqual(self.afi.ocd_express_balance, 15000 - 1225 - 15000)

    def test_problem_reported_within_the_hours(self):
        parcel = self._create()
        self._deliver(parcel, method="online")
        parcel.ocd_delivered_at = fields.Datetime.now() - timedelta(hours=49)
        self.assertFalse(parcel._ocd_express_claim_open())
        with self.assertRaises(UserError):
            parcel._ocd_express_report_claim("Abime")

    def test_position_of_the_customer(self):
        parcel = self._create()
        parcel._ocd_express_set_position(4.0711, 9.7333)
        self.assertAlmostEqual(parcel.ocd_express_latitude, 4.0711)
        with self.assertRaises(UserError):
            parcel._ocd_express_set_position(0, 0)

    def test_customers_erased_after_the_months(self):
        parcel = self._create()
        self._deliver(parcel, method="online")
        old = fields.Datetime.now() - timedelta(days=200)
        self.env.flush_all()
        self.env.cr.execute("UPDATE stock_picking SET create_date = %s, write_date = %s WHERE id = %s",
                            (old, old, parcel.id))
        parcel.invalidate_recordset()
        self.env["stock.picking"]._cron_ocd_express_erase()
        self.assertTrue(parcel.ocd_express_anonymized)
        self.assertFalse(parcel.partner_id.phone)
        self.assertEqual(self._moves(parcel, "collected").amount_total, 15000, "The amounts stay")


@tagged("post_install", "-at_install")
class TestOcdExpressPayout(OcdExpressCommon):

    def test_payout_every_working_day(self):
        Payout = self.env["ocd.payout"]
        self.assertFalse(Payout._ocd_is_due(self.afi, date(2026, 11, 29)), "Sunday")
        self.assertTrue(Payout._ocd_is_due(self.afi, date(2026, 11, 28)), "Saturday")
        parcel = self._create()
        self._deliver(parcel)
        self._remit(self.courier)
        debt = self._create(prepaid=True, value=5000, name="Paul", phone="+237 699000011")
        self._deliver(debt)
        payout = Payout._ocd_prepare(vendors=self.afi, day=date(2026, 11, 24))
        self.assertEqual(payout.amount, 13775 - 1000)
        payout.action_validate()
        payout.payment_reference = "OM-88213"
        payout.action_register_payment()
        self.assertEqual(payout.state, "paid")
        self.assertEqual(self.afi.ocd_express_balance, 0)

    def test_what_a_sender_owes_waits(self):
        parcel = self._create(prepaid=True, value=5000)
        self._deliver(parcel)
        self.assertFalse(self.env["ocd.payout"]._ocd_prepare(vendors=self.afi, day=date(2026, 11, 24)))

    def test_new_payout_number_waits(self):
        parcel = self._create()
        self._deliver(parcel, method="online")
        self.afi.ocd_payout_momo = "+237 690000999"
        self.assertTrue(self.afi.ocd_express_momo_changed_at)
        Payout = self.env["ocd.payout"]
        self.assertFalse(Payout._ocd_prepare(vendors=self.afi, day=date(2026, 11, 24)))
        self.afi.ocd_express_momo_changed_at = fields.Datetime.now() - timedelta(hours=49)
        self.assertTrue(Payout._ocd_prepare(vendors=self.afi, day=date(2026, 11, 24)))


@tagged("post_install", "-at_install")
class TestOcdExpressSender(OcdExpressCommon):

    def test_request_invited_then_approved(self):
        Partner = self.env["res.partner"]
        sender = Partner._ocd_express_request("Chez Nadine", "+237 677000111", self.env.ref("base.cm"),
                                              self.akwa, "Marche Sandaga", "@chez.nadine")
        self.assertEqual(sender.ocd_express_state, "requested")
        self.assertFalse(Partner._ocd_find_express_sender_by_phone("677000111"))
        sender.action_ocd_express_approve()
        self.assertEqual(sender.ocd_express_state, "active")
        self.assertEqual(Partner._ocd_find_express_sender_by_phone("677000111"), sender)

    def test_a_request_never_changes_a_contact(self):
        self.brenda.write({"phone": "+237 677000333", "district_id": self.makepe.id, "delivery_landmark": "Rond-point"})
        sender = self.env["res.partner"]._ocd_express_request(
            "Someone", "+237 677000333", self.env.ref("base.cm"), self.akwa, "Ailleurs", "")
        self.assertEqual(sender, self.brenda)
        self.assertEqual(self.brenda.district_id, self.makepe)
        self.assertEqual(self.brenda.delivery_landmark, "Rond-point")
        self.assertEqual(self.brenda.name, "Brenda Wax")

    def test_debt_paid_on_the_phone(self):
        self._deliver(self._create(prepaid=True, value=1000))
        self.assertEqual(self.afi._ocd_express_debt(), 1000)
        provider = self.env["payment.provider"].search([("code", "=", "custom")], limit=1)
        if not provider.payment_method_ids:
            self.skipTest("No payment provider checked by the team in this database.")
        transaction = self.env["payment.transaction"].create({
            "provider_id": provider.id, "payment_method_id": provider.payment_method_ids[:1].id, "amount": 1000,
            "currency_id": self.company.currency_id.id, "partner_id": self.afi.id, "reference": "EXD-TEST",
            "ocd_express_debt_partner_id": self.afi.id,
        }).with_context(payment_safe_write=True)
        transaction._set_done()
        transaction._post_process()
        transaction._post_process()
        self.assertEqual(self.afi.ocd_express_balance, 0)
        self.assertEqual(len(self.env["account.move"].search(
            [("partner_id", "=", self.afi.id), ("ocd_express_kind", "=", "debt_paid")])), 1, "Once")

    def test_request_open_to_all_and_vendor_keeps_their_account(self):
        self.company.ocd_express_open_to = "all"
        Partner = self.env["res.partner"]
        sender = Partner._ocd_express_request(self.brenda.name, "+237 677000222", self.env.ref("base.cm"),
                                              self.akwa, "", "", vendor=self.brenda)
        self.assertEqual(sender, self.brenda)
        self.assertEqual(sender.ocd_express_state, "active")

    def test_limit_after_twenty_parcels(self):
        self.assertEqual(self.afi.ocd_express_max_cod, 50000)
        self.company.ocd_express_cap_after = 1
        self._deliver(self._create(), method="online")
        self.afi.invalidate_recordset(["ocd_express_max_cod"])
        self.assertEqual(self.afi.ocd_express_max_cod, 200000)

    def test_too_many_returns_warn_then_suspend(self):
        self.company.ocd_express_first_day_max = 0
        parcels = self.env["stock.picking"]
        for index in range(11):
            parcels |= self._create(name=f"C{index}", phone=f"+237 69900004{index:02d}")
        self._pick(parcels)
        for parcel in parcels[:6]:
            self._deliver(parcel, method="online")
        with patch.object(type(self.afi), "_ocd_express_notify_returns_warning") as warn:
            for parcel in parcels[6:10]:
                parcel._ocd_return()
            warn.assert_called_once()
        self.assertTrue(self.afi.ocd_express_warned_at)
        self.assertEqual(self.afi.ocd_express_state, "active")
        self.afi.ocd_express_warned_at = fields.Datetime.now() - timedelta(days=8)
        parcels[10]._ocd_return()
        self.assertEqual(self.afi.ocd_express_state, "suspended")
