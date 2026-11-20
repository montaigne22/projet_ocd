import json
import re
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytz
import requests
from freezegun import freeze_time

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live_demo import scenario
from odoo.addons.ocd_live_demo.hooks import (
    PARAM_EXPRESS,
    PARAM_OPEN_DATE,
    PARAM_REPLAY_URL,
    PARAM_SHOP,
    OcdLiveDemo,
    uninstall_hook,
)


class DemoCommon:

    def _demo_partners(self):
        return self.env["res.partner"].browse(
            self.env["ir.model.data"].search([("module", "=", "ocd_live_demo"), ("model", "=", "res.partner")]).mapped("res_id")
        )

    def _at(self, day, hour, minute=0):
        """A moment of `day` at `hour` in the time of the studio, as stored (naive UTC)."""
        company = self.env.company
        return company._ocd_to_utc(company._ocd_tz().localize(datetime.combine(day, time(hour, minute))))

    def _vendors_of(self, window):
        return self.env["res.partner"].browse(
            [self.env.ref(f"ocd_live_demo.{row[0]}").id for row in scenario.DIRECTORY if window in row[3]]
        )

    def _end_open_links(self):
        self.env["ocd.directory.listing"].search([("partner_id", "in", self._demo_partners().ids)]).action_end()

    def _douala(self, day, hour, minute):
        """A moment of `day` at `hour` in Douala, as stored (naive UTC)."""
        return pytz.timezone("Africa/Douala").localize(datetime.combine(day, time(hour, minute))).astimezone(pytz.utc).replace(tzinfo=None)

    def _parcels(self):
        return self.env["stock.picking"].search([
            ("partner_id", "in", self._demo_partners().ids), ("ocd_is_parcel", "=", True),
        ])

    def _express(self):
        if "ocd.express.pickup" not in self.env:
            self.skipTest("OCD Express is not installed.")
        return self.env.ref("ocd_live_demo.sender_nadege")

    def _express_parcels(self):
        return self.env["stock.picking"].search([("ocd_express_sender_id", "=", self._express().id)])

    def _free_stock(self):
        """Free stock of the dress shown on the website, by (colour, size)."""
        website = self.env["website"].search([], limit=1)
        return {
            tuple(sorted(v.product_template_attribute_value_ids.mapped("name"))): website._get_product_available_qty(v)
            for v in self.env.ref("ocd_live_demo.product_wax_dress").product_variant_ids
        }


