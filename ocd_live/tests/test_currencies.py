from datetime import date, timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import TransactionCase, tagged

from odoo.addons.ocd_live.models.ocd_live_currencies import CFA_PER_EURO, zone_of

USD_PER_EURO = 1.1081  # the rate of the European Central Bank on 12 November 2026


@tagged("post_install", "-at_install")
class TestCurrenciesByCountry(TransactionCase):
    """The currencies by country: the prices written in CFA francs (XOF), each country sees them
    in its currency (XOF, XAF, EUR or USD), converted at the fixed rates of the CFA francs and at
    the dollar of the day, rounded to the unit in euros and dollars."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        xof = cls.env.ref("base.XOF")
        xof.active = True
        cls.company = cls.env["res.company"].create({
            "name": "OCD Live Lomé", "currency_id": xof.id, "country_id": cls.env.ref("base.tg").id,
        })
        cls.env.user.write({"company_ids": [Command.link(cls.company.id)]})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.Currencies = cls.env["ocd.live.currencies"]
        cls.product = cls.env["product.product"].create({
            "name": "Live Discovery", "list_price": 15000, "company_id": cls.company.id,
        })

    def _bank(self, usd_per_euro=USD_PER_EURO):
        """The European Central Bank answers `usd_per_euro` (None: it does not answer)."""
        return patch.object(
            self.registry["ocd.live.currencies"], "_ocd_read_usd_per_euro", return_value=usd_per_euro
        )

    def _setup(self, usd_per_euro=USD_PER_EURO):
        with self._bank(usd_per_euro):
            return self.Currencies._ocd_setup(self.company)

    def _pricelist(self, zone):
        return self.env.ref(f"ocd_live.pricelist_{zone}")

    def _price(self, zone):
        return self._pricelist(zone)._get_product_price(self.product, 1.0)

    def test_zone_of_each_country(self):
        for code in ("TG", "BJ", "CI", "SN", "ML", "BF", "NE", "GW"):
            self.assertEqual(zone_of(code), "xof", code)
        for code in ("CM", "GA", "CG", "TD", "CF", "GQ"):
            self.assertEqual(zone_of(code), "xaf", code)
        # Europe, the rest of Africa and France beyond Europe: the euro
        for code in ("FR", "BE", "DE", "GB", "CH", "MA", "NG", "GH", "CD", "ZA", "GP", "MQ", "GF", "RE", "YT"):
            self.assertEqual(zone_of(code), "eur", code)
        # The Americas, Asia and Oceania: the dollar
        for code in ("US", "CA", "BR", "HT", "CN", "IN", "AE", "JP", "AU", "NC"):
            self.assertEqual(zone_of(code), "usd", code)

    def test_setup_puts_the_four_zones_in_place(self):
        self.assertFalse(self.Currencies._ocd_is_set_up())
        pricelists = self._setup()
        self.assertTrue(self.Currencies._ocd_is_set_up())
        self.assertEqual(pricelists.currency_id.mapped("name"), ["XOF", "XAF", "EUR", "USD"])
        self.assertTrue(all(currency.active for currency in pricelists.currency_id))
        self.assertTrue(self.env["res.groups"]._is_feature_enabled("product.group_product_pricelist"))
        groups = pricelists.country_group_ids
        self.assertEqual(len(groups), 4)
        self.assertIn(self.env.ref("base.tg"), self.env.ref("ocd_live.country_group_xof").country_ids)
        self.assertIn(self.env.ref("base.cm"), self.env.ref("ocd_live.country_group_xaf").country_ids)
        self.assertIn(self.env.ref("base.fr"), self.env.ref("ocd_live.country_group_eur").country_ids)
        self.assertIn(self.env.ref("base.us"), self.env.ref("ocd_live.country_group_usd").country_ids)
        # Every country in one zone, once
        countries = self.env["res.country"].search([])
        self.assertEqual(sum(len(group.country_ids) for group in groups), len(countries))
        self.assertEqual(groups.country_ids, countries)
        # Again: the same records, nothing more
        self.assertEqual(self._setup(), pricelists)
        self.assertEqual(len(self._pricelist("eur").item_ids), 1)

    def test_names_of_the_zones_in_each_language(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self._setup()
        pricelist = self._pricelist("xaf")
        self.assertEqual(pricelist.with_context(lang="en_US").name, "Central Africa (XAF)")
        self.assertEqual(pricelist.with_context(lang="fr_FR").name, "Afrique centrale (XAF)")
        group = self.env.ref("ocd_live.country_group_usd")
        self.assertEqual(group.with_context(lang="fr_FR").name, "Amériques, Asie et Océanie (USD)")
        # Renamed by the team: kept by the next setup
        pricelist.with_context(lang="fr_FR").name = "Cameroun et voisins"
        self._setup()
        self.assertEqual(pricelist.with_context(lang="fr_FR").name, "Cameroun et voisins")

    def test_prices_in_each_currency(self):
        """15 000 F CFA: 15 000 F CFA in Cameroon (same value), 23 € and 25 $ (rounded)."""
        self._setup()
        self.assertEqual(self._price("xof"), 15000)
        self.assertEqual(self._price("xaf"), 15000)
        self.assertEqual(self._price("eur"), 23)  # 22.87 €
        self.assertEqual(self._price("usd"), 25)  # 25.34 $
        parts = self.Currencies._ocd_example(self.product).split(" · ")
        self.assertEqual(len(parts), 3, "The zones of another currency: XAF, EUR, USD")
        self.assertIn("15,000", parts[0])
        self.assertIn("23", parts[1])
        self.assertIn("€", parts[1])
        self.assertNotIn(".00", parts[1], "Rounded: no cents")
        self.assertIn("25", parts[2])

    def test_rates_of_the_francs_and_of_the_euro_are_fixed(self):
        xaf, eur = self.env.ref("base.XAF"), self.env.ref("base.EUR")
        xaf.active = eur.active = True
        # A rate typed before, wrong: put back at the parity
        self.env["res.currency.rate"].create({
            "currency_id": xaf.id, "company_id": self.company.id, "name": date(2024, 1, 1), "rate": 0.9,
        })
        self._setup()
        today = fields.Date.context_today(self.Currencies)
        xof = self.company.currency_id
        self.assertAlmostEqual(xof._convert(655957, eur, self.company, today), 1000, places=2)
        self.assertEqual(xof._convert(15000, xaf, self.company, today), 15000)
        self.assertEqual(xof._convert(15000, xaf, self.company, date(2024, 6, 1)), 15000)
        usd = self.env.ref("base.USD")
        self.assertAlmostEqual(eur._convert(1000, usd, self.company, today), 1108.10, places=2)

    def test_each_country_gets_its_pricelist(self):
        self._setup()
        Pricelist = self.env["product.pricelist"]
        codes = {"tg": "xof", "sn": "xof", "cm": "xaf", "ga": "xaf", "fr": "eur", "ng": "eur", "us": "usd", "cn": "usd"}
        countries = {code: self.env.ref(f"base.{code}") for code in codes}
        found = Pricelist._get_country_pricelist_multi([country.id for country in countries.values()])
        for code, zone in codes.items():
            self.assertEqual(found[countries[code].id], self._pricelist(zone), code)
        # A vendor of Cameroon: the pricelist in XAF, so CamPay is offered
        vendor = self.env["res.partner"].create({"name": "Awa Gâteaux", "country_id": countries["cm"].id})
        self.assertEqual(vendor.with_company(self.company).property_product_pricelist, self._pricelist("xaf"))

    def test_dollar_of_the_day(self):
        self._setup(usd_per_euro=1.10)
        usd = self.env.ref("base.USD")
        today = fields.Date.context_today(self.Currencies)
        self.assertAlmostEqual(self.Currencies._ocd_usd_per_euro(self.company), 1.10, places=6)
        with self._bank(1.20):
            self.Currencies._cron_update_usd_rate()
        rate = self.env["res.currency.rate"].search([
            ("currency_id", "=", usd.id), ("company_id", "=", self.company.id), ("name", "=", today),
        ])
        self.assertEqual(len(rate), 1)
        self.assertAlmostEqual(rate.rate, 1.20 / CFA_PER_EURO, places=10)
        self.assertEqual(self._price("usd"), 27)  # 27.44 $
        # The bank does not answer: the last rate is kept
        with self._bank(None):
            self.Currencies._cron_update_usd_rate()
        self.assertAlmostEqual(self.Currencies._ocd_usd_per_euro(self.company), 1.20, places=6)

    def test_no_rate_read_before_the_setup(self):
        with self._bank() as read_mock:
            self.Currencies._cron_update_usd_rate()
        read_mock.assert_not_called()

    def test_setup_without_the_bank(self):
        """The bank does not answer at the setup: the dollar at 1.10 until it answers."""
        self._setup(usd_per_euro=None)
        self.assertAlmostEqual(self.Currencies._ocd_usd_per_euro(self.company), 1.10, places=6)

    def test_reading_of_the_bank(self):
        xml = """<gesmes:Envelope><Cube><Cube time='2026-11-12'>
            <Cube currency='USD' rate='1.1081'/><Cube currency='JPY' rate='170.12'/>
        </Cube></Cube></gesmes:Envelope>"""
        response = type("Response", (), {"text": xml, "raise_for_status": lambda self: None})()
        with patch("odoo.addons.ocd_live.models.ocd_live_currencies.requests.get", return_value=response):
            self.assertEqual(self.Currencies._ocd_read_usd_per_euro(), 1.1081)

    def test_old_rates_of_the_dollar_are_kept(self):
        """The rates of the past days stay: an order of last week keeps its rate."""
        self._setup(usd_per_euro=1.05)
        usd = self.env.ref("base.USD")
        last_week = fields.Date.context_today(self.Currencies) - timedelta(days=7)
        self.env["res.currency.rate"].create({
            "currency_id": usd.id, "company_id": self.company.id, "name": last_week, "rate": 1.02 / CFA_PER_EURO,
        })
        with self._bank(1.20):
            self.Currencies._cron_update_usd_rate()
        old = self.env["res.currency.rate"].search([
            ("currency_id", "=", usd.id), ("company_id", "=", self.company.id), ("name", "=", last_week),
        ])
        self.assertAlmostEqual(old.rate, 1.02 / CFA_PER_EURO, places=10)
