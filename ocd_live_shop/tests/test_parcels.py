from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdParcels(OcdShopCommon):

    def test_one_parcel_per_vendor(self):
        order = self._order(self.estelle, [(self.dress, 1), (self.butter, 2)])
        parcels = order.picking_ids
        self.assertEqual(len(parcels), 2)
        self.assertEqual(parcels.ocd_vendor_id, self.brenda | self.fatou)
        self.assertTrue(all(parcels.mapped("ocd_is_parcel")))
        self.assertEqual(set(parcels.mapped("ocd_stage")), {"to_prepare"})
        dress_parcel = self._parcel(order, self.brenda)
        butter_parcel = self._parcel(order, self.fatou)
        self.assertEqual(dress_parcel.ocd_delivery_mode, "pickup")
        self.assertEqual(dress_parcel.ocd_courier_id, self.courier, "Junior covers Akwa")
        self.assertEqual(butter_parcel.ocd_delivery_mode, "vendor")
        self.assertEqual(butter_parcel.ocd_courier_id, self.fatou)
        self.assertEqual(dress_parcel.ocd_goods_amount, 12000)
        self.assertEqual(butter_parcel.ocd_goods_amount, 5000)
        self.assertEqual(dress_parcel.move_ids.product_id, self.dress)
        self.assertEqual(order.ocd_parcel_ids, parcels)

    def test_customer_outside_the_zones_gets_an_ocd_courier(self):
        order = self._order(self.herve, [(self.butter, 2)])
        parcel = order.picking_ids
        self.assertEqual(parcel.ocd_delivery_mode, "pickup")
        self.assertEqual(parcel.ocd_courier_id, self.courier_west)

    def test_delivery_with_the_code(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        self.assertEqual(parcel.ocd_stage, "picked")
        parcel.action_ocd_leave()
        self.assertEqual(parcel.ocd_stage, "on_the_way")
        code = parcel.sudo().ocd_delivery_code
        self.assertRegex(code, r"^\d{4}$")
        wrong = "0000" if code != "0000" else "1111"
        delivered, left = parcel._ocd_check_code(wrong)
        self.assertFalse(delivered)
        self.assertEqual(left, 2)
        delivered, left = parcel._ocd_check_code(code)
        self.assertTrue(delivered)
        self.assertEqual(parcel.ocd_stage, "delivered")
        self.assertEqual(parcel.state, "done")
        bill = parcel.ocd_vendor_bill_ids
        self.assertEqual(bill.move_type, "in_invoice")
        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.partner_id, self.brenda)
        self.assertAlmostEqual(bill.amount_total, 10200, msg="12,000 F minus 15 %")

    def test_three_wrong_codes_lock_the_parcel(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_ready()
        parcel.action_ocd_leave()
        code = parcel.sudo().ocd_delivery_code
        wrong = "0000" if code != "0000" else "1111"
        for _attempt in range(3):
            parcel._ocd_check_code(wrong)
        self.assertTrue(parcel.ocd_code_locked)
        with self.assertRaises(UserError):
            parcel._ocd_check_code(code)
        team_user = new_test_user(self.env, login="dispatch", groups="ocd_live.group_ocd_live_user")
        with self.assertRaises(AccessError):
            parcel.with_user(team_user)._ocd_force_deliver("Customer has no phone")
        with self.assertRaises(UserError):
            parcel._ocd_force_deliver("  ")
        parcel._ocd_force_deliver("Customer has no phone, called by the team")
        self.assertEqual(parcel.ocd_stage, "delivered")
        self.assertEqual(parcel.ocd_forced_by_id, self.env.user)

    def test_same_code_for_a_new_attempt(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        code = parcel.sudo().ocd_delivery_code
        parcel._ocd_report_problem("unreachable")
        self.assertEqual(parcel.ocd_stage, "problem")
        self.assertEqual(parcel.ocd_failed_attempts, 1)
        parcel.action_ocd_retry()
        self.assertEqual(parcel.ocd_stage, "picked")
        parcel.action_ocd_leave()
        self.assertEqual(parcel.sudo().ocd_delivery_code, code)

    def test_two_failed_attempts_send_the_parcel_back(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_report_problem("absent")
        parcel.action_ocd_retry()
        parcel.action_ocd_leave()
        parcel._ocd_report_problem("unreachable")
        self.assertEqual(parcel.ocd_stage, "returned")
        self.assertEqual(parcel.state, "cancel")

    def test_damaged_parcel_is_not_a_failed_attempt(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_ready()
        parcel._ocd_report_problem("damaged", "The box is wet")
        self.assertEqual(parcel.ocd_failed_attempts, 0)
        self.assertEqual(parcel.ocd_stage, "problem")

    def test_steps_are_checked(self):
        order = self._order(self.estelle, [(self.butter, 1)])
        parcel = order.picking_ids
        with self.assertRaises(UserError):
            parcel.action_ocd_leave()
        with self.assertRaises(UserError, msg="Nobody picks up a parcel delivered by the vendor"):
            parcel.action_ocd_pick_up()
        parcel.action_ocd_ready()
        parcel.action_ocd_leave()
        with self.assertRaises(UserError):
            parcel.action_ocd_ready()

    def test_late_vendor_is_reminded_then_dispatch_alerted(self):
        order = self._order(self.estelle, [(self.butter, 1)])
        parcel = order.picking_ids
        created = parcel.create_date
        Picking = self.env["stock.picking"]
        with freeze_time(created + timedelta(hours=3)):
            Picking._cron_ocd_escalate()
            self.assertFalse(parcel.ocd_reminded_at)
        with freeze_time(created + timedelta(hours=4, minutes=1)):
            Picking._cron_ocd_escalate()
            self.assertTrue(parcel.ocd_reminded_at)
            self.assertFalse(parcel.ocd_escalated_at)
        with freeze_time(created + timedelta(hours=6, minutes=2)):
            Picking._cron_ocd_escalate()
            self.assertTrue(parcel.ocd_escalated_at)
            self.assertTrue(parcel.ocd_is_late)
            late_type = self.env.ref("ocd_live_shop.mail_activity_type_parcel_late")
            self.assertIn(late_type, parcel.activity_ids.activity_type_id)
        parcel.action_ocd_switch_to_ocd()
        self.assertEqual(parcel.ocd_delivery_mode, "pickup")
        self.assertEqual(parcel.ocd_courier_id, self.courier)
        self.assertNotIn(late_type, parcel.activity_ids.activity_type_id)
        self.assertEqual(self.fatou.ocd_late_count, 1)

    def test_cancelled_order_cancels_the_parcels(self):
        order = self._order(self.estelle, [(self.dress, 1), (self.butter, 1)])
        order._action_cancel()
        self.assertEqual(set(order.picking_ids.mapped("ocd_stage")), {"cancelled"})

    def test_product_shown_during_the_live(self):
        booking = self.env["ocd.live.booking"].create({
            "partner_id": self.brenda.id,
            "start_datetime": self.company._ocd_slot_starts(fields.Date.today() + timedelta(days=5))[0],
            "mode": "remote",
        })
        booking._ocd_confirm()
        self.assertIn(self.dress.product_tmpl_id, booking.vendor_product_ids)
        self.dress.product_tmpl_id.with_context(ocd_booking_id=booking.id).action_ocd_show_on_live()
        self.assertEqual(booking.current_product_tmpl_id, self.dress.product_tmpl_id)
        self.assertEqual(booking.moment_ids.product_tmpl_id, self.dress.product_tmpl_id)
        with self.assertRaises(UserError):
            booking._ocd_show_product(self.butter.product_tmpl_id)

    def test_unapproved_product_cannot_be_published(self):
        template = self.dress.product_tmpl_id
        template.ocd_review_state = "to_check"
        with self.assertRaises(UserError):
            template.is_published = True
        template.action_ocd_approve()
        template.is_published = True
        self.assertTrue(template.is_published)
