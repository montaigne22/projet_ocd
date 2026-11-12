from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDemoWhatsApp(TransactionCase):
    """No WhatsApp message goes to the contacts of the demo, whose numbers are examples."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live",
            "phone_number_id": "1110009",
            "waba_id": "2220009",
            "access_token": "test-token",
            "app_secret": "test-secret",
        })
        cls.template = cls.env["whatsapp.template"].create({
            "name": "News",
            "template_name": "news",
            "lang_code": "fr",
            "model_id": cls.env["ir.model"]._get_id("res.partner"),
            "account_id": cls.account.id,
            "body": "Bonjour {{1}}",
        })
        cls.template.variable_ids.value = "{{ object.name }}"
        cls.template.status = "approved"

    def test_no_message_to_a_contact_of_the_demo(self):
        vendor = self.env.ref("ocd_live_demo.vendor_brenda")
        vendor.whatsapp_opt_in = True
        self.assertFalse(self.template._send(vendor), "Nothing is even queued for an example number")
        reason = self.template._get_skip_reason(self.account, vendor, vendor._whatsapp_number())
        self.assertTrue(reason and "demo" in reason)
        customer = self.env["res.partner"].create({
            "name": "Vraie cliente",
            "phone": "+237 670009999",
            "country_id": self.env.ref("base.cm").id,
            "whatsapp_opt_in": True,
        })
        self.assertEqual(self.template._send(customer).state, "queued", "The other contacts get their messages")

    def test_tickets_of_the_demo_stay_home(self):
        """A live of the demo confirmed with a real account connected: no ticket goes out."""
        booking = self.env["ocd.live.booking"].search([
            ("partner_id", "=", self.env.ref("ocd_live_demo.vendor_kossi").id), ("state", "=", "draft"),
        ], limit=1)
        self.assertTrue(booking, "The demo holds a live while the team checks its payment")
        before = self.env["whatsapp.message"].search_count([])
        booking.with_context(tracking_disable=True).action_ocd_mark_paid()
        self.assertEqual(booking.state, "confirmed")
        self.assertEqual(self.env["whatsapp.message"].search_count([]), before)
