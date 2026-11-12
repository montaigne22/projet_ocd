"""The currencies by country: the prices are written in the currency of the company (XOF), each
country sees them, books and pays in its own currency, by the pricelists of Odoo:

- XOF: the 8 countries of the UEMOA (West Africa);
- XAF: the 6 countries of the CEMAC (Central Africa; Campay takes XAF only);
- EUR: Europe, the rest of Africa, and the French departments beyond Europe;
- USD: the Americas, Asia and Oceania.

The CFA francs are fixed to the euro (1 € = 655.957 F since 1999): XOF and XAF are worth the
same, and the euro never moves. The dollar is read every day from the European Central Bank
(EUR → USD), then through the euro. The prices in euros and in dollars are rounded to the unit
(15 000 F → 23 € and 25 $), the prices in francs stay as they are."""

import logging
import re
from collections import defaultdict
from datetime import date

import requests

from odoo import Command, api, fields, models
from odoo.tools.misc import format_amount, format_date, formatLang

from .. import countries

_logger = logging.getLogger(__name__)

CFA_PER_EURO = 655.957
UEMOA = ("BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG")
CEMAC = ("CM", "CF", "TD", "CG", "GQ", "GA")
# France beyond Europe (Guadeloupe, Martinique, Guiana, Reunion, Mayotte...): the euro
EURO_ABROAD = ("GP", "MQ", "GF", "RE", "YT", "PM", "BL", "MF")
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
USD_PER_EURO = 1.10  # until the first reading of the bank
PARITY_DATE = date(1999, 1, 1)
ZONES = ("xof", "xaf", "eur", "usd")
ZONE_CURRENCY = {"xof": "XOF", "xaf": "XAF", "eur": "EUR", "usd": "USD"}
ROUNDED_ZONES = ("eur", "usd")
EURO_BLOCK = ("XOF", "XAF", "EUR")  # fixed to each other; the dollar moves every day


def zone_of(code):
    """The currency zone of the country `code` (ISO): xof, xaf, eur or usd."""
    code = (code or "").upper()
    if code in UEMOA:
        return "xof"
    if code in CEMAC:
        return "xaf"
    if code in EURO_ABROAD:
        return "eur"
    return "eur" if countries.continent(code) in ("africa", "europe") else "usd"


def euro_value(currency_name, usd_per_euro):
    """What one unit of `currency_name` is worth in euros; None for another currency."""
    return {
        "XOF": 1 / CFA_PER_EURO,
        "XAF": 1 / CFA_PER_EURO,
        "EUR": 1.0,
        "USD": 1 / usd_per_euro,
    }.get(currency_name)


