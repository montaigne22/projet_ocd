from datetime import date, datetime, timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import OcdAmbassadorCommon


@tagged("post_install", "-at_install")
class TestOcdAmbassadors(OcdAmbassadorCommon):
    """The rules of the ambassadors (design Ambassadeurs, « Pour que ça tienne en vrai »)."""

    def test_paid_only_on_what_is_delivered_and_kept(self):
        order = self._amb_order()
        self.assertEqual((order.ocd_ambassador_rate, order.ocd_ambassador_cap), (5.0, 3000.0), "The rules of the day")
        gain = self._gain(order)
        self.assertEqual((gain.state, gain.amount), ("ordered", 600), "5 % of 12 000 F")
        self.assertEqual(gain.customer_label, "Estelle N. · Akwa")
        self.assertEqual(gain.products_label, "Robe en wax")
        self.Gain._cron_ocd_ambassadors()
        self.assertFalse(gain.bill_id, "Nothing before the delivery")
        self._deliver(self._parcel(order, self.brenda))
        self.assertEqual(gain.state, "delivered")
        self.assertEqual(gain.confirm_on, self.company._ocd_local_today() + timedelta(days=7))
        self.Gain._cron_ocd_ambassadors()
        self.assertFalse(gain.bill_id, "Confirmed only 7 days later")
        self._confirm_due(gain)
        self.assertEqual(gain.state, "confirmed")
        self.assertEqual((gain.bill_id.move_type, gain.bill_id.amount_total, gain.bill_id.partner_id),
                         ("in_invoice", 600, self.grace))
        self.assertEqual(gain.bill_id.state, "posted")
        gain._ocd_confirm()
        self.assertEqual(len(self.env["account.move"].search([("ocd_ambassador_gain_id", "=", gain.id)])), 1,
                         "Once per gain")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError), self.env.cr.savepoint():
            gain._ocd_move("earning", 600, "Twice")
        self.assertEqual(self.grace.ocd_ambassador_to_pay, 600)

    def test_never_more_than_the_commission_nor_the_cap(self):
        self.brenda.ocd_commission_rate = 3.0
        order = self._amb_order(lines=[(self.dress, 1)])
        self.assertEqual(self._gain(order).amount, 360, "3 % of 12 000 F: the commission of OCD")
        self.brenda.ocd_commission_rate = 15.0
        order = self._amb_order(customer=self.herve, lines=[(self.dress, 10)])
        self.assertEqual(self._gain(order).amount, 3000, "At most 3 000 F per parcel")
        self.company.ocd_ambassador_rate = 10.0
        self.assertEqual(order.ocd_ambassador_rate, 5.0, "The rate of the day of the order stays")

    def test_never_on_their_own_purchases(self):
        own = self.env["res.partner"].create({"name": "G. Mbia", "phone": "691 23 45 67", "country_id": self.cameroon.id})
        order = self._amb_order(customer=own)
        gain = self._gain(order)
        self.assertEqual((order.ocd_ambassador_reason, gain.state, gain.amount), ("own", "refused", 0))
        # Paid with her Mobile Money number: the same person
        self.grace.ocd_payout_momo = "+237 670000000"
        order = self._amb_order(customer=self.estelle)
        self.assertEqual(order.ocd_ambassador_reason, "own")
        self.grace.ocd_payout_momo = "+237 677401218"
        # Her own boutique: no gain on her products
        self.brenda.phone = "+237 691234567"
        order = self._amb_order(customer=self.herve)
        self.assertFalse(order.ocd_ambassador_reason)
        self.assertFalse(self._gain(order), "Only her own products: nothing to earn")

    def test_a_customer_counts_five_times_a_month(self):
        self.company.ocd_ambassador_customer_month = 2
        first, second = self._amb_order(), self._amb_order()
        third = self._amb_order()
        self.assertFalse(first.ocd_ambassador_reason or second.ocd_ambassador_reason)
        self.assertEqual(third.ocd_ambassador_reason, "limit")
        other = self._amb_order(customer=self.herve)
        self.assertFalse(other.ocd_ambassador_reason, "Another customer counts")

    def test_the_link_counts_seven_days_and_not_when_paused(self):
        late = self._amb_order(at=fields.Datetime.now() - timedelta(days=8))
        self.assertFalse(late.ocd_ambassador_id, "The link is too old: the order is the customer's own")
        self.assertFalse(self._gain(late))
        self.grace.ocd_ambassador_state = "paused"
        paused = self._amb_order()
        self.assertEqual((paused.ocd_ambassador_reason, self._gain(paused).state), ("paused", "refused"))
        self.grace.ocd_ambassador_state = "new"
        never = self._amb_order()
        self.assertFalse(never.ocd_ambassador_id, "An account never opened earns nothing")

    def test_refused_at_the_door_then_paused_by_itself(self):
        self.company.write({"ocd_ambassador_pause_min": 2, "ocd_ambassador_pause_rate": 50})
        orders = self._amb_order(), self._amb_order(customer=self.herve)
        for order in orders:
            parcel = self._parcel(order, self.brenda)
            parcel.action_ocd_ready()
            parcel.action_ocd_pick_up()
            parcel.action_ocd_return()
        gains = self._gain(orders[0]) | self._gain(orders[1])
        self.assertEqual(set(gains.mapped("state")), {"cancelled"})
        self.assertTrue(all(gains.mapped("bad_outcome")))
        self.assertEqual(self.grace.ocd_ambassador_state, "paused", "2 returns on 2 parcels")
        self.assertIn("2 parcels refused or returned on 2", self.grace.ocd_ambassador_note)
        self.assertTrue(self.grace._ocd_ambassador_payout_blocks())

    def test_a_return_before_then_after_the_confirmation(self):
        order = self._amb_order()
        gain = self._gain(order)
        self._deliver(self._parcel(order, self.brenda))
        order._ocd_request_return()
        self.assertEqual((gain.state, gain.return_asked), ("held", True))
        self._confirm_due(gain)
        self.assertEqual(gain.state, "held", "It waits for the decision of the team")
        gain.action_ocd_return_refused()
        self._confirm_due(gain)
        self.assertEqual(gain.state, "confirmed")
        # Returned later: taken from the next payout
        other = self._amb_order(customer=self.herve)
        other_gain = self._gain(other)
        self._deliver(self._parcel(other, self.brenda))
        self._confirm_due(other_gain)
        other.write({"ocd_return_requested_at": False})
        other._ocd_request_return()
        self.assertTrue(other_gain.return_asked)
        other_gain.action_ocd_return_done()
        self.assertEqual(other_gain.state, "taken_back")
        self.assertEqual((other_gain.refund_id.move_type, other_gain.refund_id.amount_total), ("in_refund", 600))
        self.assertEqual(self.grace.ocd_ambassador_to_pay, 600, "600 + 600 − 600")
        self.assertTrue(other_gain.bad_outcome)

    def test_paid_every_week_from_the_minimum(self):
        monday = date(2026, 11, 23)
        Payout = self.env["ocd.payout"]
        order = self._amb_order()
        self._deliver(self._parcel(order, self.brenda))
        self._confirm_due(self._gain(order))
        self.assertFalse(Payout._ocd_prepare(vendors=self.grace, day=monday), "600 F: below 2 000 F, it waits")
        big = self._amb_order(customer=self.herve, lines=[(self.dress, 3)])
        self._deliver(self._parcel(big, self.brenda))
        self._confirm_due(self._gain(big))
        self.assertFalse(Payout._ocd_prepare(vendors=self.grace, day=monday - timedelta(days=1)), "Only on Monday")
        payout = Payout._ocd_prepare(vendors=self.grace, day=monday)
        self.assertEqual(payout.amount, 2400, "600 + 1 800")
        self.assertEqual((payout.amount_sales, payout.amount_commission), (0, 0), "Gains are no sales of a vendor")
        payout.action_validate()
        payout.payment_reference = "OM-93107"
        with patch.object(type(Payout), "_ocd_ambassador_paid") as told:
            payout.action_register_payment()
        told.assert_called_once()
        self.grace.invalidate_recordset()
        self.assertEqual(self.grace.ocd_ambassador_to_pay, 0)
        self.assertEqual(self.grace.ocd_ambassador_earned_total, 2400)

    def test_one_person_one_mobile_money_and_the_holds(self):
        payout_blocks = self.grace._ocd_ambassador_payout_blocks
        self.assertFalse(payout_blocks())
        other = self.env["res.partner"]._ocd_ambassador_signup("Mireille Kamga", "+237 699887766", self.cameroon,
                                                              "+237 677401218")
        other._ocd_ambassador_open_account()
        self.assertEqual(other.ocd_ambassador_state, "to_check", "The Mobile Money of Grâce")
        self.assertIn("Grâce Mbia", other.ocd_ambassador_note)
        self.assertTrue(other._ocd_ambassador_payout_blocks())
        # A new number waits 48 h, the old one is told
        with patch.object(type(self.grace), "_ocd_ambassador_momo_changed") as told:
            self.assertTrue(self.grace._ocd_ambassador_set_momo("+237 655112233"))
        told.assert_called_once_with("+237 677401218")
        self.assertTrue(payout_blocks())
        self.grace.ocd_ambassador_momo_since = fields.Datetime.now() - timedelta(hours=49)
        self.assertFalse(payout_blocks())
        self.assertFalse(self.grace._ocd_ambassador_set_momo("655 11 22 33"), "The same number")
        # Above 50 000 F earned: the identity once
        self.company.ocd_ambassador_id_above = 500
        order = self._amb_order()
        self._deliver(self._parcel(order, self.brenda))
        self._confirm_due(self._gain(order))
        self.grace.invalidate_recordset()
        self.assertTrue(payout_blocks())
        items = self.env["ocd.live.verification"]._ocd_ambassador_items()
        self.assertIn(f"ambassador_identity_{self.grace.id}", [item["key"] for item in items])
        self.assertIn(f"ambassador_{other.id}", [item["key"] for item in items])
        self.env["ocd.live.verification"].ocd_approve("ambassador_identity", self.grace.id)
        self.assertTrue(self.grace.ocd_ambassador_id_checked)
        self.env["ocd.live.verification"].ocd_approve("ambassador", other.id)
        self.assertEqual(other.ocd_ambassador_state, "active")

    def test_sign_up_open_invited_closed(self):
        Partner = self.env["res.partner"]
        new = Partner._ocd_ambassador_signup("Kevin Tossou", "+228 90112233", self.env.ref("base.tg"), "+228 90112233")
        self.assertEqual(new.ocd_ambassador_state, "new", "The number is checked by the code")
        self.assertTrue(new.ocd_ambassador_code.startswith("KEVIN"))
        self.assertEqual(new.ocd_payout_frequency, "weekly")
        self.assertEqual(Partner._ocd_ambassador_signup("Kevin", "90 11 22 33", self.env.ref("base.tg"), "1"), new,
                         "One account per number")
        new._ocd_ambassador_open_account()
        self.assertEqual((new.ocd_ambassador_state, new.ocd_ambassador_since), ("active", fields.Date.context_today(new)))
        self.company.ocd_ambassador_open = "invited"
        asked = Partner._ocd_ambassador_signup("Aïcha Diallo", "+225 0700112233", self.env.ref("base.ci"), "+225 0700112233")
        self.assertEqual(asked.ocd_ambassador_state, "requested")
        self.env["ocd.live.verification"].ocd_approve("ambassador", asked.id)
        self.assertEqual(asked.ocd_ambassador_state, "active")
        self.company.ocd_ambassador_open = "closed"
        with self.assertRaises(UserError):
            Partner._ocd_ambassador_signup("Boris", "+237 655000111", self.cameroon, "+237 655000111")
        order = self._amb_order()
        self.assertEqual(order.ocd_ambassador_reason, "closed")
        self.assertEqual(Partner._ocd_ambassador_by_code("grace7"), self.grace)
        self.assertEqual(Partner._ocd_new_ambassador_code("Élodie Ngo")[:6], "ELODIE")

    def test_numbers_never_checked_are_forgotten(self):
        new = self.env["res.partner"]._ocd_ambassador_signup("Paul", "+237 655000222", self.cameroon, "+237 655000222")
        self.env.cr.execute("UPDATE res_partner SET create_date = %s WHERE id = %s",
                            [fields.Datetime.now() - timedelta(days=8), new.id])
        new.invalidate_recordset()
        self.env["res.partner"]._cron_ocd_ambassadors_forget()
        self.assertFalse(new.exists())

    def test_the_gains_of_the_day_told_once_in_the_evening(self):
        order = self._amb_order()
        self._deliver(self._parcel(order, self.brenda))
        gain = self._gain(order)
        Partner = type(self.env["res.partner"])
        evening = datetime(2026, 11, 19, 19, 30)  # 20:30 in Douala
        morning = datetime(2026, 11, 19, 7, 0)
        with patch.object(Partner, "_ocd_ambassador_tell_delivered", autospec=True, return_value=True) as tell:
            self.Gain._ocd_tell_delivered(now=morning)
            tell.assert_not_called()
            self.Gain._ocd_tell_delivered(now=evening)
            tell.assert_called_once()
            self.assertTrue(gain.told)
            self.Gain._ocd_tell_delivered(now=evening)
            tell.assert_called_once()

    def test_the_vendor_sees_what_the_ambassadors_sold(self):
        order = self._amb_order(lines=[(self.dress, 2)])
        self._amb_order(customer=self.herve)
        figures = self.env["ocd.vendor.figures"]._ocd_ambassador_figures(self.brenda, 30)
        self.assertIn("2 orders", figures["line"])
        self.assertIn("1 ambassador", figures["line"])
        self.assertEqual(figures["rows"][0]["pieces"], "3 sold")
        self.assertFalse(self.env["ocd.vendor.figures"]._ocd_ambassador_figures(self.fatou, 30))
        self.assertTrue(order)

    def test_the_products_to_share(self):
        Product = self.env["product.template"]
        products, more = Product._ocd_ambassador_products(self.grace, "best")
        self.assertIn(self.dress.product_tmpl_id, products)
        self.assertFalse(more)
        self.assertEqual(self.dress.product_tmpl_id._ocd_ambassador_earn(self.company), 600)
        self.brenda.ocd_sale_mode = "direct"
        products, _more = Product._ocd_ambassador_products(self.grace, "best")
        self.assertNotIn(self.dress.product_tmpl_id, products, "A vendor in direct contact: no sale on the site")
        self.brenda.ocd_sale_mode = "ocd"
        self.brenda.phone = "+237 691234567"
        products, _more = Product._ocd_ambassador_products(self.grace, "best")
        self.assertNotIn(self.dress.product_tmpl_id, products, "Her own boutique")

    def test_settings_and_automations(self):
        sections = [section["key"] for section in self.env["ocd.live.settings"]._ocd_sections()]
        self.assertIn("ambassadors", sections)
        codes = self.env["ocd.automation"].search([("group", "=", "ambassadors")]).mapped("code")
        self.assertEqual(set(codes), {"ambassador_order", "ambassador_gains", "ambassador_money"})
