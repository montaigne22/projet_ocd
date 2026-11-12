import re
from datetime import datetime, time, timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.ocd_live_demo import scenario
from odoo.addons.ocd_live_demo.hooks import PARAM_OPEN_DATE, OcdLiveDemo, uninstall_hook


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
        website = self.env["website"].search([], limit=1)
        free = {
            tuple(sorted(v.product_template_attribute_value_ids.mapped("name"))): website._get_product_available_qty(v)
            for v in dress.product_variant_ids
        }
        self.assertLessEqual(free[("Bleu", "L")], 0, "A sold-out size")
        self.assertEqual(free[("Bleu", "M")], 3, "Only 3 left")
        self.assertTrue(self.env.ref("ocd_live_demo.product_black_soap")._is_sold_out())
        partners = self._demo_partners()
        couriers = partners.filtered("ocd_is_courier")
        self.assertGreaterEqual(len(couriers), 3)
        self.assertTrue(couriers.filtered(lambda c: not c.ocd_courier_available), "One courier off duty")
        parcels = self.env["stock.picking"].search([("partner_id", "in", partners.ids), ("ocd_is_parcel", "=", True)])
        stages = parcels.mapped("ocd_stage")
        for stage in ("to_prepare", "ready", "on_the_way", "delivered", "problem"):
            self.assertIn(stage, stages, stage)
        self.assertTrue(parcels.filtered("ocd_is_late"), "A late parcel for the dispatch")
        self.assertTrue(couriers.filtered(lambda c: c.ocd_cash_on_hand > 0), "Cash to hand over this evening")
        orders = parcels.sale_id
        self.assertTrue(orders.ocd_delivery_line_ids, "Orders priced with one price per parcel")
        if "whatsapp.account" in self.env:
            channels = self.env["discuss.channel"].search(
                [("channel_type", "=", "whatsapp"), ("whatsapp_partner_id", "in", partners.ids)]
            )
            self.assertGreaterEqual(len(channels), 4, "Conversations for the WhatsApp screen")
            self.assertTrue(channels.filtered("whatsapp_waiting_since"), "Customers waiting for an answer")
            self.assertFalse(channels.whatsapp_account_id.active, "Nothing goes to Meta from the demo")
        cod = self.env.ref("delivery.payment_provider_cod")
        self.assertTrue(cod.active and cod.is_published, "An order of the shop can be paid in cash at the door")
        bills = self.env["account.move"].search([("partner_id", "in", partners.ids), ("move_type", "=", "in_invoice")])
        if bills:
            # With the accounting set up when the demo was installed: the payouts to check
            self.assertTrue(self.env["ocd.payout"].search([("vendor_id", "in", partners.ids)]), "Payouts to check")

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

    def test_uninstall_removes_what_the_demo_created(self):
        partners = self._demo_partners()
        orders = self.env["sale.order"].search([("partner_id", "in", partners.ids)])
        self.assertTrue(orders)
        saved = self.env["ir.config_parameter"].get_str(PARAM_OPEN_DATE)
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
        self.assertFalse(self.env["account.move"].search(domain + [("move_type", "in", ("in_invoice", "in_refund"))]))
        templates = self.env["ir.model.data"].search(
            [("module", "=", "ocd_live_demo"), ("model", "=", "product.template")]
        ).mapped("res_id")
        self.assertFalse(self.env["stock.quant"].search([("product_id.product_tmpl_id", "in", templates)]))


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
