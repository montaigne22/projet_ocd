from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """OCD Tickets on the settings page of OCD Live."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_tickets()]

    @api.model
    def _ocd_section_tickets(self):
        _ = self.env._
        item = self._ocd_item
        return {
            "key": "tickets",
            "sequence": 46,
            "icon": "BI",
            "label": _("Tickets (OCD Tickets)"),
            "title": _("Tickets of the events"),
            "items": [
                item("number", "ocd_ticket_organizer_share", _("Share of the organiser"),
                     _("Of the tickets sold, paid after the event; the rest for OCD Live (with the fees of the "
                       "Mobile Money). No fee added for the buyer."), suffix="%", min=0, max=100, width=70),
                item("number", "ocd_ticket_max_per_order", _("Tickets per order"),
                     _("At most, all kinds together."), min=1, max=50, width=70),
                item("number", "ocd_ticket_hold_minutes", _("Seats held during the payment"),
                     _("Past this time, the tickets not paid go back on sale; a payment checked by the team keeps "
                       "them."), suffix=_("minutes"), min=2, max=1440, width=70),
                item("number", "ocd_ticket_sale_end_hours", _("End of the online sales"),
                     _("Hours before the start; 0: at the start. The sale at the door goes on."),
                     suffix=_("hours before"), min=0, max=72, width=70),
                item("number", "ocd_ticket_refund_days", _("Refund on request after a move"),
                     _("A buyer who cannot come at the new date asks for a refund during these days. No refund for a "
                       "buyer who does not come."), suffix=_("days"), min=0, max=60, width=70),
            ],
        }
