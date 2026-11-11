import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestWhatsAppConversationSale(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["res.lang"]._activate_lang("en_US")
        cls.env["whatsapp.account"].search([]).active = False
        cls.salesperson = new_test_user(
            cls.env, login="wa_sales", name="Sales Sylvie",
            groups="base.group_user,sales_team.group_sale_salesman,whatsapp_cloud.group_whatsapp_user",
        )
        cls.agent = new_test_user(
            cls.env, login="wa_agent_s", name="Agent Arnaud",
            groups="base.group_user,sales_team.group_sale_salesman,whatsapp_cloud.group_whatsapp_user",
        )
        cls.account = cls.env["whatsapp.account"].create({
            "name": "My Shop",
            "phone_number_id": "1110001",
            "waba_id": "2220002",
            "access_token": "test-token",
            "resource_calendar_id": False,
            "agent_user_ids": [Command.set((cls.salesperson | cls.agent).ids)],
            "review_url": "https://g.page/r/my-shop/review",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Awa Ngono",
            "phone": "670000000",
            "country_id": cls.env.ref("base.cm").id,
            "whatsapp_opt_in": True,
            "lang": "en_US",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Sac à dos", "type": "consu", "list_price": 65000,
        })
        cls.Message = cls.env["whatsapp.message"]

    def _order(self, confirm=True, **values):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "user_id": self.salesperson.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            **values,
        })
        if confirm:
            order.action_confirm()
        return order

    def receive(self, body=None, wa_id="wamid.IN1", **data):
        message = {"from": "237670000000", "id": wa_id, "timestamp": "1760000000"}
        if body is not None:
            message.update(type="text", text={"body": body})
        message.update(data)
        return self.Message._process_incoming(
            self.account, message, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}]
        )

    def last_sent(self, channel):
        return self.Message.search([
            ("channel_id", "=", channel.id), ("direction", "=", "outgoing"),
        ], order="id desc", limit=1)

    def test_track_my_order_option(self):
        order = self._order()
        channel = self.receive("Bonjour").channel_id
        option = self.account.bot_option_ids.filtered(lambda o: o.action == "order_status")
        self.assertEqual(option.sequence, 1)
        menu = json.loads(self.last_sent(channel).payload)
        self.assertEqual(
            menu["interactive"]["action"]["buttons"][0]["reply"]["id"], option._get_reply_id()
        )
        self.receive(wa_id="wamid.IN2", type="interactive", interactive={
            "type": "button_reply",
            "button_reply": {"id": option._get_reply_id(), "title": option.name},
        })
        answer = self.last_sent(channel).body
        self.assertIn(order.name, answer)
        self.assertIn("confirmed, being prepared", answer)
        self.assertIn(f"/my/orders/{order.id}?access_token=", answer)
        self.assertFalse(channel.whatsapp_waiting_since)

    def test_order_reference_in_a_message(self):
        order = self._order()
        other_customer = self.env["sale.order"].create({
            "partner_id": self.env["res.partner"].create({"name": "Other"}).id,
            "order_line": [Command.create({"product_id": self.product.id})],
        })
        channel = self.receive("Bonjour").channel_id
        self.receive(f"Où en est ma commande {order.name} ?", wa_id="wamid.IN2")
        self.assertIn(order.name, self.last_sent(channel).body)
        # an order of another customer is never shown
        self.receive(f"Et la {other_customer.name} ?", wa_id="wamid.IN3")
        self.assertNotIn(other_customer.name, self.last_sent(channel).body)

    def test_no_order_goes_to_an_agent(self):
        channel = self.receive("Bonjour").channel_id
        self.receive("commande", wa_id="wamid.IN2")
        self.assertTrue(any("We find no order" in body for body in channel.message_ids.mapped("body")))
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        self.assertTrue(channel.whatsapp_waiting_since)

    def test_salesperson_gets_the_conversation(self):
        self.account.write({"assignment_mode": "salesperson", "bot_enabled": False})
        self._order()
        channel = self.receive("Bonjour").channel_id
        self.assertEqual(channel.whatsapp_user_id, self.salesperson)
        self.assertNotIn(self.agent.partner_id, channel.channel_member_ids.partner_id)

    def test_satisfaction_rating(self):
        order = self._order()
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking._action_done()
        template = self.env.ref("whatsapp_cloud_sale.template_delivery_feedback_en")
        feedback = template._send(picking)
        feedback.write({"state": "sent", "wa_message_id": "wamid.FEEDBACK"})
        channel = self.receive(
            wa_id="wamid.R1", type="button", button={"payload": "5 ⭐ Excellent", "text": "5 ⭐ Excellent"},
            context={"from": "237699000000", "id": "wamid.FEEDBACK"},
        ).channel_id
        rating = self.env["rating.rating"].search([("res_model", "=", "sale.order"), ("res_id", "=", order.id)])
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.partner_id, self.partner)
        self.assertIn("https://g.page/r/my-shop/review", self.last_sent(channel).body)
        # an unsatisfied customer goes to the team
        feedback.copy({"wa_message_id": "wamid.FEEDBACK2", "state": "sent"})
        self.receive(
            wa_id="wamid.R2", type="button", button={"payload": "2 ⭐ Disappointing", "text": "2 ⭐ Disappointing"},
            context={"from": "237699000000", "id": "wamid.FEEDBACK2"},
        )
        self.assertTrue(channel.whatsapp_waiting_since)
        self.assertTrue(any("Unsatisfied customer" in body for body in channel.message_ids.mapped("body")))

    def test_feedback_automation(self):
        rule = self.env.ref("whatsapp_cloud_sale.automation_delivery_feedback")
        self.assertEqual((rule.trigger, rule.trg_date_range, rule.trg_date_range_type),
                         ("on_time", 2, "day"))
        self.assertEqual(rule.action_server_ids.whatsapp_template_id,
                         self.env.ref("whatsapp_cloud_sale.template_delivery_feedback"))

    def test_send_quotation_in_the_conversation(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour, un devis pour 3 sacs ?").channel_id
        quotation = self._order(confirm=False)
        quotation.with_user(self.salesperson).action_whatsapp_send_quotation()
        sent = self.last_sent(channel)
        self.assertIn(quotation.name, sent.body)
        self.assertIn(f"/my/orders/{quotation.id}?access_token=", sent.body)
        self.assertEqual(sent.message_type, "text")
        self.assertEqual(quotation.state, "sent")
        self.assertEqual(channel.whatsapp_user_id, self.salesperson)

    def test_send_quotation_in_the_conversation_of_another_number(self):
        second = self.env["whatsapp.account"].create({
            "name": "Shop Yaoundé", "phone_number_id": "1110002", "waba_id": "2220002",
            "access_token": "test-token", "bot_enabled": False, "resource_calendar_id": False,
        })
        channel = self.Message._process_incoming(second, {
            "from": "237670000000", "id": "wamid.Y1", "timestamp": "1760000000",
            "type": "text", "text": {"body": "Un devis svp"},
        }, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}]).channel_id
        quotation = self._order(confirm=False)
        self.assertEqual(quotation._whatsapp_get_channel(), channel)
        quotation.with_user(self.salesperson).action_whatsapp_send_quotation()
        sent = self.last_sent(channel)
        self.assertEqual(sent.account_id, second)
        self.assertIn(quotation.name, sent.body)

    def test_send_quotation_with_template_after_24_hours(self):
        self.account.bot_enabled = False
        channel = self.receive("Bonjour").channel_id
        channel.whatsapp_last_inbound_date = fields.Datetime.now() - timedelta(days=2)
        quotation = self._order(confirm=False)
        action = quotation.action_whatsapp_send_quotation()
        self.assertEqual(action["res_model"], "whatsapp.composer")
        composer = self.env["whatsapp.composer"].with_context(action["context"]).create({})
        self.assertEqual(composer.template_id, self.env.ref("whatsapp_cloud_sale.template_quotation_sent"))

    def test_information_panel(self):
        order = self._order()
        channel = self.receive("Bonjour").channel_id
        info = channel.with_user(self.agent).whatsapp_get_info()
        orders = next(section for section in info["sections"] if section["title"] == "Orders")
        self.assertEqual(orders["items"][0]["name"], order.name)
        self.assertEqual(orders["buttons"][0]["method"], "whatsapp_action_new_quotation")
        action = channel.with_user(self.agent).whatsapp_action_new_quotation()
        self.assertEqual(action["context"]["default_partner_id"], self.partner.id)

    def test_order_placeholders(self):
        self.account.bot_enabled = False
        order = self._order()
        channel = self.receive("Bonjour").channel_id
        channel.with_user(self.agent).message_post(
            body="Votre commande {commande} : {lien_commande}", message_type="comment",
        )
        self.assertIn(order.name, self.last_sent(channel).body)
        self.assertIn(f"/my/orders/{order.id}", self.last_sent(channel).body)

    def test_order_on_whatsapp_link(self):
        website = self.env["website"].search([], limit=1)
        website.whatsapp_number = "+237 6 99 00 00 00"
        self.assertEqual(website._whatsapp_get_number(), "237699000000")
        self.assertEqual(
            website._whatsapp_get_link("Bonjour"), "https://wa.me/237699000000?text=Bonjour"
        )
        website.whatsapp_number = False
        self.account.display_phone_number = "+237 6 99 11 22 33"
        self.assertEqual(website._whatsapp_get_number(), "237699112233")

    # === SETTINGS === #

    def test_order_tracking_disabled(self):
        self.env.company.whatsapp_order_tracking = False
        order = self._order()
        channel = self.receive("Bonjour").channel_id
        option = self.account.bot_option_ids.filtered(lambda o: o.action == "order_status")
        self.assertNotIn(option._get_reply_id(), self.last_sent(channel).payload)
        self.receive(f"Où en est ma commande {order.name} ?", wa_id="wamid.IN2")
        self.assertNotIn(order.name, self.last_sent(channel).body or "")
        self.assertEqual(channel.whatsapp_bot_state, "agent")
        # the option of a menu sent before: handed over to the team
        channel.whatsapp_bot_state = "menu"
        self.receive(wa_id="wamid.IN3", type="interactive", interactive={
            "type": "button_reply",
            "button_reply": {"id": option._get_reply_id(), "title": option.name},
        })
        self.assertNotIn(order.name, self.last_sent(channel).body or "")
        self.assertEqual(channel.whatsapp_bot_state, "agent")

    def test_quotations_disabled(self):
        self.env.company.whatsapp_quotation = False
        quotation = self._order(confirm=False)
        self.assertFalse(quotation.whatsapp_quotation)
        with self.assertRaises(UserError):
            quotation.action_whatsapp_send_quotation()

    def test_rating_without_conversations(self):
        self.env.company.whatsapp_conversations = False
        order = self._order()
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking._action_done()
        template = self.env.ref("whatsapp_cloud_sale.template_delivery_feedback_en")
        template._send(picking).write({"state": "sent", "wa_message_id": "wamid.FEEDBACK"})
        message = self.receive(
            wa_id="wamid.R1", type="button", button={"payload": "4 ⭐ Good", "text": "4 ⭐ Good"},
            context={"from": "237699000000", "id": "wamid.FEEDBACK"},
        )
        self.assertFalse(message.channel_id)
        rating = self.env["rating.rating"].search([("res_model", "=", "sale.order"), ("res_id", "=", order.id)])
        self.assertEqual(rating.rating, 4)
        self.assertIn("4 ⭐ Good", picking.message_ids[0].body)
        self.assertFalse(self.Message.search([
            ("account_id", "=", self.account.id), ("direction", "=", "outgoing"),
            ("parent_id", "=", message.id),
        ]))

    def test_notification_settings(self):
        rule = self.env.ref("whatsapp_cloud_sale.automation_order_confirmed")
        rule.active = True
        settings = self.env["res.config.settings"].create({})
        self.assertTrue(settings.whatsapp_notify_order_confirmed)
        settings.whatsapp_notify_order_confirmed = False
        settings.set_values()
        self.assertFalse(rule.active)
        self.assertFalse(self.env["res.config.settings"].create({}).whatsapp_notify_order_confirmed)
        settings.whatsapp_notify_order_confirmed = True
        settings.set_values()
        self.assertTrue(rule.active)

    def test_shop_settings(self):
        website = self.env["website"].search([], limit=1)
        settings = self.env["res.config.settings"].create({"website_id": website.id})
        self.assertTrue(settings.website_whatsapp_order_button)
        settings.write({
            "website_whatsapp_order_button": False,
            "website_whatsapp_checkout_consent": False,
        })
        self.assertFalse(website.whatsapp_order_button)
        self.assertFalse(website.whatsapp_checkout_consent)

    # === SHOP OPTIONS === #

    def _option(self, action):
        option = self.account.with_context(active_test=False).bot_option_ids.filtered(
            lambda option: option.action == action
        )
        option.active = True
        return option

    def _choose(self, option_or_id, wa_id):
        reply_id = option_or_id if isinstance(option_or_id, str) else option_or_id._get_reply_id()
        return self.receive(wa_id=wa_id, type="interactive", interactive={
            "type": "list_reply", "list_reply": {"id": reply_id, "title": "-"},
        })

    def _menu_ids(self, channel):
        action = json.loads(self.last_sent(channel).payload)["interactive"]["action"]
        if "buttons" in action:
            return [button["reply"]["id"] for button in action["buttons"]]
        return [row["id"] for row in action["sections"][0]["rows"]]

    def test_pay_my_order(self):
        pay = self._option("pay")
        channel = self.receive("Bonjour").channel_id
        self.assertNotIn(pay._get_reply_id(), self._menu_ids(channel))  # nothing to pay
        quotation = self._order(confirm=False)
        quotation.action_quotation_sent()
        order = self._order()
        self.receive("menu", wa_id="wamid.IN2")
        self.assertIn(pay._get_reply_id(), self._menu_ids(channel))
        self._choose(pay, "wamid.IN3")
        answer = self.last_sent(channel).body
        for record in (quotation, order):
            self.assertIn(record.name, answer)
            self.assertIn(f"/my/orders/{record.id}?access_token=", answer)
        self.assertIn("payment_amount=", answer)
        self.assertIn("payment_token=", answer)

    def test_our_stores(self):
        if "opening_hours" not in self.env["stock.warehouse"]._fields:
            self.skipTest("Opening hours of the stores: module website_sale_collect")
        stores = self._option("stores")
        calendar = self.env["resource.calendar"].create({
            "name": "Boutique",
            "attendance_ids": [Command.clear()] + [Command.create({
                "dayofweek": str(day), "hour_from": 9, "hour_to": 19,
            }) for day in range(6)],
        })
        warehouse = self.env["stock.warehouse"].create({
            "name": "Bonapriso", "code": "TBP", "opening_hours": calendar.id,
            "partner_id": self.env["res.partner"].create({
                "name": "Bonapriso Store", "street": "Rue Njo-Njo", "city": "Douala",
                "phone": "+237 699 00 00 01", "partner_latitude": 4.0311, "partner_longitude": 9.6943,
            }).id,
        })
        delivery_product = self.env["product.product"].create({"name": "Retrait", "type": "service"})
        self.env["delivery.carrier"].create({
            "name": "Retrait en magasin", "delivery_type": "in_store", "product_id": delivery_product.id,
            "warehouse_ids": [Command.set(warehouse.ids)], "is_published": True,
        })
        channel = self.receive("Bonjour").channel_id
        self._choose(stores, "wamid.IN2")
        sent = self.Message.search([
            ("channel_id", "=", channel.id), ("direction", "=", "outgoing"),
        ], order="id")
        text = sent.filtered(lambda message: "Bonapriso Store" in (message.body or "")
                             and message.message_type == "text")
        self.assertIn("Rue Njo-Njo, Douala", text.body)
        self.assertIn("+237 699 00 00 01", text.body)
        self.assertIn("Monday – Saturday: 09:00 – 19:00", text.body)
        self.assertIn("Sunday: closed", text.body)
        location = sent.filtered(lambda message: message.message_type == "location"
                                 and "Bonapriso Store" in message.body)
        self.assertEqual(json.loads(location.payload)["location"], {
            "latitude": 4.0311, "longitude": 9.6943, "name": "Bonapriso Store",
            "address": "Rue Njo-Njo, Douala",
        })

    def _skip_without_districts(self):
        if "res.city.district" not in self.env:
            self.skipTest("Cities and districts of the delivery: module delivery_cameroon")

    def test_delivery_fees(self):
        self._skip_without_districts()
        fees = self._option("delivery_fees")
        city = self.env["res.city"].create({
            "name": "Kribi Test", "country_id": self.env.ref("base.cm").id,
        })
        beach, port = self.env["res.city.district"].create([
            {"name": "Plage Test", "city_id": city.id},
            {"name": "Port Test", "city_id": city.id},
        ])
        product = self.env["product.product"].create({"name": "Livraison Kribi", "type": "service"})
        self.env["delivery.carrier"].create([{
            "name": "Kribi zone plage", "delivery_type": "fixed", "product_id": product.id,
            "fixed_price": 1000, "district_ids": [Command.set(beach.ids)], "is_published": True,
            "free_over": True, "amount": 50000,
        }, {
            "name": "Kribi zone port", "delivery_type": "fixed", "product_id": product.id,
            "fixed_price": 1500, "district_ids": [Command.set(port.ids)], "is_published": True,
        }])
        channel = self.receive("Bonjour").channel_id
        self._choose(fees, "wamid.IN2")
        self.assertEqual(channel.whatsapp_bot_step, "delivery_city")
        self.receive("kribi test", wa_id="wamid.IN3")  # without accents nor capitals
        self.assertEqual(channel.whatsapp_bot_step, "delivery_district")
        self.assertIn("In which district of Kribi Test?", self.last_sent(channel).body)
        # few districts: they are the choices, and "Another district" to write it
        self.assertEqual(self._menu_ids(channel), [
            f"whatsapp_district_{beach.id}", f"whatsapp_district_{port.id}",
            "whatsapp_district_other",
        ])
        self.receive("plage test", wa_id="wamid.IN4")
        answer = self.last_sent(channel).body
        self.assertIn("Delivery to Plage Test, Kribi Test:", answer)
        self.assertIn("Kribi zone plage", answer)
        self.assertIn("free from", answer)
        self.assertNotIn("Kribi zone port", answer)
        self.assertFalse(channel.whatsapp_bot_step)
        self.assertFalse(channel.whatsapp_waiting_since)  # answered by the menu
        # unknown district: the zones of the city
        self._choose(fees, "wamid.IN5")
        self.receive("Kribi Test", wa_id="wamid.IN6")
        self.receive("Quartier inconnu", wa_id="wamid.IN7")
        answer = self.last_sent(channel).body
        self.assertIn("Quartier inconnu is not in our delivery zones of Kribi Test", answer)
        self.assertIn("Kribi zone plage", answer)
        self.assertIn("Kribi zone port", answer)
        # chosen in the list
        self._choose(fees, "wamid.IN71")
        self.receive("Kribi Test", wa_id="wamid.IN72")
        self._choose(f"whatsapp_district_{port.id}", "wamid.IN73")
        answer = self.last_sent(channel).body
        self.assertIn("Delivery to Port Test, Kribi Test:", answer)
        self.assertIn("Kribi zone port", answer)
        self.assertNotIn("Kribi zone plage", answer)
        # no more "write advisor": the choices to go on
        self.assertNotIn("advisor\"", answer)
        self.assertEqual(self._menu_ids(channel), ["whatsapp_menu", "whatsapp_handover"])
        # the question waits 2 hours for its answer at most
        self._choose(fees, "wamid.IN8")
        channel.whatsapp_bot_step_date = fields.Datetime.now() - timedelta(hours=3)
        self.receive("Kribi Test", wa_id="wamid.IN9")
        self.assertNotIn("district", self.last_sent(channel).body or "")
        self.assertEqual(channel.whatsapp_bot_state, "agent")

    def test_delivery_zones_of_a_big_city(self):
        self._skip_without_districts()
        fees = self._option("delivery_fees")
        city = self.env["res.city"].create({"name": "Grande Ville", "country_id": self.env.ref("base.cm").id})
        districts = self.env["res.city.district"].create([
            {"name": f"Quartier {index:02d}", "city_id": city.id} for index in range(12)
        ])
        product = self.env["product.product"].create({"name": "Livraison", "type": "service"})
        centre, periphery = self.env["delivery.carrier"].create([{
            "name": "Livraison Grande Ville – Centre", "delivery_type": "fixed",
            "product_id": product.id, "fixed_price": 1000, "is_published": True,
            "district_ids": [Command.set(districts[:6].ids)],
        }, {
            "name": "Livraison Grande Ville – Périphérie", "delivery_type": "fixed",
            "product_id": product.id, "fixed_price": 2500, "is_published": True,
            "district_ids": [Command.set(districts[6:].ids)],
        }])
        channel = self.receive("Bonjour").channel_id
        self._choose(fees, "wamid.IN2")
        self.receive("Grande Ville", wa_id="wamid.IN3")
        # too many districts: the zones, with their districts under their name
        rows = json.loads(self.last_sent(channel).payload)["interactive"]["action"]["sections"][0]["rows"]
        self.assertEqual([row["id"] for row in rows], [
            f"whatsapp_zone_{centre.id}", f"whatsapp_zone_{periphery.id}", "whatsapp_district_other",
        ])
        self.assertEqual([row["title"] for row in rows[:2]], ["Centre", "Périphérie"])
        self.assertTrue(rows[0]["description"].startswith("Quartier 00, Quartier 01"))
        self.assertLessEqual(len(rows[0]["description"]), 72)
        self._choose(f"whatsapp_zone_{periphery.id}", "wamid.IN4")
        answer = self.last_sent(channel).body
        self.assertIn("Delivery to Grande Ville (Périphérie):", answer)
        self.assertIn("Périphérie", answer)
        self.assertNotIn("– Centre", answer)
        # "Another district": written by the customer
        self._choose(fees, "wamid.IN5")
        self.receive("Grande Ville", wa_id="wamid.IN6")
        self._choose("whatsapp_district_other", "wamid.IN7")
        self.assertIn("Write the name of your district in Grande Ville.", self.last_sent(channel).body)
        self.receive("quartier 03", wa_id="wamid.IN8")
        self.assertIn("– Centre", self.last_sent(channel).body)

    def test_delivery_to_another_city(self):
        self._skip_without_districts()
        fees = self._option("delivery_fees")
        product = self.env["product.product"].create({"name": "Livraison", "type": "service"})
        douala = self.env["res.city"].search([("name", "=", "Douala")], limit=1) or self.env["res.city"].create(
            {"name": "Douala", "country_id": self.env.ref("base.cm").id}
        )
        self.env["delivery.carrier"].create([{
            "name": "Livraison à Douala", "delivery_type": "fixed", "product_id": product.id,
            "fixed_price": 1000, "is_published": True, "city_ids": [Command.set(douala.ids)],
        }, {
            "name": "Expédition autres villes", "delivery_type": "fixed", "product_id": product.id,
            "fixed_price": 3000, "is_published": True, "excluded_city_ids": [Command.set(douala.ids)],
        }])
        channel = self.receive("Bonjour").channel_id
        self._choose(fees, "wamid.IN2")
        self.assertIn("whatsapp_city_other", self._menu_ids(channel))
        # the other cities: answered at once, nothing to write
        self._choose("whatsapp_city_other", "wamid.IN3")
        answer = self.last_sent(channel).body
        self.assertIn("Delivery to the other cities:", answer)
        self.assertIn("Expédition autres villes", answer)
        self.assertNotIn("Livraison à Douala", answer)

    def test_answers_in_the_language_of_the_customer(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.partner.lang = "fr_FR"
        order = self._order()
        channel = self.receive("Bonjour").channel_id
        self.receive("commande", wa_id="wamid.IN2")
        self.assertIn("Votre commande :", self.last_sent(channel).body)
        self.assertIn(order.name, self.last_sent(channel).body)
        self._choose(self._option("delivery_fees"), "wamid.IN3")
        answer = self.last_sent(channel).body
        # the question of the city, or the fees at once when they do not depend on the city
        self.assertTrue("Où faut-il livrer ?" in answer or "Les frais exacts" in answer, answer)
