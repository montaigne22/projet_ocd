from odoo.tests import BaseCase

from odoo.addons.ocd_live.tools import parse_amount


class TestOcdTools(BaseCase):

    def test_an_amount_typed_on_a_phone(self):
        francs = {
            "3000": 3000, "3 000": 3000, "3.000 F": 3000, "3,000": 3000, "15 000 FCFA": 15000,
            "3000frs": 3000, "15 000 F CFA": 15000, "1.000.000": 1000000, "1'000": 1000,
            "XAF 2500": 2500, "0": 0,
            # Not exactly one amount: refused, never misread
            "2500,50": None, "3000-5000": None, "3k": None, "": None, "F": None, "1.000.5": None,
            None: None,
        }
        for text, amount in francs.items():
            self.assertEqual(parse_amount(text), amount, text)
        cents = {"12,50": 12.5, "1.234,56": 1234.56, "1,234.56": 1234.56, "3.000": 3000, "15 €": 15, "12,505": 12505}
        for text, amount in cents.items():
            self.assertEqual(parse_amount(text, decimal_places=2), amount, text)
        self.assertEqual(parse_amount("3000 $", symbol="$"), 3000)
