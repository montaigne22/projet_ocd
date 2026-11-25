from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdSoireesWhatsapp(OcdShopCommon):
    """The big events on WhatsApp (chantier 7, design ProgrammeSoirees): the invitation of the
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
        self.assertIn("OCD Live organises Black Friday, which takes place", invitation.body)
        self.assertIn("tap « Join » before", invitation.body)

    def test_english_version_missing_at_meta(self):
        """Meta does not know the English invitation: the vendor gets the French one, with its
        dates in French too (computed in the language of the version sent)."""
        self.env["res.lang"]._activate_lang("fr_FR")
        english = self.env.ref("ocd_soirees_whatsapp.template_evening_invite_en")
        english.status = "missing"
        self.evening.action_ocd_open()
        invitation = self._messages("ocd_soiree_invitation")
        self.assertEqual(invitation.template_id, self.env.ref("ocd_soirees_whatsapp.template_evening_invite"))
        tz_name = self.brenda._ocd_tz_name()
        french = self.evening.with_context(lang="fr_FR")
        self.assertIn(french._ocd_when_sentence(tz_name), invitation.body)
        self.assertIn(french._ocd_registration_day(tz_name), invitation.body)
        self.assertNotIn(self.evening.with_context(lang="en_US")._ocd_registration_day(tz_name), invitation.body)

    def test_the_start_is_told(self):
        self.evening.action_ocd_open()
        partner = self.env["res.partner"].create({"name": "Paul", "phone": "+237 670000039", "lang": "en_US"})
        self.env["ocd.evening.alert"].create({"evening_id": self.evening.id, "partner_id": partner.id})
        self.env["ocd.evening.participation"].create({
            "evening_id": self.evening.id, "vendor_id": self.brenda.id, "state": "approved",
        })
        with freeze_time(self.evening.date_start - timedelta(minutes=10)):
            self.env["ocd.evening"]._cron_ocd_evenings()
        start = self._messages("ocd_soiree_commence")
        self.assertEqual(len(start), 1)
        self.assertIn("Hello, Black Friday of OCD Live starts at", start.body)
        self.assertIn("Vendors in live: 1, with their promos until", start.body)
        template = self.env.ref("ocd_soirees_whatsapp.template_evening_start")
        alert = self.evening.alert_ids
        self.assertEqual(template._render(template.button_url_value, alert)[alert.id], "evenements/black-friday")

    def test_an_event_of_several_days(self):
        """The period in the invitation, the last day in « until »."""
        week = self.env["ocd.evening"].create({
            "name": "Tabaski week", "date_start": self.evening.date_start,
            "date_end": self.evening.date_start + timedelta(days=4), "country_ids": self.evening.country_ids.ids,
        })
        week.action_ocd_open()
        invitation = self._messages("ocd_soiree_invitation")
        self.assertIn(f"which takes place {week._ocd_when_sentence(self.brenda._ocd_tz_name())}.", invitation.body)
        self.assertIn(" from ", invitation.body)
        partner = self.env["res.partner"].create({"name": "Paul", "phone": "+237 670000039", "lang": "en_US"})
        alert = self.env["ocd.evening.alert"].create({"evening_id": week.id, "partner_id": partner.id})
        self.assertEqual(alert._ocd_whatsapp_until(), week._ocd_until_text(partner._ocd_tz_name()))
        self.assertIn(" at ", alert._ocd_whatsapp_until())