@tagged("post_install", "-at_install")
class TestOcdLiveDemo(DemoCommon, TransactionCase):
    """The demo shows every part of OCD Live on the days around today, and its uninstallation
    removes it all."""

    def test_demo_shows_every_part(self):
        partners = self._demo_partners()
        vendors = partners.filtered("ocd_is_vendor")
        self.assertGreaterEqual(len(vendors), 15)
        approved = vendors.filtered(lambda vendor: vendor.ocd_vendor_state == "approved")
        self.assertEqual(set(approved.mapped("country_id.code")), {"TG", "CM", "CI", "SN", "BJ", "GH", "NG", "FR"})
        self.assertTrue(all(vendor._ocd_feed_image() for vendor in approved), "A picture for every card of the feed")
        bookings = self.env["ocd.live.booking"].search([("partner_id", "in", partners.ids)])
        self.assertLessEqual({"confirmed", "draft", "done"}, set(bookings.mapped("state")))
        replays = bookings.filtered("replay_published")
        self.assertTrue(replays)
        brenda = self.env.ref("ocd_live_demo.vendor_brenda")
        for replay in replays.filtered(lambda booking: booking.partner_id == brenda):
            self.assertEqual(len(replay.moment_ids), 3, "The dress, the shirt and the pagne shown on screen")
        credits = self.env["ocd.live.credit"].search([("partner_id", "in", partners.ids)])
        self.assertTrue(credits.filtered(lambda c: c.remaining == 1), "One live of the Duo left to place")
        self.assertEqual(len(partners.filtered("ocd_pass_active")), len(scenario.DIRECTORY))
        parcels = self.env["stock.picking"].search([("partner_id", "in", partners.ids), ("ocd_is_parcel", "=", True)])
        self.assertGreaterEqual(len(parcels), 3, "One parcel per vendor and per order")
        self.assertTrue(self.env.ref("ocd_live.payment_provider_momo_team").active)
        company = self.env.company
        self.assertLessEqual(company.ocd_booking_open_date or company._ocd_local_today(), company._ocd_local_today(),
                             "OCD Live is shown in service: the lives can be booked")

    def test_demo_fills_the_shop_and_the_deliveries(self):
        templates = self.env["product.template"].browse(
            self.env["ir.model.data"].search([("module", "=", "ocd_live_demo"), ("model", "=", "product.template")]).mapped("res_id")
        )
        self.assertTrue(all(templates.mapped("image_128")), "Every demo product has a picture")
        dress = self.env.ref("ocd_live_demo.product_wax_dress")
        self.assertEqual(len(dress.product_variant_ids), 8, "Two colours, four sizes")
        self.assertEqual(self._free_stock()[("Bleu", "M")], 3, "Only 3 left")
        self.assertLessEqual(self._free_stock()[("Bleu", "L")], 0, "A sold-out size")
        self.assertTrue(self.env.ref("ocd_live_demo.product_black_soap")._is_sold_out())
        partners = self._demo_partners()
        couriers = partners.filtered("ocd_is_courier")
        self.assertGreaterEqual(len(couriers), 3)
        self.assertTrue(couriers.filtered(lambda c: not c.ocd_courier_available), "One courier off duty")
        parcels = self._parcels()
        self.assertGreaterEqual(len(parcels), 6 * (scenario.SHOP_PAST_DAYS + 1) - 6, "The orders of the last week")
        self.assertTrue(parcels.sale_id.ocd_delivery_line_ids, "Orders priced with one price per parcel")
        self.assertEqual(
            set(parcels.filtered(lambda p: p.sale_id.date_order < fields.Datetime.now() - timedelta(days=2)).mapped("ocd_stage")),
            {"delivered"}, "The parcels of the days before are delivered",
        )
        remittances = self.env["ocd.cash.remittance"].search([("courier_id", "in", couriers.ids)])
        self.assertTrue(remittances and set(remittances.mapped("state")) == {"done"}, "Cash handed over every evening")
        self.assertTrue(self.env["account.journal"].search_count(
            [("type", "=", "purchase"), ("company_id", "=", self.env.company.id)]),
            "The accounting is there, also when the demo is installed with the modules in one go")
        before = parcels.filtered(lambda p: p.ocd_stage == "delivered"
                                  and p.ocd_delivered_at < fields.Datetime.now() - timedelta(days=2))
        self.assertTrue(before)
        self.assertFalse(before.filtered(lambda p: not p.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_invoice")),
                         "Each parcel delivered the days before has the bill of its vendor")
        payouts = self.env["ocd.payout"].search([("vendor_id", "in", partners.ids)])
        self.assertGreaterEqual(len(payouts.filtered(lambda p: p.state == "paid")), scenario.SHOP_PAST_DAYS - 1,
                                "The payouts of the days before, paid every day")
        if "whatsapp.account" in self.env:
            channels = self.env["discuss.channel"].search(
                [("channel_type", "=", "whatsapp"), ("whatsapp_partner_id", "in", partners.ids)]
            )
            self.assertGreaterEqual(len(channels), 6, "Conversations for the WhatsApp screen")
            self.assertFalse(channels.whatsapp_account_id.active, "Nothing goes to Meta from the demo")
        cod = self.env.ref("delivery.payment_provider_cod")
        self.assertTrue(cod.active and cod.is_published, "An order of the shop can be paid in cash at the door")

    def test_a_day_of_the_shop(self):
        """The next day, hour by hour in Douala: new orders, parcels at every step, a late parcel
        and a customer absent the day before, cash with the couriers, then handed over."""
        demo = OcdLiveDemo(self.env)
        tomorrow = demo.shop_today(fields.Datetime.now()) + timedelta(days=1)
        couriers = self._demo_partners().filtered("ocd_is_courier")
        with freeze_time(self._douala(tomorrow, 11, 30)):
            demo.keep_shop(fields.Datetime.now())
            stages = set(self._parcels().filtered(lambda p: p.ocd_stage != "delivered" or p.ocd_delivered_at
                                                  >= self._douala(tomorrow, 0, 0)).mapped("ocd_stage"))
            for stage in ("to_prepare", "ready", "on_the_way", "delivered", "problem"):
                self.assertIn(stage, stages, stage)
            late = self._parcels().filtered("ocd_is_late")
            self.assertTrue(late, "The parcel Brenda has not prepared since yesterday")
            self.assertTrue(late.ocd_reminded_at and late.ocd_escalated_at < late.ocd_reminded_at + timedelta(hours=3))
            self.assertEqual(self._free_stock()[("Bleu", "M")], 3, "The stock stays at its level")
        with freeze_time(self._douala(tomorrow, 13, 45)):
            demo.keep_shop(fields.Datetime.now())
            if "whatsapp.account" in self.env:
                waiting = self.env["discuss.channel"].search([
                    ("channel_type", "=", "whatsapp"), ("whatsapp_waiting_since", "!=", False),
                    ("whatsapp_partner_id", "in", self._demo_partners().ids),
                ])
                self.assertEqual(waiting.whatsapp_partner_id, self.env.ref("ocd_live_demo.customer_ruth"),
                                 "Ruth asks if she can pay by Mobile Money")
                self.assertGreater(waiting.whatsapp_waiting_since, fields.Datetime.now() - timedelta(hours=1))
        with freeze_time(self._douala(tomorrow, 14, 0)):
            demo.keep_shop(fields.Datetime.now())
            couriers.invalidate_recordset(["ocd_cash_on_hand"])
            self.assertTrue(couriers.filtered(lambda c: c.ocd_cash_on_hand > 0), "Cash to hand over this evening")
        with freeze_time(self._douala(tomorrow, 20, 0)):
            demo.keep_shop(fields.Datetime.now())
            couriers.invalidate_recordset(["ocd_cash_on_hand"])
            self.assertFalse(couriers.filtered(lambda c: c.ocd_cash_on_hand > 0), "Handed over at 19:30")
            of_yesterday = self._parcels().filtered(lambda p: p.sale_id.date_order < self._douala(tomorrow, 0, 0))
            self.assertEqual(set(of_yesterday.mapped("ocd_stage")), {"delivered"},
                             "The late parcel and the parcel of the absent customer delivered in the afternoon")
            bills = self.env["account.move"].search([
                ("partner_id", "in", self._demo_partners().ids), ("move_type", "=", "in_invoice"),
            ])
            if bills:
                # With the accounting: a payout of the day to check, the ones before paid
                payouts = self.env["ocd.payout"].search([("vendor_id", "in", self._demo_partners().ids)])
                self.assertFalse(payouts.filtered(lambda p: p.date < tomorrow and p.state != "paid"),
                                 "The payouts of the days before are paid")
                self.assertTrue(payouts.filtered(lambda p: p.date == tomorrow and p.state == "draft"))

    def test_stores_team_and_life_of_the_shop(self):
        """The stores of the vendors and the pieces of each one, the team of Brenda, the relay
        point, and the life of the shop: followers, reviews, alerts, a report, the promo of the
        week, a change to check, a product refused, the figures of the last months."""
        demo = OcdLiveDemo(self.env)
        brenda, fatou = self.env.ref("ocd_live_demo.vendor_brenda"), self.env.ref("ocd_live_demo.vendor_fatou")
        akwa, bonapriso = demo.demo_place("akwa"), demo.demo_place("bonapriso")
        self.assertEqual((akwa.state, bonapriso.state), ("approved", "approved"))
        self.assertEqual(brenda._ocd_departure_place(), akwa, "Her parcels leave from Akwa")
        self.assertTrue(bonapriso._ocd_location() and bonapriso.ocd_stock_count, "Pieces in each store")
        self.assertEqual(self._free_stock()[("Bleu", "M")], 3, "The website counts the pieces of every store")
        self.assertEqual(demo.demo_place("fatou_home").kind, "home")
        self.assertEqual(demo.demo_place("kossi_store").state, "approved")
        self.assertEqual(demo.demo_place("ama_store").state, "to_check", "A store waits for the team")
        member = self.env["ocd.vendor.member"].search([("vendor_id", "=", brenda.id)])
        self.assertEqual((member.partner_id, member.place_id), (self.env.ref("ocd_live_demo.member_aicha"), bonapriso))
        self.assertEqual(member.state, "active", "She opens her store space every morning")
        relay = demo.demo_place(scenario.RELAY_PLACE[0])
        self.assertTrue(relay.relay and relay.state == "approved")
        asked = self.env["ocd.vendor.place"].search([("vendor_id", "=", self.env.ref("ocd_live_demo.relay_ngo").id)])
        self.assertEqual((asked.relay, asked.state), (True, "to_check"), "A shop asks to become a relay point")
        parcels = self._parcels()
        self.assertTrue(parcels.filtered("ocd_collect"), "Orders picked up at the store of Akwa")
        self.assertTrue(parcels.filtered(lambda p: p.ocd_relay_id == relay), "Orders to the relay point")
        self.assertTrue(parcels.filtered(lambda p: p.ocd_relay_id and p.ocd_stage == "delivered"),
                        "Picked up at the relay point")
        followers = self.env["ocd.vendor.follower"].search([("vendor_id", "=", brenda.id)])
        self.assertEqual(len(followers), len(scenario.FOLLOWERS["vendor_brenda"]))
        reviews = self.env["ocd.vendor.review"].search([("vendor_id", "=", brenda.id)])
        self.assertGreaterEqual(len(reviews), 3, "Her note shows from 3 reviews")
        late = reviews.filtered(lambda review: "retard" in (review.comment or ""))
        self.assertTrue(all(review.picking_id.ocd_reminded_at for review in late), "Only a late parcel is said late")
        self.assertFalse(reviews.filtered(lambda review: "robe" in (review.comment or "").lower()
                                          and "Robe en wax" not in review.product_ids.mapped("name")),
                         "The word of the buyer fits the product")
        self.assertTrue(self.env["ocd.vendor.review"].search([("vendor_id", "=", fatou.id)]))
        self.assertEqual(len(self.env["ocd.stock.alert"].search([("product_id", "=", demo.variant("product_wax_dress", "Bleu", "L").id)])), 3)
        self.assertTrue(all(self.env.ref(f"ocd_live_demo.{xmlid}").ocd_verified for xmlid in scenario.VERIFIED))
        self.assertTrue(self.env["ocd.report"].search([("product_id", "=", self.env.ref("ocd_live_demo.product_kente").id),
                                                       ("state", "=", "new")]))
        promo = self.env["ocd.product.promo"].search([
            ("product_tmpl_id", "=", self.env.ref("ocd_live_demo.product_wax_pagne").id),
            ("date_start", "<=", fields.Datetime.now()), ("date_end", ">", fields.Datetime.now()),
        ])
        self.assertTrue(promo, "The promo of the week")
        self.assertEqual(self.env.ref("ocd_live_demo.product_powerbank").ocd_change_state, "to_check")
        self.assertEqual(self.env.ref("ocd_live_demo.product_honey_soap").ocd_review_state, "refused")
        days = self.env["ocd.vendor.count"].search_count([("vendor_id", "=", brenda.id), ("kind", "=", "visit")])
        self.assertGreaterEqual(days, scenario.FIGURES_DAYS - 2, "Her visits day by day")
        self.assertTrue(self.env["ocd.vendor.place.tap"].search_count([("place_id", "=", akwa.id)]))
        # Her lives sell: the customers who came during a live ordered, the boutique was visited,
        # a viewer followed her
        now = fields.Datetime.now()
        lived = self.env["ocd.live.booking"].search([
            ("partner_id", "=", brenda.id), ("state", "in", ("confirmed", "done")),
            ("start_datetime", ">=", now - timedelta(days=scenario.SHOP_PAST_DAYS - 1)), ("end_datetime", "<", now),
        ])
        self.assertTrue(lived, "Brenda goes live three times a week")
        for live in lived:
            sold = self.env["sale.order.line"].search([("ocd_live_id", "=", live.id), ("state", "=", "sale")])
            self.assertEqual(len(sold.order_id), len(scenario.LIVE_SALES["vendor_brenda"]), "Orders of the live")
            self.assertGreaterEqual(live.ocd_visit_count, scenario.LIVE_VISITS[0])
            self.assertTrue(self.env["ocd.vendor.follower"].search_count([
                ("vendor_id", "=", brenda.id), ("followed_at", ">=", live.start_datetime),
                ("followed_at", "<=", live.end_datetime),
            ]), "A viewer followed her during the live")
        next_live = self.env["ocd.live.booking"].search([
            ("partner_id", "=", brenda.id), ("state", "=", "confirmed"), ("start_datetime", ">", fields.Datetime.now()),
        ], order="start_datetime", limit=1)
        if next_live and next_live.start_datetime < fields.Datetime.now() + timedelta(days=3):
            self.assertTrue(next_live._ocd_prepared_products(), "Her next live is prepared for the control room")
        # Nothing twice when the demo runs again
        demo.keep_current()
        self.assertEqual(len(self.env["ocd.vendor.place"].search([("vendor_id", "=", brenda.id)])), 2)
        self.assertEqual(len(self.env["ocd.vendor.follower"].search([("vendor_id", "=", brenda.id)])), len(followers))

    def test_a_day_with_the_store_and_the_relay_point(self):
        """The next day: the order of Hervé ready at the store of Akwa, picked up the morning after;
        the parcel of Carine counted by the relay point in the evening; a piece held to try."""
        demo = OcdLiveDemo(self.env)
        tomorrow = demo.shop_today(fields.Datetime.now()) + timedelta(days=1)
        with freeze_time(self._douala(tomorrow, 18, 30)):
            demo.keep_shop(fields.Datetime.now())
            of_the_day = self._parcels().filtered(lambda p: p.sale_id.date_order >= self._douala(tomorrow, 0, 0))
            collect = of_the_day.filtered("ocd_collect")
            self.assertEqual(collect.ocd_stage, "ready", "Waiting at the counter with its code")
            relay = of_the_day.filtered("ocd_relay_id")
            self.assertEqual(relay.ocd_stage, "at_relay", "Counted by the relay point")
            self.assertTrue(relay.ocd_relay_deadline)
            hold = self.env["ocd.product.hold"].search([("partner_id", "=", self.env.ref("ocd_live_demo.customer_ruth").id)],
                                                       order="id desc", limit=1)
            self.assertIn(hold.state, ("accepted", "requested", "expired", "taken", "cancelled"))
        with freeze_time(self._douala(tomorrow + timedelta(days=1), 13, 0)):
            demo.keep_shop(fields.Datetime.now())
            self.assertEqual(collect.ocd_stage, "delivered", "Picked up at the counter")
            self.assertEqual(relay.ocd_stage, "delivered", "Picked up at the relay point")

    def test_ocd_express_of_the_demo(self):
        """Nadège Mode sends her parcels with OCD Express: the parcels of the last week delivered
        and counted for her, her money paid every working day, a request waiting for the team."""
        nadege = self._express()
        company = self.env.company
        self.assertEqual(nadege.ocd_express_state, "active")
        self.assertEqual(self.env.ref("ocd_live_demo.sender_linda").ocd_express_state, "requested",
                         "A request to check in « To check »")
        self.assertIn(self.env.ref("delivery_cameroon.city_cm_douala"), company.ocd_express_city_ids)
        self.assertTrue(company.ocd_express_point and company.ocd_express_momo_number)
        parcels = self._express_parcels()
        self.assertGreaterEqual(len(parcels), 4 * len(scenario.EXPRESS_DAY), "The parcels of the working days")
        self.assertTrue(all(parcel.name.startswith("EX-") for parcel in parcels))
        before = parcels.filtered(lambda p: p.create_date < fields.Datetime.now() - timedelta(days=3))
        self.assertTrue(before)
        self.assertLessEqual(set(before.mapped("ocd_stage")), {"delivered", "returned"},
                             "The parcels of the days before are delivered, or given back")
        self.assertTrue(before.filtered(lambda p: p.ocd_express_return_state == "handed_back"),
                        "A parcel refused at the door, given back against the return code")
        self.assertTrue(parcels.filtered(lambda p: p.ocd_express_claim_state == "sender_right"),
                        "A problem reported by a customer, checked by the team")
        delivered = before.filtered(lambda p: p.ocd_stage == "delivered" and p.ocd_express_claim_state != "open")
        self.assertEqual(set(delivered.mapped("ocd_express_money_state")), {"counted"}, "The money reached OCD")
        pickups = self.env["ocd.express.pickup"].search([("sender_id", "=", nadege.id), ("state", "=", "done")])
        self.assertTrue(pickups and all(pickup.taken_count >= 3 for pickup in pickups),
                        "A passage for the parcels of a wave, free from 3 parcels")
        self.assertEqual(pickups.courier_id, self.env.ref("ocd_live_demo.courier_ekwalla"), "The courier of Akwa")
        payouts = self.env["ocd.payout"].search([("vendor_id", "=", nadege.id)])
        self.assertGreaterEqual(len(payouts.filtered(lambda p: p.state == "paid" and p.payment_ids)), 3,
                                "Paid every working day, recorded in the accounting")
        # « My money »: what was paid does not count again
        paid = payouts.filtered(lambda p: p.state == "paid").move_ids
        self.assertLessEqual(set(paid.mapped("payment_state")), {"paid", "in_payment"})
        self.assertTrue(parcels.partner_id._ocd_demo_contact(), "No WhatsApp to the customers of the demo")
        self.assertFalse(self.env["res.partner"].create({
            "name": "Vraie cliente", "phone": "+237 699999999", "ocd_express_recipient": True,
        })._ocd_demo_contact())

    def test_a_day_of_ocd_express(self):
        """The next working day, hour by hour in Douala: the parcels of Nadège at every step."""
        nadege = self._express()
        demo = OcdLiveDemo(self.env)
        day = demo.shop_today(fields.Datetime.now()) + timedelta(days=1)
        if day.weekday() == 6:
            day += timedelta(days=1)  # no pick-up on Sunday
        Pickup = self.env["ocd.express.pickup"]
        with freeze_time(self._douala(day, 14, 30)):
            demo.keep_shop(fields.Datetime.now())
            of_day = self._express_parcels().filtered(lambda p: p.create_date >= self._douala(day, 0, 0))
            self.assertEqual(len(of_day), len(scenario.EXPRESS_DAY) - 1, "The parcels of the day, the last at 17:30")
            stages = set(self._express_parcels().mapped("ocd_stage"))
            for stage in ("to_prepare", "ready", "on_the_way", "problem", "delivered"):
                self.assertIn(stage, stages, stage)
            checked = of_day.filtered(lambda p: p.ocd_express_check == "to_check")
            self.assertEqual(len(checked), 1, "Above the limit of Nadège: the team checks it")
            morning = Pickup.search([("sender_id", "=", nadege.id), ("date", "=", day), ("part", "=", "morning")])
            self.assertEqual(morning.state, "done")
            self.assertGreaterEqual(morning.taken_count, 4)
            self.assertTrue(of_day.filtered(lambda p: p.ocd_express_confirm == "confirmed"), "« I confirm »")
            self.assertTrue(of_day.filtered("ocd_express_latitude"), "« Send my position »")
        with freeze_time(self._douala(day, 18, 0)):
            demo.keep_shop(fields.Datetime.now())
            self.assertEqual(checked.ocd_express_check, "ok")
            self.assertEqual(checked.ocd_stage, "picked", "Picked up with the parcels of the afternoon")
            returned = self._express_parcels().filtered(lambda p: p.ocd_express_return_state == "to_return")
            self.assertEqual(len(returned), 1, "Refused at the door: to give back to Nadège")
            self.assertEqual(len(returned._ocd_express_return_code()), 6)
            self.assertTrue(self._express_parcels().filtered(lambda p: p.ocd_express_claim_state == "open"),
                            "A problem reported by a customer, the money of the parcel waits")
        with freeze_time(self._douala(day, 20, 0)):
            demo.keep_shop(fields.Datetime.now())
            courier = self.env.ref("ocd_live_demo.courier_ekwalla")
            courier.invalidate_recordset(["ocd_cash_on_hand"])
            self.assertFalse(courier.ocd_cash_on_hand, "The cash handed over at 19:30")
            delivered = of_day.filtered(lambda p: p.ocd_stage == "delivered")
            self.assertTrue(delivered)
            self.assertEqual(set(delivered.mapped("ocd_express_money_state")), {"counted"})
            payouts = self.env["ocd.payout"].search([("vendor_id", "=", nadege.id)])
            self.assertTrue(payouts.filtered(lambda p: p.date == day and p.state == "paid"),
                            "Paid at 10:00 the money counted the day before")
            self.assertFalse(payouts.filtered(lambda p: p.state != "paid"))

    def test_ocd_express_left_open_the_days_before(self):
        """A parcel of Nadège created during a presentation two days ago, left waiting: delivered in
        the evening of its day, its money counted."""
        nadege = self._express()
        akwa = self.env.ref("delivery_cameroon.district_douala_akwa")
        name, phone, _district, landmark = scenario.EXPRESS_CUSTOMERS[0]
        parcel = self.env["stock.picking"]._ocd_express_create(nadege, {
            "name": name, "phone": phone, "district": akwa, "city": akwa.city_id, "landmark": landmark,
            "content": "Sac", "prepaid": False, "amount": 9000, "value": 0, "fee_by": "sender",
            "can_open": True, "consent": True, "dropoff": False,
        })
        self.env.flush_all()
        self.env.cr.execute("UPDATE stock_picking SET create_date = %s WHERE id = %s",
                            (fields.Datetime.now() - timedelta(days=2), parcel.id))
        parcel.invalidate_recordset()
        OcdLiveDemo(self.env).keep_shop(fields.Datetime.now())
        self.assertEqual(parcel.ocd_stage, "delivered")
        self.assertEqual(parcel.ocd_express_money_state, "counted")

    def test_shop_without_piling_up(self):
        demo = OcdLiveDemo(self.env)
        tomorrow = demo.shop_today(fields.Datetime.now()) + timedelta(days=1)

        def counts():
            partners = self._demo_partners()
            return (
                self.env["sale.order"].search_count([("partner_id", "in", partners.ids)]),
                self.env["mail.message"].search_count([("model", "=", "discuss.channel")]),
                self.env["ocd.cash.remittance"].search_count([]),
                self.env["ocd.payout"].search_count([]),
                self.env["stock.picking"].search_count([("ocd_is_parcel", "=", True)]),
                self.env["account.move"].search_count([("move_type", "in", ("in_invoice", "in_refund"))]),
                self.env["ocd.express.pickup"].search_count([]) if "ocd.express.pickup" in self.env else 0,
            )

        with freeze_time(self._douala(tomorrow, 16, 0)):
            demo.keep_shop(fields.Datetime.now())
            before = counts()
            demo.keep_shop(fields.Datetime.now())
            self.assertEqual(counts(), before, "Each step takes place once")

    def test_week_of_the_studio(self):
        """Every live of the week on the days around today, paid when it was booked: the vendors
        of Lomé at the studio, the others from home; over, then replayed; Saturday full."""
        demo = OcdLiveDemo(self.env)
        demo.keep_current()
        now = fields.Datetime.now()
        rows = demo.plan()
        self.assertGreater(len(rows), 60, "About four lives a day over three weeks")
        Booking = self.env["ocd.live.booking"]
        for start, vendor, mode, _need, _host in rows:
            booking = Booking.search([("partner_id", "=", vendor.id), ("start_datetime", "=", start)])
            self.assertEqual(len(booking), 1, f"{vendor.name} at {start}")
            self.assertEqual(booking.mode, mode)
            self.assertEqual(booking.sale_order_id.state, "sale", "Paid when it was booked")
            self.assertEqual(mode == "studio", vendor.country_id.code == "TG", "Only the vendors of Lomé come to the studio")
            self.assertLessEqual(booking.create_date, now)
            if booking.end_datetime <= now:
                self.assertEqual(booking.state, "done")
                if mode == "remote":
                    self.assertTrue(booking.animatrice_id, "A remote live of the past had its host")
                if booking.end_datetime <= now - timedelta(hours=1):
                    self.assertTrue(booking.replay_published and booking.replay_url.startswith("https://"))
            else:
                self.assertEqual(booking.state, "confirmed")
        coming = Booking.search([("partner_id", "in", self._demo_partners().ids), ("start_datetime", ">", now)])
        self.assertTrue(coming.filtered("needs_host"), "A coming remote live waits for its host")
        saturday = next(demo.today() + timedelta(days=offset) for offset in range(1, 8)
                        if (demo.today() + timedelta(days=offset)).weekday() == scenario.FULL_DAY)
        self.assertFalse(Booking._ocd_get_free_counts([saturday], mode="remote")[saturday], "Saturday is full")
        waiting = self.env["ocd.live.waitlist"].search([("day", "=", saturday), ("state", "=", "waiting")])
        self.assertEqual(waiting.partner_id.mapped("name"), ["Chioma Hair", "Moussa Bazin"])

    def test_kept_current_without_piling_up(self):
        demo = OcdLiveDemo(self.env)
        partners = self._demo_partners()

        def counts():
            domain = [("partner_id", "in", partners.ids)]
            return {
                model: self.env[model].search_count(domain)
                for model in ("ocd.live.booking", "sale.order", "ocd.directory.listing", "ocd.directory.pass",
                              "ocd.live.credit", "ocd.live.waitlist")
            } | {"moments": self.env["ocd.live.moment"].search_count([("booking_id.partner_id", "in", partners.ids)])}

        with freeze_time(fields.Datetime.now()):
            demo.keep_current()
            before = counts()
            demo.keep_current()
            self.assertEqual(counts(), before, "Only what is missing is added")

    def test_the_next_day(self):
        """A day later, the lives of the new last day are there, and those of today are replays."""
        demo = OcdLiveDemo(self.env)
        today = demo.today()
        Booking = self.env["ocd.live.booking"]
        new_day = today + timedelta(days=scenario.NEXT_DAYS + 1)
        with freeze_time(self._at(today + timedelta(days=1), 23, 30)):
            demo.keep_current()
            starts = [demo.start(new_day, row[0]) for row in scenario.WEEK[new_day.weekday()]]
            added = Booking.search([("partner_id", "in", self._demo_partners().ids), ("start_datetime", "in", starts)])
            self.assertEqual(len(added), len(starts), "The lives of the new day")
            of_today = Booking.search([
                ("partner_id", "in", self._demo_partners().ids), ("credit_id", "!=", False),
                ("start_datetime", ">=", self._at(today, 0)), ("start_datetime", "<", self._at(today + timedelta(days=1), 0)),
            ])
            self.assertTrue(of_today)
            self.assertEqual(set(of_today.mapped("state")), {"done"})
            self.assertTrue(all(of_today.mapped("replay_published")), "Replayed an hour after the end")

    def test_lives_of_the_directory_by_window(self):
        """The vendors of a window go live one after the other, one link waits for the team; the
        vendors of the next window have sent their link, the night before for the morning."""
        demo = OcdLiveDemo(self.env)
        Listing = self.env["ocd.directory.listing"]
        partners = self._demo_partners()
        self._end_open_links()
        day = demo.today() + timedelta(days=2)
        morning, midday = self._vendors_of(scenario.MORNING), self._vendors_of(scenario.MIDDAY)
        with freeze_time(self._at(day, 8, 15)):
            demo.keep_listings(fields.Datetime.now())
        links = Listing.search([("partner_id", "in", partners.ids), ("window_start", "=", self._at(day, 8))])
        self.assertEqual(links.partner_id, morning)
        self.assertLessEqual(len(links.filtered(lambda link: link.state == "published")), 2, "At 8:15, two went live")
        with freeze_time(self._at(day, 10, 30)):
            demo.keep_listings(fields.Datetime.now())
        live = links.filtered(lambda link: link.state == "published")
        waiting = links.filtered(lambda link: link.state == "to_check")
        self.assertEqual(len(waiting), 1, "One link waits for the check of the team")
        self.assertNotEqual(waiting.country_id.code, "TG", "The vendors of Togo are live")
        self.assertEqual(len(live), len(morning) - 1)
        self.assertIn(self.env.ref("ocd_live_demo.vendor_awa"), live.partner_id)
        self.assertEqual(len(set(live.mapped("checked_at"))), len(live), "Live one after the other")
        sent = Listing.search([("partner_id", "in", partners.ids), ("window_start", "=", self._at(day, 11))])
        self.assertEqual(sent.partner_id, midday, "The vendors of midday sent their link")
        self.assertEqual(set(sent.mapped("state")), {"queued"})
        with freeze_time(self._at(day, 22, 0)):
            Listing._cron_update_windows()
            demo.keep_listings(fields.Datetime.now())
        self.assertEqual(set(links.mapped("state")), {"ended"})
        tomorrow = Listing.search([("partner_id", "in", partners.ids), ("window_start", "=", self._at(day + timedelta(days=1), 8))])
        self.assertEqual(tomorrow.partner_id, morning, "The links of the morning, sent the evening before")

    def test_payment_to_check(self):
        """A live held while the team checks the Mobile Money announced by Kossi; once
        confirmed, another one comes."""
        demo = OcdLiveDemo(self.env)
        kossi = self.env.ref("ocd_live_demo.vendor_kossi")
        Booking = self.env["ocd.live.booking"]
        held = Booking.search([("partner_id", "=", kossi.id), ("state", "=", "draft")])
        self.assertEqual(len(held), 1)
        self.assertIn("Flooz", held.sale_order_id.ocd_payment_reference)
        self.assertEqual(held.sale_order_id.transaction_ids.mapped("state"), ["pending"],
                         "Mobile Money chosen on the payment page: « Payment to check » in the planning")
        self.assertGreater(held._ocd_hold_end(), fields.Datetime.now() + timedelta(hours=12), "Held while the team checks")
        held.action_ocd_mark_paid()
        self.assertEqual(held.state, "confirmed")
        demo.keep_current()
        again = Booking.search([("partner_id", "=", kossi.id), ("state", "=", "draft")])
        self.assertEqual(len(again), 1)
        self.assertNotEqual(again.start_datetime, held.start_datetime)

    def test_real_video_and_live_link_of_the_settings(self):
        """With a real video and a real live link in the settings (section Demo), every replay of
        the demo plays the video with its products along it, every live opens the account, and
        the next replays too; a link pasted by hand stays; empty, the examples come back."""
        Settings = self.env["ocd.live.settings"]
        Booking = self.env["ocd.live.booking"]
        demo = OcdLiveDemo(self.env)
        partners = self._demo_partners()
        video, account = "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.tiktok.com/@ocdlive/live"
        page = Settings.save_settings_page({
            "ocd_demo_replay_url": "https://example.com/video", "ocd_demo_live_url": "http://www.tiktok.com/@ocdlive/live",
        })
        self.assertFalse(page["ok"])
        self.assertEqual(set(page["errors"]), {"ocd_demo_replay_url", "ocd_demo_live_url"}, "A video that does not play")
        replays = Booking.search([("partner_id", "in", partners.ids), ("replay_published", "=", True)])
        by_hand = replays[:1]
        by_hand.replay_url = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
        page = Settings.save_settings_page({
            "ocd_demo_replay_url": video, "ocd_demo_replay_minutes": 3, "ocd_demo_live_url": account,
        })
        self.assertTrue(page["ok"], page.get("errors"))
        self.assertEqual(set((replays - by_hand).mapped("replay_url")), {video})
        self.assertEqual(by_hand.replay_url, "https://www.youtube.com/watch?v=aaaaaaaaaaa", "A link pasted by hand stays")
        moments = (replays - by_hand).moment_ids
        self.assertTrue(moments)
        self.assertLess(max(moments.mapped("offset_seconds")), 180, "The products along the video of 3 minutes")
        coming = Booking.search([("partner_id", "in", partners.ids), ("state", "in", ("draft", "confirmed"))])
        self.assertEqual(set(coming.mapped("live_url")), {account})
        links = self.env["ocd.directory.listing"].search([
            ("partner_id", "in", partners.ids), ("state", "in", ("queued", "to_check", "published")),
        ])
        self.assertEqual(set(links.mapped("url")) | {account}, {account})
        with freeze_time(self._at(demo.today() + timedelta(days=1), 23, 30)):
            demo.keep_current()
        new = Booking.search([("partner_id", "in", partners.ids), ("replay_published", "=", True), ("id", "not in", replays.ids)])
        self.assertTrue(new)
        self.assertEqual(set(new.mapped("replay_url")), {video}, "The next replays play it too")
        self.assertTrue(Settings.save_settings_page({"ocd_demo_replay_url": "", "ocd_demo_live_url": ""})["ok"])
        self.assertNotIn(video, (replays - by_hand).mapped("replay_url"), "The examples again")
        self.assertNotIn(account, coming.mapped("live_url"))

    def test_cards_of_the_feed_and_accounts_of_ocd_live(self):
        """The cards show a short video (Awa), an image (Ama), the products (Kossi); the lives go
        on the accounts of OCD Live on TikTok, the vendors of the remote lives join them."""
        awa = self.env.ref("ocd_live_demo.vendor_awa")
        ama = self.env.ref("ocd_live_demo.vendor_ama")
        kossi = self.env.ref("ocd_live_demo.vendor_kossi")
        self.assertEqual(awa._ocd_card_media()["kind"], "video")
        self.assertEqual(ama._ocd_card_media()["kind"], "image")
        self.assertEqual(kossi._ocd_card_media()["kind"], "products")
        self.assertEqual(awa.ocd_live_handle, "@awa.gateaux", "Its name on TikTok, for the host")
        self.assertTrue(self.env.ref("ocd_live_demo.host_dzifa").mobile_phone)
        togo = self.env.ref("ocd_live_demo.account_togo")
        africa = self.env.ref("ocd_live_demo.account_africa")
        coming = self.env["ocd.live.booking"].search([
            ("partner_id", "in", self._demo_partners().ids), ("state", "=", "confirmed"),
        ])
        self.assertTrue(coming)
        for booking in coming:
            expected = togo if booking.partner_id.country_id == togo.country_ids else africa
            self.assertEqual(booking.account_id, expected, booking.display_name)
        self.assertFalse(any(coming.mapped("live_url")), "No link of the vendor: the one of the account")
        remote = coming.filtered(lambda booking: booking.mode == "remote")[:1]
        self.assertEqual(remote._ocd_watch_url(), remote.account_id.live_url)

    def test_currencies_by_country(self):
        """Awa (Lomé) sees her prices in CFA (XOF), Brenda (Douala) in FCFA (XAF, the currency of
        CamPay) for the same amount, Kadi (Paris) in euros rounded to the unit."""
        self.assertTrue(self.env["ocd.live.currencies"]._ocd_is_set_up())
        discovery = self.env.ref("ocd_live.product_package_discovery")
        prices = {}
        for xmlid, currency in (("vendor_awa", "XOF"), ("vendor_brenda", "XAF"), ("vendor_kadi", "EUR")):
            pricelist = self.env.ref(f"ocd_live_demo.{xmlid}").property_product_pricelist
            self.assertEqual(pricelist.currency_id.name, currency, xmlid)
            prices[currency] = pricelist._get_product_price(discovery, 1.0)
        self.assertAlmostEqual(prices["XAF"], prices["XOF"], places=2)
        self.assertEqual(prices["EUR"], round(prices["XOF"] / 655.957))

    def test_short_link_of_a_video_in_the_settings(self):
        """A short link of TikTok (Share › Copy the link: vt.tiktok.com/ZS…) is followed to the full
        address of the video, which the replays play; one that does not open says what to paste."""
        Settings = self.env["ocd.live.settings"]
        full = "https://www.tiktok.com/@bovann/video/7706183840514968865"

        def head(url, **kwargs):
            if "ZSoff" in url:
                raise requests.ConnectionError("no answer")
            return SimpleNamespace(status_code=301, headers={"Location": f"{full}?_r=1&_t=ZS-9BLO2PoUM5M"})

        with patch.object(tools.requests, "head", side_effect=head), patch.dict(tools._expanded, clear=True):
            page = Settings.save_settings_page({"ocd_demo_replay_url": "https://vt.tiktok.com/ZSoff/"})
            self.assertFalse(page["ok"])
            self.assertIn("could not be opened", page["errors"]["ocd_demo_replay_url"])
            page = Settings.save_settings_page({"ocd_demo_replay_url": "https://vt.tiktok.com/ZSpHErvqo"})
        self.assertTrue(page["ok"], page.get("errors"))
        self.assertEqual(self.env["ir.config_parameter"].get_str(PARAM_REPLAY_URL), full)
        replays = self.env["ocd.live.booking"].search([
            ("partner_id", "in", self._demo_partners().ids), ("replay_published", "=", True),
        ])
        self.assertEqual(set(replays.mapped("replay_url")), {full})
        self.assertEqual(replays[:1]._ocd_replay_embed()["platform"], "tiktok")

    def test_uninstall_removes_what_the_demo_created(self):
        partners = self._demo_partners()
        orders = self.env["sale.order"].search([("partner_id", "in", partners.ids)])
        self.assertTrue(orders)
        saved = self.env["ir.config_parameter"].get_str(PARAM_OPEN_DATE)
        if "ocd.express.pickup" in self.env:
            express = self._express_parcels()
            customers = express.partner_id
            payments = self.env["ocd.payout"].search([("vendor_id", "in", partners.ids)]).payment_ids
            self.assertTrue(express and customers and payments)
            cities = self.env.company.ocd_express_city_ids
            if json.loads(self.env["ir.config_parameter"].get_str(PARAM_EXPRESS) or "{}").get("city"):
                cities -= self.env.ref("delivery_cameroon.city_cm_douala")  # opened by the demo
        uninstall_hook(self.env)
        domain = [("partner_id", "in", partners.ids)]
        self.assertFalse(orders.exists())
        for model in ("ocd.live.booking", "ocd.live.credit", "ocd.directory.pass", "ocd.directory.listing", "ocd.live.waitlist"):
            self.assertFalse(self.env[model].with_context(active_test=False).search(domain), model)
        self.assertFalse(self.env.ref("ocd_live.payment_provider_momo_team").active)
        self.assertFalse(self.env.ref("delivery.payment_provider_cod").is_published, "Back as before the demo")
        if saved:
            self.assertEqual(fields.Date.to_string(self.env.company.ocd_booking_open_date), saved.split('"date": "')[1][:10],
                             "The opening date of the bookings set by the team comes back")
        if "whatsapp.account" in self.env:
            self.assertFalse(self.env["discuss.channel"].search(
                [("channel_type", "=", "whatsapp"), ("whatsapp_partner_id", "in", partners.ids)]
            ), "The conversations of the demo are removed")
        self.assertFalse(self.env["ocd.payout"].search([("vendor_id", "in", partners.ids)]))
        self.assertFalse(self.env["ocd.cash.remittance"].search([("courier_id", "in", partners.ids)]))
        self.assertFalse(self.env["account.move"].search(domain + [("move_type", "in", ("in_invoice", "in_refund"))]))
        templates = self.env["ir.model.data"].search(
            [("module", "=", "ocd_live_demo"), ("model", "=", "product.template")]
        ).mapped("res_id")
        self.assertFalse(self.env["stock.quant"].search([("product_id.product_tmpl_id", "in", templates)]))
        # The stores, the team and the life of the shop
        for model in ("ocd.vendor.place", "ocd.vendor.member", "ocd.vendor.follower", "ocd.vendor.review"):
            self.assertFalse(self.env[model].with_context(active_test=False).search([("vendor_id", "in", partners.ids)]), model)
        self.assertFalse(self.env["ocd.vendor.count"].search([("vendor_id", "in", partners.ids)]))
        self.assertFalse(self.env["ir.config_parameter"].get_str(PARAM_SHOP))
        if "ocd.express.pickup" in self.env:
            self.assertFalse(express.exists(), "The parcels of OCD Express")
            self.assertFalse(customers.exists(), "Their customers")
            self.assertFalse(self.env["ocd.express.pickup"].search([("sender_id", "in", partners.ids)]))
            self.assertFalse(payments.exists(), "The money paid to the senders")
            self.assertEqual(self.env.company.ocd_express_city_ids, cities, "Back as before the demo")


@tagged("post_install", "-at_install")
class TestOcdLiveDemoFeed(DemoCommon, HttpCase):
    """The feed of the lives, as a visitor sees it during a presentation."""

    def test_feed_of_each_country(self):
        demo = OcdLiveDemo(self.env)
        self._end_open_links()
        day = demo.today() + timedelta(days=2)
        kossi = self.env.ref("ocd_live_demo.vendor_kossi")
        with freeze_time(self._at(day, 19, 30)):
            demo.keep_current()
            html = self.url_open("/lives?pays=tg").text
            senegal = self.url_open("/lives?pays=sn").text
        link = self.env["ocd.directory.listing"].search([("partner_id", "=", kossi.id), ("window_start", "=", self._at(day, 18))])
        self.assertEqual(link.state, "published")
        keys = re.findall(r'data-key="([^"]+)"', html)
        self.assertEqual(keys[0], f"l{link.id}", "In Togo in the evening: Kossi is live first")
        chips = {
            re.search(r'data-country="([a-z]+)"', tag).group(1)
            for tag in re.findall(r"<a [^>]*o_ocd_feed_chip[^>]*>", html)
        }
        self.assertLessEqual({"tg", "cm", "ci", "sn", "bj", "gh", "ng", "fr"}, chips, "Every country of the demo")
        moussa = self.env["ocd.directory.listing"].search([
            ("partner_id", "=", self.env.ref("ocd_live_demo.vendor_moussa").id), ("window_start", "=", self._at(day, 18)),
        ])
        senegal_keys = re.findall(r'data-key="([^"]+)"', senegal)
        if moussa.state == "published":
            self.assertEqual(senegal_keys[0], f"l{moussa.id}", "In Senegal: Moussa first")
        else:
            self.assertNotEqual(senegal_keys[0], "none-SN", "Senegal has its next lives and replays")
