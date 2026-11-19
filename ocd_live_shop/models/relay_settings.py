from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """The relay points on the settings page of OCD Live (chantier 10)."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_relay()]

    @api.model
    def _ocd_section_relay(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        symbol = company.currency_id.symbol
        Place = self.env["ocd.vendor.place"].sudo()
        relays = Place.search_count([("relay", "=", True), ("state", "=", "approved")])
        waiting = Place.search_count([("relay", "=", True), ("state", "=", "to_check")])
        rates = self.env["ocd.delivery.rate"].sudo().search_count([("operator", "=", "relay"),
                                                                   ("company_id", "in", (company.id, False))])
        return {
            "key": "relay",
            "sequence": 33,
            "icon": "PR",
            "label": _("Relay points"),
            "title": _("Relay points: the parcels kept by the shops of the neighbourhood"),
            "items": [
                item("check", "ocd_relay_enabled", _("Relay points"),
                     _("The customers choose a relay point at the delivery step, cheaper than at the door."),
                     span=2),
                item("money", "ocd_relay_fee", _("Earned by a relay point"),
                     _("For each parcel handed over to its customer, nothing for a parcel taken back; paid every month "
                       "with the payouts."), suffix=symbol, min=0, width=100),
                item("group", "ocd_relay_days_group", _("Kept at the relay point"),
                     _("Until the closing of the relay point on the last day; then the parcel goes back."), fields=[
                         item("number", "ocd_relay_days", _("days"), min=1, max=30, width=70),
                         item("number", "ocd_relay_reminder_days", _("reminder before (days)"), min=0, max=10, width=70),
                     ]),
                item("number", "ocd_relay_capacity", _("Places of a new relay point"),
                     _("Full, it is not offered. Changed on the form of each relay point."),
                     suffix=_("parcels"), min=1, max=500, width=70),
                item("check", "ocd_relay_vendor_stores", _("Stores of the vendors as relay points"),
                     _("A vendor whose store is verified and open to the public keeps the parcels of the others, from "
                       "« My stores ».")),
                item("number", "ocd_relay_pause_after", _("Paused after"),
                     _("Parcels lost at a relay point before it is paused for the team. 0: never."),
                     suffix=_("parcels lost"), min=0, max=20, width=70),
                item("info", "ocd_relay_info", _("Relay points and their prices"),
                     _("%(relays)s relay points open, %(waiting)s to visit; %(rates)s rates « relay point ». Without a "
                       "rate for a city, its relay points are not offered.", relays=relays, waiting=waiting, rates=rates),
                     link={"label": _("Relay points"), "action": "ocd_live_shop.ocd_relay_action"}, span=2),
            ],
        }
