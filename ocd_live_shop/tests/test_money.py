from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdMoney(OcdShopCommon):

    def _deliver(self, parcel):
        if parcel.ocd_stage == "to_prepare":
            parcel.action_ocd_ready()
        if parcel.ocd_delivery_mode != "vendor" and parcel.ocd_stage == "ready":
            parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)

    def test_unpaid_order_is_collected_at_the_door(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        self.assertEqual(parcel.ocd_cod_state, "to_collect")
        self.assertEqual(parcel.ocd_cod_amount, 12000)
        parcel.action_ocd_pick_up()
        parcel._ocd_collect("cash", self.courier)
        self.assertEqual(parcel.ocd_cod_state, "collected")
        self.assertEqual(parcel.ocd_cod_collected_amount, 12000)
        self.assertEqual(self.courier.ocd_cash_on_hand, 12000)
        with self.assertRaises(UserError):
            parcel._ocd_collect("cash", self.courier)

    def test_declared_mobile_money_needs_a_reference(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        with self.assertRaises(UserError):
            parcel._ocd_collect("momo_declared", self.courier)
        parcel._ocd_collect("momo_declared", self.courier, reference="MP240101.1234")
        self.assertEqual(parcel.ocd_cod_method, "momo_declared")

    def test_payment_options_chosen_by_the_team(self):
        order = self._order(self.estelle, [(self.butter, 1)])
        parcel = order.picking_ids
        self.assertEqual(parcel._ocd_allowed_cod_methods(self.fatou), [], "Fatou may not collect")
        self.fatou.ocd_vendor_collects = True
        self.assertEqual(parcel._ocd_allowed_cod_methods(self.fatou), ["cash", "online", "momo_declared"])
        self.company.ocd_cod_cash = False
        self.assertEqual(parcel._ocd_allowed_cod_methods(self.courier), ["online", "momo_declared"])
        with self.assertRaises(UserError):
            parcel._ocd_collect("cash", self.courier)

    def test_cash_of_the_courier_is_counted(self):
        first = self._order(self.estelle, [(self.dress, 1)]).picking_ids
        second = self._order(self.estelle, [(self.dress, 2)]).picking_ids
        for parcel in first | second:
            parcel._ocd_collect("cash", self.courier)
        remittance = self.env["ocd.cash.remittance"]._ocd_open_for(self.courier)
        self.assertEqual(remittance.picking_ids, first | second)
        self.assertEqual(remittance.amount_expected, 36000)
        remittance.amount_received = 35000
        remittance.action_done()
        self.assertEqual(remittance.difference, -1000)
        self.assertEqual(set((first | second).mapped("ocd_cod_state")), {"remitted"})
        self.assertEqual(self.courier.ocd_cash_on_hand, 0)

    def test_vendor_who_collects_pays_the_commission_back(self):
        self.fatou.ocd_vendor_collects = True
        order = self._order(self.estelle, [(self.butter, 2)])
        parcel = order.picking_ids
        parcel.action_ocd_ready()
        parcel._ocd_collect("cash", self.fatou)
        parcel.action_ocd_leave()
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        bill = parcel.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_invoice")
        refund = parcel.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_refund")
        self.assertAlmostEqual(bill.amount_total, 4250, msg="5,000 F minus 15 %")
        self.assertAlmostEqual(refund.amount_total, 5000, msg="Fatou kept the 5,000 F of the customer")
        payouts = self.env["ocd.payout"]._ocd_prepare(vendors=self.fatou, force=True)
        self.assertAlmostEqual(payouts.amount, -750, msg="Fatou owes the commission")

    def test_payment_on_the_phone_is_not_kept_by_the_vendor(self):
        """The customer pays on their phone at the door of a vendor who delivers: the money goes
        to OCD Live, nothing is withheld from the vendor, who gets the sales and the delivery."""
        order = self._order(self.estelle, [(self.butter, 2)])
        parcel = order.picking_ids
        parcel.action_ocd_ready()
        parcel.action_ocd_leave()
        parcel._ocd_collect("online", self.fatou)
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        self.assertFalse(parcel.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_refund"))
        payouts = self.env["ocd.payout"]._ocd_prepare(vendors=self.fatou, force=True)
        self.assertAlmostEqual(payouts.amount, 4250, msg="5,000 F minus 15 %, nothing withheld")

    def test_payout_of_the_week(self):
        for _i in range(2):
            self._deliver(self._order(self.estelle, [(self.dress, 1)]).picking_ids)
        Payout = self.env["ocd.payout"]
        self.assertFalse(Payout._ocd_prepare(vendors=self.brenda, day=date(2026, 12, 1)), "Tuesday: not the day")
        payout = Payout._ocd_prepare(vendors=self.brenda, day=date(2026, 12, 7))
        self.assertEqual(payout.vendor_id, self.brenda)
        self.assertAlmostEqual(payout.amount, 20400)
        self.assertEqual(len(payout.move_ids), 2)
        with self.assertRaises(UserError):
            payout.action_register_payment()
        payout.action_validate()
        payout.payment_reference = "CP-2041"
        payout.action_register_payment()
        self.assertEqual(payout.state, "paid")
        self.assertTrue(all(s in ("paid", "in_payment") for s in payout.move_ids.mapped("payment_state")))
        self.assertFalse(Payout._ocd_prepare(vendors=self.brenda, force=True), "Nothing left to pay")

    def test_small_payout_waits(self):
        cheap = self._product("Savon", 500, self.brenda)
        self._deliver(self._order(self.estelle, [(cheap, 1)]).picking_ids)
        self.assertFalse(self.env["ocd.payout"]._ocd_prepare(vendors=self.brenda, day=date(2026, 12, 7)))

    def test_vendor_delivery_fee_goes_to_the_vendor(self):
        fee_product = self.env["product.product"].create({"name": "Delivery Akwa", "type": "service", "list_price": 1000})
        order = self.env["sale.order"].create({
            "partner_id": self.estelle.id,
            "order_line": [
                (0, 0, {"product_id": self.butter.id, "product_uom_qty": 2, "tax_ids": [(5, 0, 0)]}),
                (0, 0, {"product_id": fee_product.id, "product_uom_qty": 1, "is_delivery": True, "tax_ids": [(5, 0, 0)]}),
            ],
        })
        order.action_confirm()
        parcel = order.picking_ids
        self.assertEqual(parcel.ocd_fee_amount, 1000)
        self.assertEqual(parcel.ocd_cod_amount, 6000)
        self._deliver(parcel)
        bill = parcel.ocd_vendor_bill_ids
        self.assertAlmostEqual(bill.amount_total, 5250, msg="4,250 F of sales + 1,000 F of delivery")

    def test_paid_on_the_phone_of_the_customer(self):
        """The customer pays on the phone with any provider of Odoo: once the provider confirms
        the payment, the parcel is paid, whoever is at the door."""
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        url = parcel._ocd_payment_url()
        self.assertIn(f"/ocd/colis/{parcel.id}/payer?access_token=", url)
        provider = self.env["payment.provider"].create({"name": "Any provider", "code": "none"})
        method = self.env["payment.method"].create({"name": "Any method", "code": "ocd_test", "provider_id": provider.id})
        transaction = self.env["payment.transaction"].create({
            "provider_id": provider.id,
            "payment_method_id": method.id,
            "reference": f"TEST-{parcel.id}",
            "amount": parcel.ocd_cod_amount,
            "currency_id": parcel.ocd_currency_id.id,
            "partner_id": self.estelle.id,
            "ocd_picking_id": parcel.id,
        })
        transaction = transaction.with_context(payment_safe_write=True)
        transaction._set_done()
        transaction._ocd_mark_parcels_paid()
        self.assertEqual(parcel.ocd_cod_state, "collected")
        self.assertEqual(parcel.ocd_cod_method, "online")
