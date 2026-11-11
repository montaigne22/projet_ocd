from odoo.tests import TransactionCase, tagged

from odoo.addons.ocd_live_demo.hooks import uninstall_hook


@tagged("post_install", "-at_install")
class TestOcdLiveDemo(TransactionCase):
    """The demo shows every part of OCD Live, and its uninstallation removes it all."""

    def _demo_partners(self):
        return self.env["res.partner"].browse(
            self.env["ir.model.data"].search([("module", "=", "ocd_live_demo"), ("model", "=", "res.partner")]).mapped("res_id")
        )

    def test_demo_shows_every_part(self):
        partners = self._demo_partners()
        self.assertGreaterEqual(len(partners.filtered("ocd_is_vendor")), 7)
        bookings = self.env["ocd.live.booking"].search([("partner_id", "in", partners.ids)])
        self.assertEqual(set(bookings.mapped("state")), {"confirmed", "draft", "done"})
        past = bookings.filtered(lambda b: b.state == "done")
        self.assertTrue(past.replay_published)
        self.assertEqual(len(self.env["ocd.live.moment"].search([("booking_id", "=", past.id)])), 3)
        credits = self.env["ocd.live.credit"].search([("partner_id", "in", partners.ids)])
        self.assertTrue(credits.filtered(lambda c: c.remaining == 1), "One live of the Duo left to place")
        self.assertEqual(len(partners.filtered("ocd_pass_active")), 6)
        self.assertEqual(len(self.env["ocd.directory.listing"].search([("partner_id", "in", partners.ids)])), 6)
        parcels = self.env["stock.picking"].search([("partner_id", "in", partners.ids), ("ocd_is_parcel", "=", True)])
        self.assertGreaterEqual(len(parcels), 3, "One parcel per vendor and per order")
        self.assertTrue(self.env.ref("ocd_live.payment_provider_momo_team").active)

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

    def test_uninstall_removes_what_the_demo_created(self):
        partners = self._demo_partners()
        orders = self.env["sale.order"].search([("partner_id", "in", partners.ids)])
        self.assertTrue(orders)
        uninstall_hook(self.env)
        domain = [("partner_id", "in", partners.ids)]
        self.assertFalse(orders.exists())
        for model in ("ocd.live.booking", "ocd.live.credit", "ocd.directory.pass", "ocd.directory.listing", "ocd.live.waitlist"):
            self.assertFalse(self.env[model].with_context(active_test=False).search(domain), model)
        self.assertFalse(self.env.ref("ocd_live.payment_provider_momo_team").active)
        self.assertFalse(self.env.ref("delivery.payment_provider_cod").is_published, "Back as before the demo")
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
