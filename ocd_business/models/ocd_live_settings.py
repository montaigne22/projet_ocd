from odoo import api, models

DURATIONS = (
    ("ocd_business.product_business_1", "ocd_business_price_1"),
    ("ocd_business.product_business_3", "ocd_business_price_3"),
    ("ocd_business.product_business_12", "ocd_business_price_12"),
)


class OcdLiveSettings(models.AbstractModel):
    """OCD Business on the settings page of OCD Live (design OcdBusiness, « Réglages »)."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_business()]

    @api.model
    def _ocd_section_business(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        symbol = company.currency_id.symbol
        Partner = self.env["res.partner"].sudo()
        active = Partner.search_count([("ocd_business_until", ">=", company._ocd_local_today())])
        prices = [
            item("money", key, label, suffix=symbol, min=0, width=110, get="_ocd_get_business_price",
                 set="_ocd_set_business_price", args=[xmlid])
            for (xmlid, key), label in zip(DURATIONS, (_("1 month"), _("3 months"), _("12 months")))
        ]
        return {
            "key": "business",
            "sequence": 37,
            "icon": "OB",
            "label": _("OCD Business"),
            "title": _("OCD Business: the monthly formula of the organised vendors"),
            "items": [
                item("group", "ocd_business_prices", _("Prices"),
                     _("Paid in advance, never debited; in the currency of each country, as the directory pass. A price "
                       "changed counts for the next payments."), fields=prices),
                item("date", "ocd_business_launch_date", _("Launch"),
                     _("This day, the features offered to all stop (« OCD Business features offered to all », section "
                       "Stores); the vendors who use them receive the months below first.")),
                item("number", "ocd_business_launch_months", _("Months offered at the launch"),
                     _("To the vendors with several stores or a team, once."), suffix=_("months"), min=0, max=12, width=70),
                item("number", "ocd_business_reminder_days", _("First reminder"),
                     _("Then the day before; once per date of end, never after a renewal."), suffix=_("days before"),
                     min=1, max=30, width=70),
                item("number", "ocd_business_grace_days", _("Grace for a payment checked"),
                     _("« I paid » for a Mobile Money checked by the team: the features stay this long after the end."),
                     suffix=_("days"), min=0, max=10, width=70),
                item("info", "ocd_business_info", _("The formulas"),
                     _("%s vendors with a formula running.", active),
                     link={"label": _("OCD Business"), "action": "ocd_business.ocd_business_period_action"}, span=2),
            ],
        }

    def _ocd_get_business_price(self, xmlid):
        return self._ocd_product_price(xmlid)

    def _ocd_set_business_price(self, xmlid, price):
        self._ocd_set_product_price(xmlid, price)
