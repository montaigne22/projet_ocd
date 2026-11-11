import json
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.whatsapp_cloud_sale.controllers.main import WebsiteSaleWhatsApp


@tagged("post_install", "-at_install")
class TestWhatsAppCloudSale(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "My Shop",
            "phone_number_id": "1110001",
            "waba_id": "2220002",
            "access_token": "test-token",
        })
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.partner = cls.env["res.partner"].create({
            "name": "Awa Ngono",
            "phone": "670000000",
            "country_id": cls.env.ref("base.cm").id,
            "whatsapp_opt_in": True,
            "lang": "fr_FR",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Sac à dos", "type": "consu", "list_price": 65000,
        })
        cls.website = cls.env["website"].search([], limit=1)

    def _messages(self, template_xmlid):
        return self.env["whatsapp.message"].search([
            ("partner_id", "=", self.partner.id),
            ("template_id", "=", self.env.ref(template_xmlid).id),
        ])

    def _create_order(self, **values):
        return self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            **values,
        })

    def test_order_confirmed_then_shipped(self):
        order = self._create_order()
        order.action_confirm()
        confirmed = self._messages("whatsapp_cloud_sale.template_order_confirmed")
        self.assertEqual(confirmed.state, "queued")
        self.assertEqual(confirmed.res_id, order.id)
        self.assertIn(order.name, confirmed.body)
        self.assertTrue(confirmed.body.startswith("Bonjour Awa Ngono, merci pour votre commande"))

        picking = order.picking_ids
        self.assertTrue(picking)
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking._action_done()
        shipped = self._messages("whatsapp_cloud_sale.template_order_shipped")
        self.assertEqual(shipped.res_id, picking.id)
        self.assertIn(order.name, shipped.body)
        # "Track my order" link button ({base_url}/{{1}}): the order in the customer account
        button = json.loads(shipped.sudo().payload)["template"]["components"][-1]
        self.assertEqual(button["type"], "button")
        self.assertTrue(button["parameters"][0]["text"].startswith(f"my/orders/{order.id}?access_token="))

    def test_order_confirmed_in_english(self):
        self.env["res.lang"]._activate_lang("en_US")
        self.partner.lang = "en_US"
        order = self._create_order()
        order.action_confirm()
        confirmed = self._messages("whatsapp_cloud_sale.template_order_confirmed_en")
        self.assertEqual(confirmed.res_id, order.id)
        self.assertTrue(confirmed.body.startswith("Hello Awa Ngono, thank you for your order"))
        self.assertFalse(self._messages("whatsapp_cloud_sale.template_order_confirmed"))

    def test_no_message_without_consent(self):
        self.partner.whatsapp_opt_in = False
        self._create_order().action_confirm()
        message = self._messages("whatsapp_cloud_sale.template_order_confirmed")
        self.assertEqual(message.state, "skipped")

    def _pay_later(self, order, custom_mode):
        provider = self.env["payment.provider"].search([
            ("code", "=", "custom"), ("custom_mode", "=", custom_mode),
            ("company_id", "=", order.company_id.id),
        ], limit=1)
        if not provider.payment_method_ids:
            self.skipTest(f"No {custom_mode} payment provider in this database.")
        transaction = self.env["payment.transaction"].create({
            "provider_id": provider.id,
            "payment_method_id": provider.payment_method_ids[:1].id,
            "amount": order.amount_total,
            "currency_id": order.currency_id.id,
            "partner_id": self.partner.id,
            "reference": f"{order.name}-WA",
            "sale_order_ids": [Command.set(order.ids)],
        }).with_context(payment_safe_write=True)
        transaction._set_pending()
        transaction._post_process()
        return transaction

    def test_order_received_when_paid_by_transfer(self):
        order = self._create_order(website_id=self.website.id)
        transaction = self._pay_later(order, "wire_transfer")
        self.assertEqual(order.state, "sent")
        received = self._messages("whatsapp_cloud_sale.template_order_received")
        self.assertEqual(received.res_id, order.id)
        method = transaction.payment_method_id.with_context(
            lang=received.template_id._get_render_lang()
        )
        self.assertIn(f"Moyen de paiement : {method.name}. Elle sera confirmée", received.body)
        self.assertFalse(self._messages("whatsapp_cloud_sale.template_order_confirmed"))

    def test_order_paid_on_delivery_is_confirmed(self):
        order = self._create_order(website_id=self.website.id)
        with patch.object(type(order), "_send_order_confirmation_mail"):
            self._pay_later(order, "cash_on_delivery")
        self.assertEqual(order.state, "sale")
        self.assertFalse(self._messages("whatsapp_cloud_sale.template_order_received"))
        confirmed = self._messages("whatsapp_cloud_sale.template_order_confirmed")
        self.assertEqual(confirmed.res_id, order.id)

    def test_checkout_consent(self):
        controller = WebsiteSaleWhatsApp()
        with MockRequest(self.env, website=self.website):
            values, extra = controller._parse_form_data({
                "name": "Awa", "whatsapp_opt_in_shown": "1", "whatsapp_opt_in": "1",
            })
            self.assertIs(values["whatsapp_opt_in"], True)
            self.assertNotIn("whatsapp_opt_in", extra)
            values, _extra = controller._parse_form_data(
                {"name": "Awa", "whatsapp_opt_in_shown": "1"}
            )
            self.assertIs(values["whatsapp_opt_in"], False)
            values, _extra = controller._parse_form_data({"name": "Awa"})
            self.assertNotIn("whatsapp_opt_in", values)
