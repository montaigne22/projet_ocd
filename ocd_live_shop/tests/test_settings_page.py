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
