import json

from odoo import Command
from odoo.tests import tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdBotStores(OcdShopCommon):
    """The bot of OCD Live gives the stores of a vendor (chantier 20, A.2 of the plan, design
    VacancesProximite): « Where are you? » about a product linked in the conversation, or about
    the latest order of the customer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110009", "waba_id": "2220009", "access_token": "test-token",
            "resource_calendar_id": False, "bot_enabled": True,
        })
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                           "ocd_place_proof_required": False})
        cls.customer = cls.env["res.partner"].create({
            "name": "Estelle", "phone": "+237 670000019", "country_id": cls.env.ref("base.cm").id,
            "whatsapp_opt_in": True, "lang": "en_US",
        })
        cls.store = cls.env["ocd.vendor.place"]._ocd_vendor_create(cls.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": cls.akwa.id, "city_id": cls.akwa.city_id.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
        })
        cls.store._ocd_set_hours(cls.company._ocd_place_default_intervals())
        cls.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        cls.Message = cls.env["whatsapp.message"]

    def receive(self, body, wa_id):
        message = {"from": "237670000019", "id": wa_id, "timestamp": "1760000000", "type": "text", "text": {"body": body}}
        return self.Message._process_incoming(
            self.account, message, [{"profile": {"name": "Estelle"}, "wa_id": "237670000019"}]
        )

    def sent(self, channel):
        return self.Message.search([("channel_id", "=", channel.id), ("direction", "=", "outgoing")], order="id")

    def test_where_is_the_store_of_a_product(self):
        link = f"https://ocdlive.com{self.dress.product_tmpl_id.website_url}"
        channel = self.receive(f"Bonjour, {link} le magasin est où ?", "wamid.W1").channel_id
        sent = self.sent(channel)
        text = sent.filtered(lambda message: message.message_type == "text" and "The stores of Brenda Wax" in (message.body or ""))
        self.assertTrue(text, sent.mapped("body"))
        self.assertIn("Brenda Wax Akwa", text.body)
        self.assertIn("En face de la pharmacie du Port", text.body)
        location = sent.filtered(lambda message: message.message_type == "location")
        self.assertEqual(json.loads(location.payload)["location"]["latitude"], 4.0511)

    def test_where_are_you_after_an_order(self):
        self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "order_line": [Command.create({"product_id": self.dress.id, "product_uom_qty": 1})],
        })
        channel = self.receive("Où êtes-vous ?", "wamid.W2").channel_id
        self.assertTrue(any("The stores of Brenda Wax" in (message.body or "") for message in self.sent(channel)))

    def test_a_vendor_without_store_and_no_question(self):
        channel = self.receive(f"Où êtes-vous ? https://ocdlive.com/ocd/boutique/{self.fatou.id}", "wamid.W3").channel_id
        self.assertTrue(any("Fatou Karite has no store open to the public" in (message.body or "")
                            for message in self.sent(channel)))
        # Another customer, nothing about a vendor: the bot answers as before
        channel = self.Message._process_incoming(self.account, {
            "from": "237670000029", "id": "wamid.W4", "timestamp": "1760000000", "type": "text",
            "text": {"body": "Où êtes-vous ?"},
        }, [{"profile": {"name": "Paul"}, "wa_id": "237670000029"}]).channel_id
        self.assertFalse(any("The stores of" in (message.body or "") for message in self.sent(channel)))
