from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveSettingsPage(OcdLiveCommon):
    """The settings page (BoParametres): sections, values of the company, checks, saving by a
    manager of OCD Live who is not an administrator of Odoo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["res.users"].create({
            "name": "Esi Manager",
            "login": "esi.manager",
            "group_ids": [Command.set([cls.env.ref("ocd_live.group_ocd_live_manager").id])],
        })
        cls.user = cls.env["res.users"].create({
            "name": "Kofi Team",
            "login": "kofi.team",
            "group_ids": [Command.set([cls.env.ref("ocd_live.group_ocd_live_user").id])],
        })

    def _page(self, user=None):
        return self.env["ocd.live.settings"].with_user(user or self.manager)

    def test_page_has_the_sections_and_the_values(self):
        page = self._page().get_settings_page()
        keys = [section["key"] for section in page["sections"]]
        self.assertEqual(keys[:2], ["lives", "directory"])
        lives = page["sections"][0]
        self.assertTrue(lives["count"])
        items = {item["key"]: item for item in lives["items"]}
        self.assertEqual(items["ocd_open_days"]["kind"], "checks")
        self.assertEqual(page["values"]["ocd_hold_minutes"], 30)
        self.assertEqual(page["values"]["ocd_lives_channel_id"], self.env.ref("ocd_live.channel_lives").id)
        self.assertEqual(page["values"]["ocd_discovery_price"], self.discovery.list_price)
        self.assertNotIn("odoo_settings", page, "No link to the screens of Odoo")

    def test_only_the_managers(self):
        with self.assertRaises(AccessError):
            self._page(self.user).get_settings_page()
        with self.assertRaises(AccessError):
            self._page(self.user).save_settings_page({"ocd_hold_minutes": 15})

    def test_save_by_a_manager(self):
        result = self._page().save_settings_page({
            "ocd_hold_minutes": 15,
            "ocd_require_animatrice": False,
            "ocd_first_slot_hour": 9.0,
            "ocd_booking_open_date": "2026-12-15",
            "ocd_lives_channel_id": False,
            "ocd_discovery_price": 20000,
            "ocd_studio_city": "  Kara ",
        })
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["saved_at"])
        company = self.company
        self.assertEqual(company.ocd_hold_minutes, 15)
        self.assertFalse(company.ocd_require_animatrice)
        self.assertEqual(company.ocd_first_slot_hour, 9.0)
        self.assertEqual(str(company.ocd_booking_open_date), "2026-12-15")
        self.assertFalse(company.ocd_lives_channel_id)
        self.assertEqual(self.discovery.list_price, 20000)
        self.assertEqual(company.ocd_studio_city, "Kara")
        self.assertEqual(result["values"]["ocd_hold_minutes"], 15)

    def test_wrong_values_write_nothing(self):
        result = self._page().save_settings_page({
            "ocd_hold_minutes": "abc",
            "ocd_slots_per_day": 2.5,
            "ocd_pass_reminder_days": -1,
            "ocd_calendar_mode": "nonsense",
            "ocd_require_animatrice": False,
        })
        self.assertFalse(result["ok"])
        self.assertEqual(
            set(result["errors"]), {"ocd_hold_minutes", "ocd_slots_per_day", "ocd_pass_reminder_days", "ocd_calendar_mode"}
        )
        self.assertTrue(self.company.ocd_require_animatrice, "Nothing is written when a value is wrong")

    def test_checks_between_settings(self):
        result = self._page().save_settings_page({"ocd_slots_per_day": 20, "ocd_slot_hours": 2})
        self.assertFalse(result["ok"])
        self.assertIn("ocd_slots_per_day", result["errors"], "The last live would end after midnight")
        days = ["ocd_open_mon", "ocd_open_tue", "ocd_open_wed", "ocd_open_thu", "ocd_open_fri", "ocd_open_sat", "ocd_open_sun"]
        result = self._page().save_settings_page(dict.fromkeys(days, False))
        self.assertIn("ocd_open_mon", result["errors"], "Open at least one day")
        self.assertTrue(self.company.ocd_open_mon)

    def test_only_the_settings_of_the_page(self):
        result = self._page().save_settings_page({"name": "Another company", "ocd_hold_minutes": 20})
        self.assertFalse(result["ok"])
        self.assertIn("name", result["errors"])
        self.assertNotEqual(self.company.name, "Another company")

    def test_currencies_by_country(self):
        """The section of the currencies: one button puts them in place, then the zones, the
        rates and what a customer pays show."""
        section = self._page()._ocd_section_currencies()
        self.assertEqual(section["key"], "currencies")
        items = {item["key"]: item for item in section["items"]}
        self.assertIn("ocd_currency_off", items)
        self.assertEqual(items["ocd_currency_zones"]["button"]["method"], "_ocd_currencies_setup_button")
        Currencies = self.registry["ocd.live.currencies"]
        with patch.object(Currencies, "_ocd_read_usd_per_euro", return_value=1.1081):
            action = self._page().run_settings_action("ocd_currency_zones")
        self.assertEqual(action["params"]["type"], "success")
        self.assertTrue(self.env["ocd.live.currencies"]._ocd_is_set_up())
        section = self._page()._ocd_section_currencies()
        items = {item["key"]: item for item in section["items"]}
        self.assertNotIn("ocd_currency_off", items)
        self.assertEqual(len(items["ocd_currency_zones"]["chips"]), 4)
        self.assertIn("655.957", items["ocd_currency_rates"]["help"])
        self.assertIn("1.1081", items["ocd_currency_rates"]["help"])
        self.assertIn(self.discovery.name, items["ocd_currency_example"]["help"])
        # The dollar of the day, by the button
        with patch.object(Currencies, "_ocd_read_usd_per_euro", return_value=1.2):
            action = self._page().run_settings_action("ocd_currency_rates")
        self.assertIn("1.2000", action["params"]["message"])
        with patch.object(Currencies, "_ocd_read_usd_per_euro", return_value=None):
            action = self._page().run_settings_action("ocd_currency_rates")
        self.assertEqual(action["params"]["type"], "warning")
