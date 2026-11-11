import re
from datetime import datetime, time, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.modules.module import load_script
from odoo.tests import TransactionCase, tagged

from odoo.addons.ocd_live.tests.common import OcdLiveCommon
from odoo.addons.ocd_live_whatsapp.hooks import restore_english_templates
from odoo.addons.whatsapp_cloud.models.whatsapp_template import PLACEHOLDER_RE, WhatsappTemplate


@tagged("post_install", "-at_install")
class TestOcdLiveWhatsapp(OcdLiveCommon):

    def _capture(self):
        """Patch the sending of the templates: return the list of (template, records, context)."""
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records, dict(template.env.context)))
            return template.env["whatsapp.message"].new({"state": "queued"})

        return calls, patch.object(WhatsappTemplate, "_send", fake_send)

    def test_login_code_and_links_are_sent(self):
        calls, patcher = self._capture()
        with patcher:
            self.assertTrue(self.vendor._ocd_send_login_code())
            self.vendor._ocd_send_space_link()
            self.vendor._ocd_send_access_link("https://ocd.example/web/reset_password?token=x")
        names = [call[0] for call in calls]
        self.assertEqual(names, ["ocd_code_connexion", "ocd_lien_espace", "ocd_mot_de_passe"])
        code = calls[0][2]["ocd_login_code"]
        self.assertTrue(self.vendor._ocd_check_login_code(code), "The code sent is the code checked")

    def test_english_version_speaks_english(self):
        self.env["res.lang"]._activate_lang("en_US")
        booking = self._book(self.starts[0], mode="remote")
        ticket = self.env.ref("ocd_live_whatsapp.template_ticket_en")
        values = {variable.sequence: ticket._render(variable.value, booking)[booking.id] for variable in ticket.variable_ids}
        self.assertEqual(values[5], "remotely")
        days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        self.assertTrue(values[2].startswith(days), values[2])
        self.assertEqual(values[6], booking.ticket_code)

    def test_live_confirmed_then_reminded(self):
        calls, patcher = self._capture()
        booking = self._book(self.starts[0], mode="remote")
        # The studio is in Lome: its time is the UTC time
        evening_before = datetime.combine(self.day - timedelta(days=1), time(19, 0))
        with patcher:
            booking._ocd_confirm()
            self.assertEqual(calls[-1][0], "ocd_live_confirme")
            self.assertEqual(calls[-1][1], booking)
            with freeze_time(evening_before - timedelta(hours=3)):
                self.env["ocd.live.booking"]._cron_send_reminders()
            self.assertFalse(booking.ocd_reminder_sent, "Not before 18:00 the day before")
            with freeze_time(evening_before):
                self.env["ocd.live.booking"]._cron_send_reminders()
        self.assertTrue(booking.ocd_reminder_sent)
        self.assertEqual(calls[-1][0], "ocd_rappel_live")

    def test_directory_messages(self):
        calls, patcher = self._capture()
        listing = self.env["ocd.directory.listing"].create({
            "partner_id": self.vendor.id,
            "url": "https://www.tiktok.com/@awa/live",
            "state": "to_check",
            "window_end": fields.Datetime.now() + timedelta(hours=2),
        })
        with patcher:
            listing.action_publish()
            listing._ocd_refuse(self.env.ref("ocd_live.refuse_reason_broken"))
        self.assertEqual([call[0] for call in calls], ["ocd_lien_en_ligne", "ocd_lien_refuse"])

    def test_templates_render(self):
        """The variables of the templates render on real records."""
        template = self.env.ref("ocd_live_whatsapp.template_live_confirmed")
        booking = self._book(self.starts[3])
        for variable in template.variable_ids:
            rendered = template._render(variable.value, booking)
            self.assertTrue(rendered[booking.id], variable.value)
        code_template = self.env.ref("ocd_live_whatsapp.template_login_code").with_context(ocd_login_code="654321")
        rendered = code_template._render(code_template.variable_ids.value, self.vendor)
        self.assertEqual(rendered[self.vendor.id], "654321")

    # === NEW MESSAGES === #

    def test_ticket_free_hour_and_directory_alerts(self):
        calls, patcher = self._capture()
        booking = self._book(self.starts[0])
        booking._ocd_confirm()
        Waitlist = self.env["ocd.live.waitlist"]
        entry = Waitlist._ocd_register("+228 90 00 00 31", self.day, "studio")
        window_start = fields.Datetime.now() - timedelta(minutes=1)
        alert = self.env["ocd.directory.alert"].create({"partner_id": self.vendor.id, "window_start": window_start})
        with patcher:
            self.assertTrue(booking._ocd_send_ticket(), "The ticket page tells it is on its way")
            Waitlist._ocd_notify_free(self.company, self.day, "studio")
            self.env["ocd.directory.alert"]._ocd_send_due()
        names = [call[0] for call in calls]
        self.assertEqual(names, ["ocd_ticket_live", "ocd_creneau_libre", "ocd_annuaire_ouvert"])
        self.assertTrue(all(call[2].get("ocd_whatsapp_requested") for call in calls), "Asked by the contact")
        self.assertEqual(entry.state, "notified")
        self.assertEqual(alert.state, "sent")

    def test_link_received_out_of_the_windows(self):
        self._sell(self.pass_product)
        calls, patcher = self._capture()
        day = fields.Date.today() + timedelta(days=1)
        with patcher, freeze_time(datetime.combine(day, time(12, 0))):
            listing = self.env["ocd.directory.listing"]._ocd_submit(self.vendor, "https://www.tiktok.com/@awa/live")
            self.assertEqual(listing.state, "queued")
            self.assertEqual(listing._ocd_window_start_label(), "18:00", "The studio is in Lome: UTC")
        self.assertEqual([call[0] for call in calls], ["ocd_lien_recu"])
        self.assertFalse(calls[0][2].get("ocd_whatsapp_requested"))

    def test_new_templates_render(self):
        booking = self._book(self.starts[1])
        booking._ocd_confirm()
        entry = self.env["ocd.live.waitlist"]._ocd_register("+228 90 00 00 32", self.day, "remote")
        alert = self.env["ocd.directory.alert"].create({
            "partner_id": self.vendor.id,
            "window_start": datetime.combine(self.day, time(18, 0)),
        })
        listing = self.env["ocd.directory.listing"].create({
            "partner_id": self.vendor.id,
            "url": "https://www.tiktok.com/@awa/live",
            "window_start": datetime.combine(self.day, time(18, 0)),
            "window_end": datetime.combine(self.day, time(21, 0)),
        })
        for xmlid, record in (
            ("template_ticket", booking), ("template_free_slot", entry),
            ("template_window_open", alert), ("template_link_received", listing),
        ):
            template = self.env.ref(f"ocd_live_whatsapp.{xmlid}")
            for variable in template.variable_ids:
                self.assertTrue(template._render(variable.value, record)[record.id], f"{xmlid}: {variable.value}")
            self.assertTrue(template._render(template.button_url_value, record)[record.id] if template.button_url_value else True)
        self.assertEqual(booking._ocd_ticket_path(), f"ocd/ticket/{booking.id}", "No order, no secret")
        booking.sale_order_id = self.env["sale.order"].create({"partner_id": self.vendor.id})
        path = booking._ocd_ticket_path()
        self.assertEqual(path, f"ocd/ticket/{booking.id}?access_token={booking.sale_order_id.access_token}")
        self.assertEqual(entry._ocd_booking_path(), f"reserver/remote/{self.day:%Y-%m-%d}")
        self.assertEqual(alert._ocd_window_end_label(), "21:00")


