from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.modules.module import load_script
from odoo.tests import tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon
from odoo.addons.ocd_live_shop.tests.test_delivery_rates import OcdRatesCommon
from odoo.addons.whatsapp_cloud.models.whatsapp_template import AUTHENTICATION_RE, WhatsappTemplate


@tagged("post_install", "-at_install")
class TestOcdParcelMessages(OcdShopCommon):

    def test_messages_of_a_parcel(self):
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        with patch.object(WhatsappTemplate, "_send", fake_send):
            order = self._order(self.estelle, [(self.butter, 1)])
            parcel = order.picking_ids
            parcel.action_ocd_ready()
            parcel.action_ocd_leave()
            parcel._ocd_report_problem("unreachable")
            parcel.action_ocd_retry()
            parcel.action_ocd_leave()
            parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        # whatsapp_cloud_sale also sends its own message of the confirmed order
        names = [name for name, _records in calls if name.startswith("ocd_")]
        self.assertEqual(names, [
            "ocd_colis_a_preparer",
            "ocd_colis_en_route",
            "ocd_colis_echec",
            "ocd_colis_en_route",
            "ocd_colis_livre",
        ])

    def test_code_is_behind_the_button(self):
        """Meta refuses a code in a Utility template: the message has no code, its button opens
        the page that follows the order, where the customer reads it."""
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        with patch.object(WhatsappTemplate, "_send", lambda template, records: template.env["whatsapp.message"]):
            parcel.action_ocd_leave()
        template = self.env.ref("ocd_live_shop_whatsapp.template_parcel_on_the_way")
        self.assertNotIn("{{4}}", template.body)
        self.assertFalse(template.variable_ids.filtered(lambda v: v.sequence == 4))
        for variable in template.variable_ids:
            self.assertNotEqual(template._render(variable.value, parcel)[parcel.id], parcel.sudo().ocd_delivery_code)
        self.assertEqual(template.button_ids.name, "Suivre mon colis")
        path = template._render(template.button_url_value, parcel)[parcel.id]
        self.assertEqual(path, f"ocd/suivi/{order.id}?access_token={order.access_token}")

    def test_migration_puts_the_code_behind_the_button(self):
        """A database installed before has the refused text with the code and no button, still
        waiting in Odoo (no webhook): the migration gives the new text and the button."""
        xmlid = "ocd_live_shop_whatsapp.template_parcel_on_the_way"
        template = self.env.ref(xmlid)
        new_text = template.body
        migration = load_script(
            "ocd_live_shop_whatsapp/migrations/20.0.1.5.0/post-migration.py", "ocd_shop_whatsapp_texts_20_0_1_5_0"
        )
        template.write({
            "body": migration.OLD_TEXTS[xmlid][0], "button_ids": [Command.clear()],
            "button_url_value": False, "status": "pending",
        })
        template.variable_ids.filtered(lambda v: v.sequence == 4).value = "{{ object.ocd_delivery_code }}"
        migration.migrate(self.env.cr, "20.0.1.4.0")
        self.env.invalidate_all()
        self.assertEqual(template.body, new_text)
        self.assertEqual(template.button_ids.mapped("name"), ["Suivre mon colis"])
        self.assertEqual(template.button_url_value, "{{ object._ocd_tracking_path() }}")
        self.assertEqual(sorted(template.variable_ids.mapped("sequence")), [1, 2, 3])

    def test_texts_refused_as_incorrect_category(self):
        """Meta refused « colis en route » as INCORRECT_CATEGORY: a code named in a Utility
        template is taken for an authentication message, like a link « to keep for yourself ».
        The migration gives the new texts (French and English) to the refused templates; an
        approved one keeps its text, the one Meta sends."""
        migration = load_script(
            "ocd_live_shop_whatsapp/migrations/20.0.1.7.0/post-migration.py", "ocd_shop_whatsapp_texts_20_0_1_7_0"
        )
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "https://ocd.example.com")
        templates = {xmlid: self.env.ref(xmlid) for xmlid in migration.OLD_TEXTS}
        texts = {xmlid: template.body for xmlid, template in templates.items()}
        for xmlid, template in templates.items():
            self.assertIsNone(AUTHENTICATION_RE.search(texts[xmlid]), xmlid)
            template._check_for_meta()
            template.write({"body": migration.OLD_TEXTS[xmlid][0], "status": "rejected"})
        approved = templates["ocd_live_shop_whatsapp.template_parcel_failed_en"]
        approved.status = "approved"
        migration.migrate(self.env.cr, "20.0.1.6.0")
        self.env.invalidate_all()
        for xmlid, template in templates.items():
            with self.subTest(template=xmlid):
                expected = migration.OLD_TEXTS[xmlid][0] if template == approved else texts[xmlid]
                self.assertEqual(template.body, expected)
        on_the_way = templates["ocd_live_shop_whatsapp.template_parcel_on_the_way"]
        self.assertEqual(on_the_way.button_ids.name, "Suivre mon colis", "The code stays behind the button")

    def test_delivery_login_asks_a_code_while_the_link_is_refused(self):
        Partner = self.env["res.partner"]
        link = self.env.ref("ocd_live_shop_whatsapp.template_delivery_link")
        code = self.env.ref("ocd_live_whatsapp.template_login_code")
        code.status = "approved"
        self.assertTrue(Partner._ocd_link_login_ready("livrer"))
        link.status = "rejected"
        self.assertFalse(Partner._ocd_link_login_ready("livrer"))
        self.assertTrue(Partner._ocd_link_login_ready("space"), "The page of the vendors has its own link")

    def test_message_when_the_vendor_goes_live(self):
        Follower = self.env["ocd.vendor.follower"]
        follower = Follower._ocd_follow(self.brenda, Follower._ocd_contact("+228 90112233"))
        follower.followed_at = fields.Datetime.now() - timedelta(days=1)
        later = self.company._ocd_local_today() + timedelta(days=30)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": self.brenda.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "remote",
        })
        booking.state = "confirmed"
        now = fields.Datetime.now()
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [now - timedelta(minutes=5), now + timedelta(minutes=85), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        with patch.object(WhatsappTemplate, "_send", fake_send):
            self.env["ocd.boutique.alert"]._ocd_send_due()
        self.assertEqual(calls, [("ocd_vendeur_en_live", follower)])
        self.assertTrue(follower.live_told_at)
        template = self.env.ref("ocd_live_shop_whatsapp.template_vendor_live")
        rendered = template._render(template.variable_ids.value, follower)
        self.assertEqual(rendered[follower.id], "Brenda Wax")
        url = template._render(template.button_url_value, follower)[follower.id]
        self.assertEqual(url, f"ocd/abonne/{follower.id}/{follower.sudo().access_token}")
        # Following is the consent to these messages, never after STOP
        self.assertTrue(follower.partner_id.whatsapp_opt_in)
        stopped = Follower._ocd_contact("+228 90112244")
        stopped.write({"whatsapp_opt_out": True, "ocd_whatsapp_optin": False})
        Follower._ocd_follow(self.brenda, stopped)
        self.assertFalse(stopped.ocd_whatsapp_optin)

    def _deliver(self, parcel):
        if parcel.ocd_stage == "to_prepare":
            parcel.action_ocd_ready()
        if parcel.ocd_delivery_mode != "vendor" and parcel.ocd_stage == "ready":
            parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)

    def test_shop_messages_not_doubled_for_the_parcels(self):
        """"Order shipped" of the shop goes when a transfer is validated, i.e. when a parcel is
        delivered: not for the parcels, which have their own messages. The satisfaction message
        goes once per order, after its last parcel."""
        Template = self.env["whatsapp.template"]
        shipped = Template.new({"template_name": "order_shipped"})
        feedback = Template.new({"template_name": "delivery_feedback"})
        order = self._order(self.estelle, [(self.butter, 1), (self.dress, 1)])
        parcels = order.picking_ids
        self.assertEqual(len(parcels), 2, "One parcel per vendor")
        first, second = parcels.sorted("id")
        self._deliver(first)
        self.assertEqual(first.state, "done")
        self.assertFalse(parcels._ocd_whatsapp_keep(shipped))
        self.assertFalse(parcels._ocd_whatsapp_keep(feedback), "A parcel is still on its way")
        self._deliver(second)
        self.assertEqual(parcels._ocd_whatsapp_keep(feedback), second)
        other = Template.new({"template_name": "ocd_colis_livre"})
        self.assertEqual(parcels._ocd_whatsapp_keep(other), parcels)


