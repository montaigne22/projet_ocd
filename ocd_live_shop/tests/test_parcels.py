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

    def test_control_room(self):
        booking = self.env["ocd.live.booking"].create({
            "partner_id": self.brenda.id,
            "start_datetime": self.company._ocd_slot_starts(fields.Date.today() + timedelta(days=5))[1],
            "mode": "remote",
        })
        booking._ocd_confirm()
        Regie = self.env["ocd.live.regie"]
        data = Regie.get_regie_data(booking.id)
        self.assertEqual(data["status"], "coming")
        self.assertEqual(data["vendor"], self.brenda.name)
        tiles = {tile["id"]: tile for tile in data["products"]}
        self.assertIn(self.dress.product_tmpl_id.id, tiles)
        self.assertFalse(tiles[self.dress.product_tmpl_id.id]["shown"])
        # The product touched is on screen and noted for the replay
        Regie.ocd_show_product(booking.id, self.dress.product_tmpl_id.id)
        data = Regie.get_regie_data(booking.id)
        self.assertTrue({tile["id"]: tile for tile in data["products"]}[self.dress.product_tmpl_id.id]["shown"])
        self.assertEqual([moment["name"] for moment in data["moments"]], [self.dress.product_tmpl_id.name])
        # A visit of the boutique during the live is counted
        booking._ocd_count_visit()
        self.assertEqual(Regie.get_regie_data(booking.id)["visits"], 1)
        # The replay is published with its link
        with self.assertRaises(UserError):
            Regie.ocd_publish_replay(booking.id, "tiktok.com/@brenda/video/1")
        Regie.ocd_publish_replay(booking.id, "https://www.tiktok.com/@brenda/video/1")
        self.assertTrue(booking.replay_published)

    def test_dispatch_board(self):
        order = self._order(self.estelle, [(self.dress, 1), (self.butter, 1)])
        brenda_parcel = self._parcel(order, self.brenda)
        fatou_parcel = self._parcel(order, self.fatou)
        Dispatch = self.env["ocd.live.dispatch"]
        data = Dispatch.get_dispatch_data()
        cards = {card["id"]: card for card in data["cards"]}
        self.assertEqual(cards[brenda_parcel.id]["column"], "prep")
        self.assertEqual(data["counts"]["all"], data["counts"]["ocd"] + data["counts"]["vendor"])
        self.assertIn(self.courier.id, [row["id"] for row in data["couriers"]])
        # A courier is chosen for a parcel picked up by OCD
        self.assertEqual(cards[brenda_parcel.id]["by"], "ocd")
        self.assertTrue(cards[brenda_parcel.id]["can_assign"])
        Dispatch.ocd_assign(brenda_parcel.id, self.courier.id)
        self.assertEqual(brenda_parcel.ocd_courier_id, self.courier)
        # A parcel in problem gets a new attempt
        fatou_parcel.action_ocd_ready()
        fatou_parcel._ocd_report_problem("unreachable")
        self.assertEqual(self._column(fatou_parcel), "problem")
        Dispatch.ocd_retry(fatou_parcel.id)
        self.assertEqual(fatou_parcel.ocd_stage, "ready")
        with self.assertRaises(UserError):
            Dispatch.ocd_assign(fatou_parcel.id, self.estelle.id)

    def test_orders_of_the_week(self):
        order = self._order(self.estelle, [(self.dress, 1), (self.butter, 2)])
        Orders = self.env["ocd.live.orders"]
        data = Orders.get_orders_data()
        rows = {row["id"]: row for group in data["groups"] for row in group["rows"]}
        self.assertIn(order.id, rows)
        self.assertTrue(rows[order.id]["todo"])
        self.assertEqual(rows[order.id]["ref"], order.name)
        detail = Orders.get_order_detail(order.id)
        self.assertEqual(len(detail["parcels"]), 2)
        self.assertEqual(len(detail["lines"]), 2)
        self.assertEqual(detail["history"][0]["text"], "Order received")

    def test_couriers_and_cash(self):
        Couriers = self.env["ocd.live.couriers"]
        data = Couriers.get_couriers_data()
        self.assertIn(self.courier.id, [card["id"] for card in data["cards"]])
        Couriers.ocd_set_status(self.courier.id, "rest")
        self.assertFalse(self.courier.ocd_courier_available)
        Couriers.ocd_set_status(self.courier.id, "available")
        self.assertTrue(self.courier.ocd_courier_available)
        with self.assertRaises(UserError):
            Couriers.ocd_set_status(self.courier.id, "holiday")
        # Nothing collected: nothing to count
        with self.assertRaises(UserError):
            Couriers.ocd_save_remittance(self.courier.id, 0)

    def _column(self, parcel):
        cards = {card["id"]: card for card in self.env["ocd.live.dispatch"].get_dispatch_data()["cards"]}
        return cards[parcel.id]["column"]

    def test_unapproved_product_cannot_be_published(self):
        template = self.dress.product_tmpl_id
        template.ocd_review_state = "to_check"
        with self.assertRaises(UserError):
            template.is_published = True
        template.action_ocd_approve()
        template.is_published = True
        self.assertTrue(template.is_published)
