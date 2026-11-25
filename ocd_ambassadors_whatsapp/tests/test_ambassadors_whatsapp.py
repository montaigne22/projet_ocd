from datetime import date, datetime

from odoo.tests import tagged

from odoo.addons.ocd_ambassadors.tests.common import OcdAmbassadorCommon


@tagged("post_install", "-at_install")
class TestOcdAmbassadorsWhatsapp(OcdAmbassadorCommon):
    """The messages of the ambassadors (design Ambassadeurs): the parcels delivered, once a day in
    the evening; the payout made; the payout number changed, to the number of the account."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110041", "waba_id": "2220041", "access_token": "test-token",
            "resource_calendar_id": False,
        })
        cls.grace.write({"lang": "en_US", "ocd_whatsapp_optin": True, "whatsapp_opt_in": True})
        cls.Message = cls.env["whatsapp.message"]

    def messages(self, record, name):
        return self.Message.search([("model", "=", record._name), ("res_id", "=", record.id),
                                    ("template_id.template_name", "=", name)], order="id")

    def test_the_parcels_delivered_told_once_a_day(self):
        first, second = self._amb_order(), self._amb_order(customer=self.herve)
        for order in (first, second):
            self._deliver(self._parcel(order, self.brenda))
        self.Gain._ocd_tell_delivered(now=datetime(2026, 11, 19, 19, 30))
        message = self.messages(self.grace, "ocd_ambassadeur_livres")
        self.assertEqual(len(message), 1, "One message for the two parcels")
        self.assertIn("parcels you shared were delivered: 2 parcels, for", message.body)
        self.assertIn("1,200", message.body)
        self.assertIn("confirmed in 7 days", message.body)
        self.assertNotIn("code", message.body.lower())
        self.Gain._ocd_tell_delivered(now=datetime(2026, 11, 19, 21, 0))
        self.assertEqual(len(self.messages(self.grace, "ocd_ambassadeur_livres")), 1, "Once a day")

    def test_parcels_counted_in_the_language_sent(self):
        """Meta does not know the English version: the French one, with « 2 colis » in French."""
        self.env["res.lang"]._activate_lang("fr_FR")
        english = self.env["whatsapp.template"].search([
            ("template_name", "=", "ocd_ambassadeur_livres"), ("lang_code", "=", "en"),
        ])
        english.status = "missing"
        Partner = self.env["res.partner"]
        xmlid = "ocd_ambassadors_whatsapp.template_ambassador_delivered"
        self.assertEqual(Partner._ocd_whatsapp_lang(xmlid, self.grace), "fr_FR")
        english.status = "unknown"
        self.assertEqual(Partner._ocd_whatsapp_lang(xmlid, self.grace), "en_US")

    def test_the_payout_and_a_new_number(self):
        orders = self._amb_order(lines=[(self.dress, 4)])
        self._deliver(self._parcel(orders, self.brenda))
        self._confirm_due(self._gain(orders))
        payout = self.env["ocd.payout"]._ocd_prepare(vendors=self.grace, day=date(2026, 11, 23))
        payout.action_validate()
        payout.payment_reference = "OM-93107"
        payout.action_register_payment()
        paid = self.messages(payout, "ocd_ambassadeur_versement")
        self.assertEqual(len(paid), 1)
        self.assertIn("reference OM-93107", paid.body)
        self.grace._ocd_ambassador_set_momo("+237 655112233")
        number = self.messages(self.grace, "ocd_ambassadeur_numero")
        self.assertEqual(len(number), 1)
        self.assertIn("655112233", number.body.replace(" ", ""))

    def test_opened_accounts_agree_to_the_messages(self):
        new = self.env["res.partner"]._ocd_ambassador_signup("Kevin", "+237 655001122", self.cameroon, "+237 655001122")
        new.ocd_whatsapp_optin = False
        new._ocd_ambassador_open_account()
        self.assertTrue(new.ocd_whatsapp_optin)

    def test_templates_for_meta(self):
        """The rules of Meta (no variable at the start or at the end, words between two variables,
        never « code » in a Utility template), and each template has its English version."""
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "https://ocd.example.com")
        data = self.env["ir.model.data"].search([("model", "=", "whatsapp.template"),
                                                 ("module", "=", "ocd_ambassadors_whatsapp")])
        templates = self.env["whatsapp.template"].browse(data.mapped("res_id"))
        self.assertEqual(len(templates), 6)
        for template in templates:
            with self.subTest(template=template.name):
                template._check_for_meta()
                self.assertNotIn("code", template.body.lower())
                english = templates.filtered(lambda other: other.template_name == template.template_name and other != template)
                self.assertEqual(len(english), 1)
                self.assertEqual(english.variable_ids.mapped("sequence"), template.variable_ids.mapped("sequence"))
                self.assertEqual(english.button_url_value, template.button_url_value)
