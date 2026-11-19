from datetime import timedelta

from odoo.tests import tagged

from odoo.addons.ocd_business.tests.test_business import OcdBusinessCommon


@tagged("post_install", "-at_install")
class TestOcdBusinessWhatsapp(OcdBusinessCommon):
    """The messages of OCD Business (design OcdBusiness): paid, the end close, the end, the launch."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110051", "waba_id": "2220051", "access_token": "test-token",
            "resource_calendar_id": False,
        })
        cls.brenda.write({"lang": "en_US", "ocd_whatsapp_optin": True, "whatsapp_opt_in": True})
        cls.Message = cls.env["whatsapp.message"]

    def messages(self, name):
        return self.Message.search([("model", "=", "res.partner"), ("res_id", "=", self.brenda.id),
                                    ("template_id.template_name", "=", name)], order="id")

    def test_paid_then_the_end(self):
        self._order(self.quarter)
        paid = self.messages("ocd_business_payee")
        self.assertEqual(len(paid), 1)
        self.assertIn("your formula OCD Business is paid: it runs until", paid.body)
        period = self.Period.search([("vendor_id", "=", self.brenda.id)])
        period.date_end = self._today() + timedelta(days=5)
        self.brenda._ocd_business_refresh()
        self.env["res.partner"]._ocd_business_tell_ends()
        self.env["res.partner"]._ocd_business_tell_ends()
        self.assertEqual(len(self.messages("ocd_business_fin_proche")), 1, "Once per date of end")
        period.write({"date_start": self._today() - timedelta(days=30), "date_end": self._today() - timedelta(days=1)})
        self.brenda._ocd_business_refresh()
        self.env["res.partner"]._ocd_business_tell_ends()
        ended = self.messages("ocd_business_terminee")
        self.assertEqual(len(ended), 1)
        self.assertIn("nothing is erased", ended.body)

    def test_templates_for_meta(self):
        """The rules of Meta (no variable at the start or at the end, words between two variables,
        never « code » in a Utility template), and each template has its English version."""
        self.env["ir.config_parameter"].sudo().set_str("web.base.url", "https://ocd.example.com")
        data = self.env["ir.model.data"].search([("model", "=", "whatsapp.template"),
                                                 ("module", "=", "ocd_business_whatsapp")])
        templates = self.env["whatsapp.template"].browse(data.mapped("res_id"))
        self.assertEqual(len(templates), 8)
        for template in templates:
            with self.subTest(template=template.name):
                template._check_for_meta()
                self.assertNotIn("code", template.body.lower())
                english = templates.filtered(lambda other: other.template_name == template.template_name and other != template)
                self.assertEqual(len(english), 1)
                self.assertEqual(english.variable_ids.mapped("sequence"), template.variable_ids.mapped("sequence"))
