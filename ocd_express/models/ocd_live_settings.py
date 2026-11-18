from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """OCD Express on the settings page of OCD Live: prices, rules of the money, couriers."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_express()]

    @api.model
    def _ocd_section_express(self):
        _ = self.env._
        item = self._ocd_item
        symbol = self.env.company.currency_id.symbol
        return {
            "key": "express",
            "sequence": 36,
            "icon": "EX",
            "label": _("OCD Express"),
            "title": _("OCD Express: the parcels of the vendors of the social networks"),
            "items": [
                item("select", "ocd_express_open_to", _("Open to"),
                     _("Invited: a request goes to the team. Everybody: the account opens with the number checked."),
                     options=self._ocd_selection_options("ocd_express_open_to")),
                item("chips", "ocd_express_city_ids", _("Cities open"),
                     _("Chosen on the company (Settings › Companies); the price is the rate « OCD courier » of the "
                       "city, elsewhere by travel agency, paid in advance."),
                     chips=self.env.company.ocd_express_city_ids.mapped("name") or [_("No city yet")]),
                item("group", "ocd_express_cod", _("Collecting at the door"),
                     _("Of the money collected for the sender; nothing for a parcel already paid."), fields=[
                         item("number", "ocd_express_cod_rate", "%", min=0, max=20, width=70),
                         item("money", "ocd_express_cod_min", _("at least"), suffix=symbol, min=0, width=90),
                     ]),
                item("group", "ocd_express_fees", _("Return and small pick-up"),
                     _("The second passage at the customer is free; the drop-off at the OCD point too."), fields=[
                         item("money", "ocd_express_return_fee", _("return"), suffix=symbol, min=0, width=90),
                         item("money", "ocd_express_pickup_fee", _("pick-up"), suffix=symbol, min=0, width=90),
                         item("number", "ocd_express_pickup_free_from", _("free from"), suffix=_("parcels"),
                              min=1, max=50, width=70),
                     ]),
                item("group", "ocd_express_caps", _("To collect at most per parcel"),
                     _("Above, the team checks the parcel before it leaves."), fields=[
                         item("money", "ocd_express_cap_new", _("new sender"), suffix=symbol, min=0, width=100),
                         item("money", "ocd_express_cap_confirmed", _("then"), suffix=symbol, min=0, width=100),
                         item("number", "ocd_express_cap_after", _("after"), suffix=_("parcels"), min=0, max=500, width=70),
                     ]),
                item("money", "ocd_express_online_above", _("On the phone only above"),
                     _("The customer pays on their phone, never in cash. 0: never."), suffix=symbol, min=0, width=100),
                item("money", "ocd_express_cash_max", _("Cash on a courier at most"),
                     _("Above, they drop their cash at the OCD point first. 0: no limit."), suffix=symbol, min=0, width=100),
                item("money", "ocd_express_debt_max", _("Owed by a sender at most"),
                     _("Above, they pay it before a new parcel, or their customer pays the delivery."),
                     suffix=symbol, min=0, width=100),
                item("money", "ocd_express_id_daily", _("Identity checked above"),
                     _("Money to collect in a day by a sender whose identity was not checked. 0: never."),
                     suffix=symbol, min=0, width=100),
                item("group", "ocd_express_waves", _("Waves"),
                     _("Created before the first hour: delivered the afternoon; before the second: the next morning."),
                     fields=[
                         item("time", "ocd_express_wave1_hour", _("morning before"), max=23.99, before=True),
                         item("time", "ocd_express_wave2_hour", _("afternoon before"), max=23.99, before=True),
                     ]),
                item("group", "ocd_express_capacity", _("Capacity of the couriers"),
                     _("Pick-ups included; the share kept for the parcels of the shop. 0: no limit."), fields=[
                         item("number", "ocd_express_per_courier", _("parcels a day"), min=0, max=200, width=70),
                         item("number", "ocd_express_shop_share", _("kept for the shop"), suffix="%", min=0, max=100,
                              width=70),
                     ]),
                item("number", "ocd_express_claim_hours", _("Problem reported within"),
                     _("After the delivery: the money of the parcel waits for the answer of the team."),
                     suffix=_("hours"), min=0, max=720, width=70),
                item("money", "ocd_express_lost_max", _("Lost or damaged: paid at most"),
                     _("The declared value; never the content."), suffix=symbol, min=0, width=100),
                item("number", "ocd_express_return_alert", _("Returns: alert at"),
                     _("On 30 days, from 10 parcels: a warning, then the suspension. 0: never."),
                     suffix="%", min=0, max=100, width=70),
                item("number", "ocd_express_momo_hold_hours", _("New payout number: wait"),
                     _("The old number is told."), suffix=_("hours"), min=0, max=240, width=70),
                item("number", "ocd_express_retention_months", _("Customers erased after"),
                     _("Name, number, address; the amounts stay. 0: never."), suffix=_("months"), min=0, max=120,
                     width=70),
                item("text", "ocd_express_point", _("OCD point"),
                     _("Where the senders drop their parcels and the couriers their cash.")),
                item("text", "ocd_express_momo_number", _("Mobile Money of OCD"),
                     _("Where a sender sends what they owe, with their reference.")),
            ],
        }

    @api.model
    def _ocd_check_values(self, values):
        errors = super()._ocd_check_values(values)
        first, second = values.get("ocd_express_wave1_hour"), values.get("ocd_express_wave2_hour")
        if first is not None and second is not None and first >= second:
            errors["ocd_express_wave2_hour"] = self.env._("The afternoon wave comes after the morning wave.")
        return errors
