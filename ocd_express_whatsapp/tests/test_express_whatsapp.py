from datetime import date

from odoo import Command
from odoo.tests import tagged

from odoo.addons.ocd_express.tests.common import OcdExpressCommon


@tagged("post_install", "-at_install")
class TestOcdExpressWhatsapp(OcdExpressCommon):
    """The messages of OCD Express (design OcdExpress): announced and on the way to the customer,
    the pick-up, the news and the payout to the sender; nothing else to the customer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Express", "phone_number_id": "1110029", "waba_id": "2220029", "access_token": "test-token",
            "resource_calendar_id": False,
        })
        cls.afi.write({"lang": "en_US", "ocd_whatsapp_optin": True, "whatsapp_opt_in": True})
        cls.Message = cls.env["whatsapp.message"]

    def messages(self, record, name=None):
        domain = [("model", "=", record._name), ("res_id", "=", record.id)]
        if name:
            domain.append(("template_id.template_name", "=", name))
        return self.Message.search(domain, order="id")

    def test_the_customer_is_told_twice_only(self):
        parcel = self._create()
        self.assertTrue(parcel.partner_id.whatsapp_opt_in, "The customer agreed through the sender")
        announced = self.messages(parcel, "ocd_express_annonce")
        self.assertEqual(len(announced), 1)
        self.assertIn("your vendor Mode Afi sends you a parcel with OCD Express: 2 robes wax", announced.body)
        self.assertIn("to pay at the door:", announced.body)
        self.assertNotIn("code", announced.body.lower())
        template = self.env.ref("ocd_express_whatsapp.template_express_announced")
        self.assertEqual(template._render(template.button_url_value, parcel)[parcel.id], parcel._ocd_tracking_path())
        self._pick(parcel)
        parcel.action_ocd_leave()
        on_the_way = self.messages(parcel, "ocd_express_en_route")
        self.assertEqual(len(on_the_way), 1)
        self.assertNotIn(parcel.sudo().ocd_delivery_code, on_the_way.body)
        self.assertFalse(self.messages(parcel, "ocd_colis_en_route"), "Not the message of the shop")
        parcel._ocd_collect("online", self.courier, reference="CP-9")
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        customer = self.Message.search([("model", "=", "stock.picking"), ("res_id", "=", parcel.id),
                                        ("partner_id", "=", parcel.partner_id.id)])
        self.assertEqual(set(customer.template_id.mapped("template_name")), {"ocd_express_annonce", "ocd_express_en_route"})

    def test_the_sender_is_told(self):
        parcels = self._create() | self._create(name="Paul Eto'o", phone="+237 699000011")
        pickup = parcels.ocd_express_pickup_id
        pickup._ocd_done(parcels)
        picked = self.messages(pickup, "ocd_express_pris")
        self.assertIn("2 parcels", picked.body)
        self.assertIn(parcels.sorted("id")[0].name, picked.body)
        first = parcels.sorted("id")[0]
        first.action_ocd_leave()
        first._ocd_report_problem("absent")
        state = self.messages(first, "ocd_express_etat")
        self.assertIn("customer absent, a second passage is planned", state.body)
        first.action_ocd_retry()
        first.action_ocd_leave()
        first._ocd_collect("online", self.courier, reference="CP-10")
        first._ocd_check_code(first.sudo().ocd_delivery_code)
        last = self.messages(first, "ocd_express_etat")[-1].body
        self.assertIn("delivered,", last)
        self.assertIn("collected", last)
        payout = self.env["ocd.payout"]._ocd_prepare(vendors=self.afi, day=date(2026, 11, 24))
        payout.action_validate()
        payout.payment_reference = "OM-88213"
        payout.action_register_payment()
        paid = self.messages(payout, "ocd_express_versement")
        self.assertIn("reference OM-88213", paid.body)

    def test_not_for_me_stops_the_messages(self):
        parcel = self._create()
        parcel._ocd_express_not_for_me()
        self.assertTrue(parcel.partner_id.whatsapp_opt_out)
        again = self._create(name="Grace", phone="+237 691234567")
        self.assertFalse(self.messages(again, "ocd_express_annonce"), "No message to this number any more")

    def test_new_payout_number_told(self):
        self.afi.ocd_payout_momo = "+237 690000999"
        message = self.messages(self.afi, "ocd_express_numero")
        self.assertEqual(len(message), 1)
        self.assertIn("690000999", message.body.replace(" ", ""))

    def test_templates_for_meta(self):
        """Each template follows the rules of Meta (no variable at the start or at the end, words
        between two variables, never « code » in a Utility template) and has its English version."""
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "https://ocd.example.com")
        data = self.env["ir.model.data"].search([("model", "=", "whatsapp.template"), ("module", "=", "ocd_express_whatsapp")])
        templates = self.env["whatsapp.template"].browse(data.mapped("res_id"))
        self.assertEqual(len(templates), 14)
        for template in templates:
            with self.subTest(template=template.name):
                template._check_for_meta()
                self.assertNotIn("code", template.body.lower())
                english = templates.filtered(lambda other: other.template_name == template.template_name and other != template)
                self.assertEqual(len(english), 1)
                self.assertEqual(english.variable_ids.mapped("sequence"), template.variable_ids.mapped("sequence"))
                self.assertEqual(english.button_url_value, template.button_url_value)

    def test_at_the_relay_point(self):
        """Chantier 10: the customer is told by OCD Express when the relay point counted the
        parcel, never by the messages of the shop."""
        cm = self.env.ref("base.cm")
        self.company.ocd_relay_enabled = True
        self.env["ocd.delivery.rate"].create({
            "operator": "relay", "origin_city_id": self.douala.id, "country_id": cm.id,
            "city_ids": [Command.set(self.douala.ids)], "price": 500,
        })
        holder = self.env["res.partner"].create({"name": "Mama Ngo", "phone": "+237 677330011", "ocd_is_relay": True})
        relay = self.env["ocd.vendor.place"].create({
            "name": "Chez Mama Ngo", "vendor_id": holder.id, "kind": "store", "city_id": self.douala.id,
            "district_id": self.akwa.id, "relay": True, "relay_capacity": 25, "state": "approved",
        })
        relay._ocd_set_hours(self.company._ocd_place_default_intervals())
        parcel = self._create(relay=relay, district=False)
        self._pick(parcel)
        parcel.action_ocd_leave()
        self.assertFalse(self.messages(parcel, "ocd_express_en_route"), "Told when the relay point counted it")
        relay._ocd_relay_receive(parcel)
        message = self.messages(parcel, "ocd_express_point_relais")
        self.assertEqual(len(message), 1)
        self.assertIn("waits for you at the relay point Chez Mama Ngo", message.body)
        self.assertNotIn(parcel.sudo().ocd_delivery_code, message.body)
        self.assertFalse(self.messages(parcel, "ocd_colis_point_relais"), "Not the message of the shop")
        automation = self.env.ref("ocd_live_shop.automation_relay_arrived")
        self.assertIn(self.env.ref("ocd_express_whatsapp.template_express_relay"), automation.template_ids)