@tagged("post_install", "-at_install")
class TestOcdCollectMessages(OcdRatesCommon):
    """Pick up in a store (chantier 20): the customer is told when it is ready, the day before
    the end, and when it is cancelled; the code stays behind the button."""

    def test_messages_of_a_parcel_picked_up_at_the_store(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                            "ocd_place_proof_required": False, "ocd_store_pickup": True, "ocd_collect_days": 3})
        self.dress.is_storable = True
        store = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": self.akwa.id, "city_id": self.douala.id,
        })
        store._ocd_set_hours(self.company._ocd_place_default_intervals())
        self.dress._ocd_change_stock(3)
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        with patch.object(WhatsappTemplate, "_send", fake_send):
            order = self._cart(self.estelle, [(self.dress, 1)])
            order._ocd_set_collect_places(store)
            order.set_delivery_line(self.carrier_ocd, self.carrier_ocd.rate_shipment(order)["price"])
            order.action_confirm()
            parcel = order.picking_ids.filtered("ocd_is_parcel")
            parcel.action_ocd_collect_ready()
            parcel.ocd_collect_deadline = fields.Datetime.now() + timedelta(hours=5)
            self.env["stock.picking"]._cron_ocd_collect()
            parcel.ocd_collect_deadline = fields.Datetime.now() - timedelta(minutes=5)
            self.env["stock.picking"]._cron_ocd_collect()
        names = [name for name, _records in calls if name.startswith("ocd_")]
        self.assertEqual(names, ["ocd_colis_a_preparer_magasin", "ocd_colis_pret_magasin", "ocd_colis_rappel_magasin",
                                 "ocd_colis_non_retire"])
        template = self.env.ref("ocd_live_shop_whatsapp.template_parcel_collect_ready")
        values = [template._render(variable.value, parcel)[parcel.id] for variable in template.variable_ids.sorted("sequence")]
        self.assertEqual(values[2], "Brenda Wax Akwa")
        self.assertRegex(values[3], r"^(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche) \d+ \w+ \S+ \d\d:\d\d$")
        self.assertNotIn(parcel.sudo().ocd_delivery_code, values)
        self.assertEqual(template.button_ids.name, "Ma commande")
        english = self.env.ref("ocd_live_shop_whatsapp.template_parcel_collect_ready_en")
        self.assertRegex(english._render(english.variable_ids.sorted("sequence")[3].value, parcel)[parcel.id],
                         r"^[A-Z][a-z]+day \d+ [A-Z][a-z]+ at \d\d:\d\d$")


