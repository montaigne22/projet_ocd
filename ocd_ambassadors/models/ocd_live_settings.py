from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """The ambassadors on the settings page of OCD Live (design Ambassadeurs, « Réglages »)."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_ambassadors()]

    @api.model
    def _ocd_section_ambassadors(self):
        _ = self.env._
        company = self.env.company
        item = self._ocd_item
        symbol = company.currency_id.symbol
        Partner = self.env["res.partner"].sudo()
        active = Partner.search_count([("ocd_ambassador_state", "=", "active")])
        waiting = Partner.search_count([("ocd_ambassador_state", "in", ("to_check", "paused", "requested"))])
        return {
            "key": "ambassadors",
            "sequence": 38,
            "icon": "AM",
            "label": _("Ambassadors"),
            "title": _("Ambassadors: the sales brought by their shares"),
            "items": [
                item("select", "ocd_ambassador_open", _("The program"),
                     _("Closed: no new gain, the gains already due are paid."),
                     options=self._ocd_selection_options("ocd_ambassador_open")),
                item("number", "ocd_ambassador_rate", _("Gain on the articles"),
                     _("Not on the delivery; never more than the commission of OCD on the article. Paid by OCD: the "
                       "customer pays the same price, the vendor pays nothing."), suffix="%", min=0, max=50, width=70),
                item("money", "ocd_ambassador_cap", _("At most per parcel"), _("0: no cap."), suffix=symbol, min=0,
                     width=100),
                item("group", "ocd_ambassador_days", _("The link and the confirmation"),
                     _("The last link opened on the phone counts; the gain is confirmed after the delivery with the "
                       "code, a return later is taken from the next payout."), fields=[
                         item("number", "ocd_ambassador_link_days", _("days the link counts"), min=1, max=60, width=70),
                         item("number", "ocd_ambassador_confirm_days", _("days after the delivery"), min=0, max=60,
                              width=70),
                     ]),
                item("money", "ocd_ambassador_min_payout", _("Paid every week from"),
                     _("On the payout day of the shop, on their Mobile Money; below, it waits."), suffix=symbol, min=0,
                     width=100),
                item("money", "ocd_ambassador_id_above", _("Identity seen above"),
                     _("Gains since the start: the team sees an identity document once before the next payout. 0: "
                       "never."), suffix=symbol, min=0, width=100),
                item("group", "ocd_ambassador_pause", _("Paused by itself above"),
                     _("Parcels refused at the door or returned: the links still work, nothing is earned, the gains due "
                       "are kept. 0: never."), fields=[
                         item("number", "ocd_ambassador_pause_rate", _("% of returns"), min=0, max=100, width=70),
                         item("number", "ocd_ambassador_pause_min", _("on parcels at least"), min=1, max=500, width=70),
                     ]),
                item("number", "ocd_ambassador_customer_month", _("Orders of a customer per month"),
                     _("The orders of the same customer that count for the same ambassador. 0: no limit."),
                     min=0, max=100, width=70),
                item("number", "ocd_ambassador_momo_hold_hours", _("New payout number: wait"),
                     _("The number of the account is told on WhatsApp."), suffix=_("hours"), min=0, max=240, width=70),
                item("info", "ocd_ambassador_info", _("The ambassadors"),
                     _("%(active)s ambassadors active, %(waiting)s waiting for the team.", active=active, waiting=waiting),
                     link={"label": _("Ambassadors"), "action": "ocd_ambassadors.res_partner_action_ocd_ambassador"},
                     span=2),
            ],
        }
