from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.ocd_live.tests.common import OcdLiveCommon
from odoo.addons.whatsapp_cloud.models.whatsapp_template import WhatsappTemplate


@tagged("post_install", "-at_install")
class TestOcdRemoteWhatsapp(OcdLiveCommon):
    """Remote live: the vendor is told who their host is, then invited to join the account of
    OCD Live 15 minutes before."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ocd.live.account"].search([]).active = False
        cls.account = cls.env["ocd.live.account"].create({
            "name": "OCD Live Cameroun", "handle": "@ocdlive.cm", "live_url": "https://www.tiktok.com/@ocdlive.cm/live",
            "country_ids": [Command.set(cls.env.ref("base.cm").ids)],
        })

    def _capture(self):
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"].new({"state": "queued"})

        return calls, patch.object(WhatsappTemplate, "_send", fake_send)

    def test_host_chosen_then_invitation_to_join(self):
        calls, patcher = self._capture()
        booking = self._book(self.starts[4], mode="remote", state="confirmed")
        studio = self._book(self.starts[1], partner=self.other_vendor, state="confirmed")
        with patcher:
            booking.animatrice_id = self.host
            studio.animatrice_id = self.host
            booking.animatrice_id = self.host
            with freeze_time(booking.start_datetime - timedelta(minutes=14)):
                self.env["ocd.live.booking"]._cron_remote_join()
                self.env["ocd.live.booking"]._cron_remote_join()
        self.assertEqual(
            [call[0] for call in calls], ["ocd_live_animatrice", "ocd_live_rejoindre"],
            "The host once (not for a studio live), then the invitation once",
        )
        self.assertEqual(calls[1][1], booking)
        self.assertTrue(booking.ocd_join_sent_at)
        self.assertEqual(booking.ocd_join_state, "invited")

    def test_templates_of_the_remote_live_render(self):
        booking = self._book(self.starts[4], mode="remote", state="confirmed", animatrice_id=self.host.id)
        for xmlid in ("template_live_host", "template_live_join", "template_live_host_en", "template_live_join_en"):
            template = self.env.ref(f"ocd_live_whatsapp.{xmlid}")
            values = [template._render(variable.value, booking)[booking.id] for variable in template.variable_ids]
            self.assertTrue(all(values), xmlid)
            if "join" in xmlid:
                self.assertEqual(values[2:], ["TikTok", "@ocdlive.cm"], "The platform and the account to join")
                url = template._render(template.button_url_value, booking)[booking.id]
                self.assertEqual(url, booking._ocd_join_path()[1:], "The button opens « Join my live »")
            else:
                self.assertEqual(values[2], "Dzifa A.")