@tagged("post_install", "-at_install")
class TestOcdHoldMessages(OcdShopCommon):
    """Hold a piece to try (chantier 20): the vendor is told, then the customer gets the answer."""

    def test_messages_of_a_piece_held(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                            "ocd_place_proof_required": False, "ocd_hold_enabled": True})
        self.brenda.country_id = self.env.ref("base.cm")
        self.dress.is_storable = True
        self.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        store = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": self.akwa.id, "city_id": self.akwa.city_id.id,
        })
        store._ocd_set_hours(self.company._ocd_place_default_intervals())
        self.dress._ocd_change_stock(2)
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        Hold = self.env["ocd.product.hold"]
        with patch.object(WhatsappTemplate, "_send", fake_send):
            hold = Hold._ocd_request(store, self.dress, self.estelle)
            hold.action_ocd_accept()
            hold.action_ocd_outcome("not_taken")
            Hold._ocd_request(store, self.dress, self.estelle).action_ocd_refuse()
        self.assertEqual([name for name, _records in calls],
                         ["ocd_essai_demande", "ocd_essai_garde", "ocd_essai_demande", "ocd_essai_refuse"])
        template = self.env.ref("ocd_live_shop_whatsapp.template_hold_requested")
        values = [template._render(variable.value, hold)[hold.id] for variable in template.variable_ids.sorted("sequence")]
        self.assertEqual(values[3], "Brenda Wax Akwa")
        self.assertEqual(values[4], hold._ocd_deadline_text("fr_FR"), "In French, the language of the template")
        self.assertIn("?vue=essayer", template._render(template.button_url_value, hold)[hold.id])
        accepted = self.env.ref("ocd_live_shop_whatsapp.template_hold_accepted")
        self.assertEqual(accepted._render(accepted.button_url_value, hold)[hold.id], hold._ocd_page_path())


