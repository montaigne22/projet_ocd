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