class OcdLiveCurrencies(models.AbstractModel):
    _name = "ocd.live.currencies"
    _description = "Currencies Of The Countries"

    @api.model
    def _ocd_zone_names(self):
        _ = self.env._
        return {
            "xof": _("West Africa (XOF)"),
            "xaf": _("Central Africa (XAF)"),
            "eur": _("Europe and the rest of Africa (EUR)"),
            "usd": _("Americas, Asia and Oceania (USD)"),
        }

    # === SETUP === #

    @api.model
    def _ocd_setup(self, company=None):
        """Put the currencies by country in place, or again (the countries of the zones, the
        rates, the rounding): the currencies, the rates of the francs and of the euro (fixed),
        the dollar of the day, the pricelists of the four zones with their countries."""
        company = company or self.env.company
        currencies = self._ocd_currencies()
        currencies.filtered(lambda currency: not currency.active).write({"active": True})
        usd_per_euro = self._ocd_read_usd_per_euro() or self._ocd_usd_per_euro(company) or USD_PER_EURO
        self._ocd_set_rates(company, usd_per_euro)
        # The pricelists of Odoo, used by the pages and the shop
        self.env.ref("base.group_user").sudo()._apply_group(self.env.ref("product.group_product_pricelist"))
        self = self.with_context(lang="en_US")  # noqa: PLW0642 (the names in English, then translated)
        names = self._ocd_zone_names()
        by_zone = defaultdict(list)
        for country in self.env["res.country"].sudo().search([]):
            by_zone[zone_of(country.code)].append(country.id)
        pricelists = self.env["product.pricelist"]
        for sequence, zone in enumerate(ZONES, start=1):
            group = self._ocd_record(f"country_group_{zone}", "res.country.group", {"name": names[zone]}, zone)
            group.write({"country_ids": [Command.set(by_zone[zone])]})
            currency = currencies.filtered(lambda c, name=ZONE_CURRENCY[zone]: c.name == name)
            pricelist = self._ocd_record(f"pricelist_{zone}", "product.pricelist", {
                "name": names[zone], "company_id": company.id, "currency_id": currency.id,
            }, zone)
            pricelist.write({
                "currency_id": currency.id,
                "country_group_ids": [Command.set(group.ids)],
                "sequence": sequence,
                "active": True,
            })
            if zone in ROUNDED_ZONES:
                self._ocd_rounding(pricelist)
            pricelists |= pricelist
        return pricelists

    @api.model
    def _ocd_currencies(self):
        Currency = self.env["res.currency"].sudo().with_context(active_test=False)
        return Currency.search([("name", "in", list(ZONE_CURRENCY.values()))])

    @api.model
    def _ocd_record(self, name, model, vals, zone):
        """The record `name` of OCD Live (xmlid), created the first time with the name of the
        zone in each language (the team may rename it after)."""
        record = self.env.ref(f"ocd_live.{name}", raise_if_not_found=False)
        if record:
            return record.sudo()
        record = self.env[model].sudo().create(vals)
        self.env["ir.model.data"].sudo().create({
            "module": "ocd_live", "name": name, "model": model, "res_id": record.id, "noupdate": True,
        })
        self._ocd_translate_name(record, zone)
        return record

    @api.model
    def _ocd_translate_name(self, record, zone):
        """The name of the zone `zone` on `record` in each language of the database."""
        for code, _label in self.env["res.lang"].get_installed():
            if code != "en_US":
                record.with_context(lang=code).name = self.with_context(lang=code)._ocd_zone_names()[zone]

    @api.model
    def _ocd_rounding(self, pricelist):
        """Every price of the pricelist from the sales price, converted and rounded to the unit."""
        rule = pricelist.item_ids.filtered(lambda item: item.applied_on == "3_global")[:1]
        vals = {"applied_on": "3_global", "base": "list_price", "compute_price": "discount",
                "price_discount": 0, "price_round": 1.0, "price_surcharge": 0}
        if rule:
            rule.write(vals)
        else:
            self.env["product.pricelist.item"].sudo().create({"pricelist_id": pricelist.id, **vals})

    # === RATES === #

    @api.model
    def _ocd_set_rates(self, company, usd_per_euro):
        """The rates of the currencies for `company`: the francs and the euro at their parity
        (also over a wrong rate typed before), the dollar of the day (for a company in dollars,
        the francs and the euro of the day)."""
        company = company.root_id  # the rates are the ones of the main company
        base = euro_value(company.currency_id.name, usd_per_euro)
        if base is None:
            _logger.info("OCD Live: company in %s: the rates are kept as they are.", company.currency_id.name)
            return
        Rate = self.env["res.currency.rate"].sudo()
        today = fields.Date.context_today(self)
        for currency in self._ocd_currencies():
            if currency == company.currency_id:
                continue
            rate = base / euro_value(currency.name, usd_per_euro)
            if currency.name in EURO_BLOCK and company.currency_id.name in EURO_BLOCK:
                # Fixed: from 1999, and over every rate typed before
                days = sorted({PARITY_DATE, *Rate.search([
                    ("currency_id", "=", currency.id), ("company_id", "=", company.id),
                ]).mapped("name")})
            else:
                days = [today]
            for day in days:
                existing = Rate.search([
                    ("currency_id", "=", currency.id), ("company_id", "=", company.id), ("name", "=", day),
                ], limit=1)
                if existing:
                    existing.rate = rate
                else:
                    Rate.create({"currency_id": currency.id, "company_id": company.id, "name": day, "rate": rate})

    @api.model
    def _ocd_read_usd_per_euro(self):
        """The dollars for one euro of the day, from the European Central Bank (None when it does
        not answer)."""
        try:
            response = requests.get(ECB_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            _logger.info("OCD Live: rate of the dollar not read: %s", error)
            return None
        match = re.search(r"""currency=['"]USD['"]\s+rate=['"]([0-9.]+)['"]""", response.text)
        return float(match[1]) if match else None

    @api.model
    def _ocd_last_usd_rate(self, company):
        """The last rate of the dollar against the euro of `company`: the one of the dollar (of
        the euro for a company in dollars), else an empty record."""
        company = company.root_id
        name = "EUR" if company.currency_id.name == "USD" else "USD"
        currency = self._ocd_currencies().filtered(lambda c: c.name == name)
        return self.env["res.currency.rate"].sudo().search([
            ("currency_id", "=", currency.id), ("company_id", "=", company.id),
        ], order="name desc", limit=1)

    @api.model
    def _ocd_usd_per_euro(self, company):
        """The dollars for one euro of the last rate of `company`, else None."""
        company = company.root_id
        rate = self._ocd_last_usd_rate(company)
        if not rate or euro_value(company.currency_id.name, 1.0) is None:
            return None
        currencies = self._ocd_currencies()
        eur = currencies.filtered(lambda c: c.name == "EUR")
        usd = currencies.filtered(lambda c: c.name == "USD")
        return self.env["res.currency"]._get_conversion_rate(eur, usd, company, rate.name)

    @api.model
    def _cron_update_usd_rate(self):
        """Every day: the dollar of the day, for the companies whose currencies by country are
        in place."""
        if not self.env.ref("ocd_live.pricelist_usd", raise_if_not_found=False):
            return
        usd_per_euro = self._ocd_read_usd_per_euro()
        if not usd_per_euro:
            return
        for company in self.env["res.company"].sudo().search([("parent_id", "=", False)]):
            if euro_value(company.currency_id.name, usd_per_euro) is not None:
                self._ocd_set_rates(company, usd_per_euro)

    # === WHAT THE SETTINGS SHOW === #

    @api.model
    def _ocd_is_set_up(self):
        return bool(self.env.ref("ocd_live.pricelist_xaf", raise_if_not_found=False))

    @api.model
    def _ocd_zone_chips(self):
        """« Central Africa (XAF) · 6 countries » for each zone in place."""
        names = self._ocd_zone_names()
        chips = []
        for zone in ZONES:
            group = self.env.ref(f"ocd_live.country_group_{zone}", raise_if_not_found=False)
            if group:
                count = len(group.sudo().country_ids)
                chips.append(self.env._("%(zone)s · %(count)s countries", zone=names[zone], count=count))
        return chips

    @api.model
    def _ocd_rates_text(self, company):
        _ = self.env._
        company = company.root_id
        if euro_value(company.currency_id.name, USD_PER_EURO) is None:
            return _("The company is in %s: the rates are typed on the currencies.", company.currency_id.name)
        fixed = _("XAF = XOF and 1 € = 655.957 F CFA: fixed since 1999.")
        rate = self._ocd_last_usd_rate(company)
        usd_per_euro = self._ocd_usd_per_euro(company)
        if not rate or not usd_per_euro:
            return fixed
        return _(
            "%(fixed)s The dollar: 1 € = %(usd)s $ on %(day)s, from the European Central Bank.",
            fixed=fixed, usd=formatLang(self.env, usd_per_euro, digits=4), day=format_date(self.env, rate.name),
        )

    @api.model
    def _ocd_example_text(self):
        """« Discovery: 15 000 CFA → 15 000 FCFA · 23 € · 25 $ »."""
        product = self.env.ref("ocd_live.product_package_discovery", raise_if_not_found=False)
        if not product:
            return ""
        product = product.sudo()
        written = format_amount(self.env, product.list_price, product.currency_id)
        return self.env._(
            "%(product)s: %(written)s → %(prices)s.",
            product=product.name, written=written, prices=self._ocd_example(product),
        )

    @api.model
    def _ocd_example(self, product):
        """« 15 000 FCFA · 23 € · 25 $ »: the price of `product` in the zones of another
        currency than its own."""
        parts = []
        for zone in ZONES:
            pricelist = self.env.ref(f"ocd_live.pricelist_{zone}", raise_if_not_found=False)
            if pricelist and pricelist.currency_id != product.currency_id:
                price = pricelist.sudo()._get_product_price(product, 1.0)
                parts.append(format_amount(self.env, price, pricelist.currency_id, trailing_zeroes=False))
        return " · ".join(parts)
