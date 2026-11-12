from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdShopSettingsPage(OcdShopCommon):

    def _page(self):
        return self.env["ocd.live.settings"]

    def test_shop_and_payments_sections(self):
        page = self._page().get_settings_page()
        keys = [section["key"] for section in page["sections"]]
        self.assertIn("shop", keys)
        self.assertIn("payments", keys)
        payments = next(section for section in page["sections"] if section["key"] == "payments")
        cod = self.env.ref("delivery.payment_provider_cod")
        key = f"ocd_provider_{cod.id}"
        self.assertIn(key, [item["key"] for item in payments["items"]], "One switch per payment provider")
        result = self._page().save_settings_page({key: True, "ocd_prep_hours": 6, "ocd_cash_deadline": 19.5})
        self.assertTrue(result["ok"], result)
        self.assertTrue(cod.is_published)
        self.assertEqual(self.env.company.ocd_prep_hours, 6)
        self.assertEqual(self.env.company.ocd_cash_deadline, 19.5)

    def test_prices_of_the_vendors_in_order(self):
        result = self._page().save_settings_page({"ocd_vendor_rate_min": 2000, "ocd_vendor_rate_max": 1000})
        self.assertFalse(result["ok"])
        self.assertIn("ocd_vendor_rate_max", result["errors"])
        result = self._page().save_settings_page({"ocd_vendor_rate_min": 500, "ocd_vendor_rate_max": 3000})
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.env.company._ocd_vendor_rate_bounds(), (500, 3000))

    def test_rates_button(self):
        action = self._page().run_settings_action("ocd_rates")
        self.assertEqual(action["tag"], "display_notification")

    def _campay(self):
        Provider = self.env["payment.provider"]
        if "campay_demo_active" not in Provider._fields:
            self.skipTest("The CamPay module is not installed.")
        campay = Provider.search([("code", "=", "campay"), ("company_id", "=", self.env.company.id)], limit=1)
        if not campay:
            self.skipTest("No CamPay provider.")
        return campay

    def test_demo_payments_of_campay(self):
        """The demo payments of CamPay on the page: on or off, the amount, the last day, the
        numbers; checked before saving; a red line on the dashboard while they are on."""
        campay = self._campay()
        page = self._page().get_settings_page()
        payments = next(section for section in page["sections"] if section["key"] == "payments")
        keys = [item["key"] for item in payments["items"]]
        self.assertIn("ocd_campay_demo_active", keys)
        self.assertIn("ocd_campay_demo_numbers", keys)
        self.assertFalse(page["values"]["ocd_campay_demo_active"])
        self.assertEqual(page["values"]["ocd_campay_demo_amount"], 25)

        result = self._page().save_settings_page({
            "ocd_campay_demo_active": True, "ocd_campay_demo_numbers": "670000001, 12345",
        })
        self.assertFalse(result["ok"])
        self.assertIn("12345", result["errors"]["ocd_campay_demo_numbers"])
        self.assertFalse(campay.campay_demo_active, "Nothing is written when a value is wrong")
        today = fields.Date.context_today(campay)
        result = self._page().save_settings_page({
            "ocd_campay_demo_active": True, "ocd_campay_demo_end": (today - timedelta(days=1)).isoformat(),
        })
        self.assertIn("ocd_campay_demo_end", result["errors"])

        result = self._page().save_settings_page({
            "ocd_campay_demo_active": True, "ocd_campay_demo_amount": 50,
            "ocd_campay_demo_numbers": "670000001, 6 90 00 00 02",
        })
        self.assertTrue(result["ok"], result)
        self.assertTrue(campay.campay_demo_active)
        self.assertEqual(campay.campay_demo_amount, 50)
        self.assertEqual(campay.campay_demo_end, today, "Switched on without a day: until tonight")
        self.assertEqual(campay._campay_demo_number_list(), {"237670000001", "237690000002"})
        todos = self.env["ocd.live.dashboard"]._ocd_todos()
        demo = next(todo for todo in todos if todo["key"] == f"campay_demo_{campay.id}")
        self.assertEqual(demo["tone"], "red")
        self.assertIn("2", demo["text"])

        result = self._page().save_settings_page({"ocd_campay_demo_active": False})
        self.assertTrue(result["ok"], result)
        todos = self.env["ocd.live.dashboard"]._ocd_todos()
        self.assertFalse([todo for todo in todos if todo["key"].startswith("campay_demo_")])
