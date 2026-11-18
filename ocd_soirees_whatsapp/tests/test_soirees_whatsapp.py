from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdSoireesWhatsapp(OcdShopCommon):
    """The big evenings on WhatsApp (chantier 7, design ProgrammeSoirees): the invitation of the
    vendors, the start told to the people who asked."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110039", "waba_id": "2220039", "access_token": "test-token",
            "resource_calendar_id": False,
        })
        cameroon = cls.env.ref("base.cm")
        cls.brenda.write({"country_id": cameroon.id, "phone": "+237 690000039", "lang": "en_US",
                          "ocd_whatsapp_optin": True})
        start = fields.Datetime.now().replace(microsecond=0) + timedelta(days=6)
        cls.evening = cls.env["ocd.evening"].create({
            "name": "Black Friday", "date_start": start, "date_end": start + timedelta(hours=5),
            "country_ids": [fields.Command.set(cameroon.ids)],
        })
        cls.Message = cls.env["whatsapp.message"]

    def _messages(self, name):
        return self.Message.search([("template_id.template_name", "=", name)], order="id")

    def test_the_vendors_are_invited(self):
        self.evening.action_ocd_open()
        invitation = self._messages("ocd_soiree_invitation")
        self.assertEqual(len(invitation), 1)
        self.assertEqual(invitation.res_id, self.brenda.id)
        self.assertIn("OCD Live organises Black Friday on", invitation.body)
        self.assertIn("tap « Join » before", invitation.body)

    def test_the_start_is_told(self):
        self.evening.action_ocd_open()
        partner = self.env["res.partner"].create({"name": "Paul", "phone": "+237 670000039", "lang": "en_US"})
        self.env["ocd.evening.alert"].create({"evening_id": self.evening.id, "partner_id": partner.id})
        with freeze_time(self.evening.date_start - timedelta(minutes=10)):
            self.env["ocd.evening"]._cron_ocd_evenings()
        start = self._messages("ocd_soiree_commence")
        self.assertEqual(len(start), 1)
        self.assertIn("Good evening, Black Friday of OCD Live starts at", start.body)
        template = self.env.ref("ocd_soirees_whatsapp.template_evening_start")
        alert = self.evening.alert_ids
        self.assertEqual(template._render(template.button_url_value, alert)[alert.id], "soirees/black-friday")