@tagged("post_install", "-at_install")
class TestOcdLowStockMessage(OcdShopCommon):
    """Low stock (chantier 21): the vendor is told how many pieces are left."""

    def test_message_of_low_stock(self):
        self.company.ocd_low_stock_threshold = 2
        self.dress.product_tmpl_id.write({"is_storable": True, "allow_out_of_stock_order": False})
        self.dress._ocd_change_stock(3)
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records, template.env.context.get("ocd_low_qty")))
            return template.env["whatsapp.message"]

        with patch.object(WhatsappTemplate, "_send", fake_send):
            self._order(self.estelle, [(self.dress, 2)])
        product = self.dress.product_tmpl_id
        self.assertIn(("ocd_stock_bas", product, 1), calls)
        template = self.env.ref("ocd_live_shop_whatsapp.template_stock_low").with_context(
            ocd_low_qty=1, ocd_low_name=self.dress.display_name)
        values = [template._render(variable.value, product)[product.id] for variable in template.variable_ids.sorted("sequence")]
        self.assertEqual(values, [self.brenda.name, "1", self.dress.display_name], "The choice and its pieces")
        self.assertEqual(template._get_recipient(product), self.brenda)
        self.assertIn("/produits", template._render(template.button_url_value, product)[product.id])

    def test_migration_gives_the_values_of_the_choice(self):
        """A database installed before: the template keeps its values; the migration makes it read
        the pieces and the choice of the sending, and removes a second template of the same name."""
        from odoo.modules.module import load_script
        template = self.env.ref("ocd_live_shop_whatsapp.template_stock_low")
        template.variable_ids.filtered(lambda v: v.sequence == 2).value = "{{ object._ocd_free_total() }}"
        template.variable_ids.filtered(lambda v: v.sequence == 3).value = "{{ object.name }}"
        load_script("ocd_live_shop_whatsapp/migrations/20.0.1.21.0/post-migration.py",
                    "ocd_shop_whatsapp_low_stock_20_0_1_21_0").migrate(self.env.cr, "20.0.1.20.0")
        self.env.invalidate_all()
        self.assertIn("ocd_low_qty", template.variable_ids.filtered(lambda v: v.sequence == 2).value)
        self.assertIn("ocd_low_name", template.variable_ids.filtered(lambda v: v.sequence == 3).value)


