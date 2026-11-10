from datetime import datetime, time, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.ocd_live.tests.common import OcdLiveCommon
from odoo.addons.whatsapp_cloud.models.whatsapp_template import WhatsappTemplate


@tagged("post_install", "-at_install")
class TestOcdLiveWhatsapp(OcdLiveCommon):

    def _capture(self):
        """Patch the sending of the templates: return the list of (template, records, context)."""
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records, dict(template.env.context)))
            return template.env["whatsapp.message"].browse([1])

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