@tagged("post_install", "-at_install")
class TestOcdWhatsappConsent(OcdLiveCommon):
    """One consent for OCD Live and WhatsApp; the messages asked by the contact go anyway."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live",
            "phone_number_id": "1110001",
            "waba_id": "2220002",
            "access_token": "test-token",
            "app_secret": "test-secret",
            "verify_token": "test-verify-token",
            "require_opt_in": True,
        })

    def _messages(self, template_name):
        return self.env["whatsapp.message"].search([("template_id.template_name", "=", template_name)])

    def test_one_consent(self):
        vendor = self.vendor
        self.assertFalse(vendor.whatsapp_opt_in, "Never asked")
        self.assertFalse(vendor._ocd_whatsapp_consent(), "The account requires the consent")
        vendor.ocd_whatsapp_optin = True
        self.assertTrue(vendor.whatsapp_opt_in, "The box of OCD Live is the consent of WhatsApp")
        self.assertTrue(vendor._ocd_whatsapp_consent())
        vendor._whatsapp_apply_subscription_keyword("STOP")
        self.assertFalse(vendor.ocd_whatsapp_optin, "STOP switches off the messages of OCD Live")
        self.assertTrue(vendor._ocd_whatsapp_refused())
        vendor._whatsapp_apply_subscription_keyword("START")
        self.assertTrue(vendor.ocd_whatsapp_optin)
        vendor.ocd_whatsapp_optin = False
        self.assertTrue(vendor.whatsapp_opt_out, "The switch of the vendor space is a refusal")
        partner = self.env["res.partner"].create({"name": "Ama", "phone": "+228 90 00 00 41", "ocd_whatsapp_optin": True})
        self.assertTrue(partner.whatsapp_opt_in, "A box ticked in a form of OCD Live")

    def test_asked_messages_go_without_consent(self):
        vendor = self.vendor
        self.assertTrue(vendor._ocd_send_login_code(), "The vendor asked for the code")
        self.assertEqual(self._messages("ocd_code_connexion").state, "queued")
        booking = self._book(self.starts[2])
        self.assertFalse(
            self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_live_confirmed", booking),
            "A notification without consent is not on its way",
        )
        skipped = self._messages("ocd_live_confirme")
        self.assertEqual(skipped.state, "skipped", "Kept with its reason for the team")
        vendor.ocd_whatsapp_optin = True
        self.assertTrue(self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_live_confirmed", booking))

    def test_refused_contacts_get_no_notification(self):
        vendor = self.vendor
        vendor.ocd_whatsapp_optin = False
        booking = self._book(self.starts[3])
        self.assertFalse(self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_live_confirmed", booking))
        self.assertFalse(self._messages("ocd_live_confirme"), "Not even queued")
        self.assertTrue(vendor._ocd_send_space_link(), "A link asked by the vendor still goes")

    def test_alignment_at_installation(self):
        from odoo.addons.ocd_live_whatsapp.hooks import align_whatsapp_consent

        refused = self.env["res.partner"].create({"name": "Kossi", "phone": "+228 90 00 00 42"})
        # Written as before this module: only on the field of OCD Live
        self.env.cr.execute("UPDATE res_partner SET ocd_whatsapp_optin = FALSE WHERE id = %s", [refused.id])
        refused.invalidate_recordset()
        align_whatsapp_consent(self.env)
        self.assertTrue(refused.whatsapp_opt_out)
        self.assertTrue(self.vendor.whatsapp_opt_in, "The vendors agreed through OCD Live")


@tagged("post_install", "-at_install")
class TestOcdWhatsappSettingsPage(OcdLiveCommon):

    def test_whatsapp_section(self):
        Page = self.env["ocd.live.settings"]
        section = Page._ocd_section_whatsapp()
        items = {item["key"]: item for item in section["items"]}
        self.assertTrue(items["wa_require_opt_in"]["readonly"], "No account yet: nothing to change")
        account = self.env["whatsapp.account"].create({
            "name": "OCD Live",
            "phone_number_id": "1110009",
            "waba_id": "2220009",
            "access_token": "test-token",
            "app_secret": "test-secret",
            "verify_token": "test-verify",
        })
        result = Page.save_settings_page({"wa_require_opt_in": False, "wa_welcome_menu": False})
        self.assertTrue(result["ok"], result)
        self.assertFalse(account.require_opt_in)
        self.assertFalse(account.bot_enabled)
        rows = {row["name"]: row for row in items["wa_templates"]["rows"]}
        self.assertIn("ocd_ticket_live", rows)
        self.assertIn("ocd_creneau_libre", rows)
        self.assertEqual(rows["ocd_ticket_live"]["tone"], "grey", "Not synchronised with Meta yet")


@tagged("post_install", "-at_install")
class TestOcdWhatsappAutomations(OcdLiveCommon):

    def test_paused_automation_sends_nothing(self):
        calls = []

        def fake_send(template, records):
            calls.append(template.template_name)
            return template.env["whatsapp.message"].new({"state": "queued"})

        automation = self.env.ref("ocd_live_whatsapp.automation_free_slot")
        automation.enabled = False
        with patch.object(WhatsappTemplate, "_send", fake_send):
            Waitlist = self.env["ocd.live.waitlist"]
            Waitlist._ocd_register("+228 90 00 00 51", self.day, "studio")
            Waitlist._ocd_notify_free(self.company, self.day, "studio")
            self.assertFalse(calls, "Paused by the team")
            self.assertTrue(self.vendor._ocd_send_login_code(), "A locked automation always goes")
        self.assertEqual(calls, ["ocd_code_connexion"])

    def test_template_waiting_for_meta_is_told(self):
        automation = self.env.ref("ocd_live_whatsapp.automation_link_received")
        automation.template_ids.status = "pending"
        row = automation._ocd_row()
        self.assertIn("ocd_lien_recu", row["warning"])
        self.assertEqual(row["templates"], ["ocd_lien_recu"])


@tagged("post_install", "-at_install")
class TestOcdTemplatesForMeta(TransactionCase):

    def test_templates_of_the_modules_follow_meta(self):
        """Every template given by a module (OCD Live, shop, sale) is submitted to Meta as it
        is: no variable at the start or at the end, words between two variables."""
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "https://ocd.example.com")
        data = self.env["ir.model.data"].search([("model", "=", "whatsapp.template")])
        self.assertGreater(len(data), 20)
        for xmlid in data:
            template = self.env["whatsapp.template"].browse(xmlid.res_id)
            with self.subTest(template=xmlid.complete_name):
                template._check_for_meta()
                if template.category == "authentication":
                    continue
                # Meta also refuses a text with too many variables for its length, without
                # telling its limit: 3 words per variable, and 1 more, keep away from it.
                words = re.findall(r"[^\W_][\w'’-]*", PLACEHOLDER_RE.sub(" ", template.body))
                variables = set(PLACEHOLDER_RE.findall(template.body))
                self.assertGreaterEqual(len(words), 3 * len(variables) + 1)

    def test_english_versions(self):
        """Every message exists in French and in English (same name at Meta), with the same
        variables and buttons. An English-speaking contact receives the English version once
        Meta approved it, the French one until then."""
        data = self.env["ir.model.data"].search([
            ("model", "=", "whatsapp.template"),
            ("module", "in", ("whatsapp_cloud", "whatsapp_cloud_sale", "ocd_live_whatsapp", "ocd_live_shop_whatsapp")),
        ])
        templates = self.env["whatsapp.template"].with_context(active_test=False).browse(data.mapped("res_id"))
        self.assertTrue(all(templates.mapped("active")), "The English versions are active too")
        french = templates.filtered(lambda template: template._lang_base(template.lang_code) == "fr")
        self.assertGreater(len(french), 25)
        for template in french:
            with self.subTest(template=template.template_name):
                english = templates.filtered(lambda other: (
                    other.template_name == template.template_name and other._lang_base(other.lang_code) == "en"
                ))
                self.assertEqual(len(english), 1)
                self.assertEqual((english.model_id, english.category), (template.model_id, template.category))
                self.assertEqual(english.variable_ids.mapped("sequence"), template.variable_ids.mapped("sequence"))
                self.assertEqual(len(english.button_ids), len(template.button_ids))
                self.assertEqual(english.button_url_value, template.button_url_value)
        self.env["res.lang"]._activate_lang("en_US")
        partner = self.env["res.partner"].create({"name": "Grace Mensah", "lang": "en_US"})
        space = self.env.ref("ocd_live_whatsapp.template_space_link")
        space_en = self.env.ref("ocd_live_whatsapp.template_space_link_en")
        space.status = "approved"
        self.assertEqual(space._get_lang_version(partner), space, "Not submitted to Meta yet")
        space_en.status = "approved"
        self.assertEqual(space._get_lang_version(partner), space_en)
        # Archived by the version 20.0.1.4.0 (French only): active again at the update
        confirmed = self.env.ref("whatsapp_cloud_sale.template_order_confirmed_en")
        confirmed.active = False
        self.assertEqual(restore_english_templates(self.env), confirmed)
        self.assertTrue(confirmed.active)

    def test_refused_templates_take_the_new_texts(self):
        """Refused by Meta: the ticket (a « code », a sentence in a variable) and the access (a
        password with a link). Still waiting in Odoo when the webhook is not set up, they take
        the new texts; the ticket loses its variable {{7}}, the button of the access its label."""
        migration = load_script(
            "ocd_live_whatsapp/migrations/20.0.1.5.0/post-migration.py", "ocd_live_whatsapp_texts_20_0_1_5_0"
        )
        ticket = self.env.ref("ocd_live_whatsapp.template_ticket")
        access = self.env.ref("ocd_live_whatsapp.template_access_link")
        texts = {"ticket": ticket.body, "access": access.body}
        self.assertNotIn("code", texts["ticket"].lower())
        self.assertNotIn("mot de passe", texts["access"].lower())
        ticket.write({"body": migration.OLD_TEXTS["ocd_live_whatsapp.template_ticket"][0], "status": "pending"})
        access.write({"body": migration.OLD_TEXTS["ocd_live_whatsapp.template_access_link"][0], "status": "rejected"})
        access.button_ids.name = "Choisir mon mot de passe"
        self.assertIn(7, ticket.variable_ids.mapped("sequence"))
        migration.migrate(self.env.cr, "20.0.1.4.0")
        self.env.invalidate_all()
        self.assertEqual(ticket.body, texts["ticket"])
        self.assertEqual(sorted(ticket.variable_ids.mapped("sequence")), [1, 2, 3, 4, 5, 6])
        self.assertEqual(access.body, texts["access"])
        self.assertEqual(access.button_ids.name, "Activer mon compte")

    def test_migrations_give_the_new_texts(self):
        """The databases installed before keep the previous texts (data loaded once): the
        migrations give them the new ones, except to a template approved by Meta."""
        Module = self.env["ir.module.module"]
        for module, version in (
            ("whatsapp_cloud_sale", "20.0.2.4.0"),
            ("ocd_live_whatsapp", "20.0.1.3.0"),
            ("ocd_live_shop_whatsapp", "20.0.1.3.0"),
            ("ocd_live_whatsapp", "20.0.1.5.0"),
            ("ocd_live_shop_whatsapp", "20.0.1.5.0"),
        ):
            if not Module.search_count([("name", "=", module), ("state", "=", "installed")]):
                continue
            migration = load_script(
                f"{module}/migrations/{version}/post-migration.py", f"{module}_texts_{version}"
            )
            templates = {xmlid: self.env.ref(xmlid) for xmlid in migration.OLD_TEXTS}
            texts = {xmlid: template.body for xmlid, template in templates.items()}
            for xmlid, template in templates.items():
                template.body = migration.OLD_TEXTS[xmlid][-1]
            approved = next(t for t in templates.values() if t.category != "authentication")
            approved.status = "approved"
            migration.migrate(self.env.cr, "previous version")
            self.env.invalidate_all()
            for xmlid, template in templates.items():
                with self.subTest(template=xmlid):
                    expected = migration.OLD_TEXTS[xmlid][-1] if template == approved else texts[xmlid]
                    self.assertEqual(template.body, expected)