@tagged("post_install", "-at_install")
class TestOcdTeamMessages(OcdShopCommon):
    """The team of a vendor (chantier 22): her link when she is added, then the news of her store
    (a parcel to prepare, a piece to try) when she agreed to them; nothing while the team is
    paused."""

    def test_messages_of_the_team(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                            "ocd_place_proof_required": False, "ocd_hold_enabled": True, "ocd_vendor_team_max": 5})
        self.brenda.country_id = self.env.ref("base.cm")
        self.dress.is_storable = True
        self.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        store = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": self.akwa.id, "city_id": self.akwa.city_id.id,
        })
        store._ocd_set_hours(self.company._ocd_place_default_intervals())
        self.brenda.ocd_departure_place_id = store
        self.dress._ocd_change_stock(3)
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records, dict(template.env.context)))
            return template.env["whatsapp.message"]

        Member = self.env["ocd.vendor.member"]
        with patch.object(WhatsappTemplate, "_send", fake_send):
            aicha = Member._ocd_add(self.brenda, "Aïcha Njoya", "+237699123456", store)
            self.assertEqual([(name, records) for name, records, _ctx in calls], [("ocd_equipe_lien", aicha)])
            self.assertTrue(calls[0][2]["ocd_whatsapp_requested"], "Her link: sent even without the consent")
            # The news of her store: when she agreed to them
            aicha.partner_id.ocd_whatsapp_optin = True
            calls.clear()
            order = self._order(self.estelle, [(self.dress, 1)])
            parcel = order.picking_ids.filtered(lambda p: p.ocd_vendor_id == self.brenda)
            self.assertEqual(parcel.ocd_pickup_place_id, store)
            team = [(name, records, ctx) for name, records, ctx in calls if records == aicha]
            self.assertEqual([(name, ctx["ocd_customer"]) for name, _r, ctx in team], [("ocd_equipe_colis", "Estelle")])
            calls.clear()
            hold = self.env["ocd.product.hold"]._ocd_request(store, self.dress, self.herve)
            team = [(name, ctx) for name, records, ctx in calls if records == aicha]
            self.assertEqual([name for name, _ctx in team], ["ocd_equipe_essai"])
            self.assertEqual(team[0][1]["ocd_until_fr"], hold._ocd_deadline_text("fr_FR"))
            # Paused (no more OCD Business): nothing to her
            self.company.ocd_business_offered_all = False
            calls.clear()
            self._order(self.estelle, [(self.dress, 1)])
            self.assertFalse([records for _name, records, _ctx in calls if records == aicha])
        template = self.env.ref("ocd_live_shop_whatsapp.template_team_link")
        values = [template._render(variable.value, aicha)[aicha.id] for variable in template.variable_ids.sorted("sequence")]
        self.assertEqual(values, ["Aïcha", "Brenda Wax", "Brenda Wax Akwa"])
        self.assertEqual(template._render(template.button_url_value, aicha)[aicha.id],
                         f"ocd/mon-magasin/{aicha.partner_id._ocd_get_space_token()}")
        self.assertEqual(template._get_recipient(aicha), aicha.partner_id)
        parcel_template = self.env.ref("ocd_live_shop_whatsapp.template_team_parcel")
        self.assertTrue(parcel_template._render(parcel_template.button_url_value, aicha)[aicha.id].endswith("?vers=colis"))
        # Her login page sends this link in the link mode
        self.assertEqual(self.env["res.partner"]._ocd_link_templates()["magasin"], "ocd_live_shop_whatsapp.template_team_link")


@tagged("post_install", "-at_install")
class TestOcdFollowerMessages(OcdShopCommon):
    """Follow a vendor (chantier 1): the news of the vendor to the followers who want them
    (A.8, Marketing at Meta)."""

    def test_message_of_the_news(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.company.write({"ocd_business_offered_all": True, "ocd_news_weekday": "4"})
        self.brenda.country_id = self.env.ref("base.cm")
        self.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved",
                                         "ocd_review_date": fields.Datetime.now() - timedelta(days=1)})
        Follower = self.env["ocd.vendor.follower"]
        follower = Follower._ocd_follow(self.brenda, Follower._ocd_contact("+237 670000011"))
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records, dict(template.env.context)))
            return template.env["whatsapp.message"]

        friday = fields.Datetime.now()
        while friday.weekday() != 4:
            friday += timedelta(days=1)
        friday = friday.replace(hour=9, minute=30)  # 10:30 in Douala
        with patch.object(WhatsappTemplate, "_send", fake_send):
            Follower._ocd_send_news(friday)
        self.assertEqual([(name, records) for name, records, _ctx in calls], [("ocd_vendeur_nouveautes", follower)])
        self.assertEqual(calls[0][2]["ocd_news_fr"], "Robe en wax")
        self.assertFalse(calls[0][2]["ocd_whatsapp_requested"], "STOP stops them like the others")
        template = self.env.ref("ocd_live_shop_whatsapp.template_vendor_news").with_context(ocd_news_fr="Robe en wax")
        self.assertEqual(template.category, "marketing")
        values = [template._render(variable.value, follower)[follower.id] for variable in template.variable_ids.sorted("sequence")]
        self.assertEqual(values, ["Brenda Wax", "Robe en wax"])
        self.assertTrue(template._render(template.button_url_value, follower)[follower.id].endswith("?vers=nouveautes"))
        self.assertEqual(template._get_recipient(follower), follower.partner_id)
