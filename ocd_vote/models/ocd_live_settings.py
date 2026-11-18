from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """OCD Vote on the settings page of OCD Live: the defaults of a new contest."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_votes()]

    @api.model
    def _ocd_section_votes(self):
        _ = self.env._
        item = self._ocd_item
        symbol = self.env.company.currency_id.symbol
        return {
            "key": "votes",
            "sequence": 45,
            "icon": "VO",
            "label": _("Votes (OCD Vote)"),
            "title": _("Votes of the contests"),
            "items": [
                item("money", "ocd_vote_price", _("Price of a vote"),
                     _("For a new contest; changed on the contest before its opening. No free votes."),
                     suffix=symbol, min=1, width=90),
                item("group", "ocd_vote_pack1", _("First pack"), _("Votes bought together, a little cheaper."), fields=[
                    item("number", "ocd_vote_pack1_votes", _("votes for"), min=0, max=10000, width=70),
                    item("money", "ocd_vote_pack1_price", symbol, min=0, width=90),
                ]),
                item("group", "ocd_vote_pack2", _("Second pack"), _("0 votes: no second pack."), fields=[
                    item("number", "ocd_vote_pack2_votes", _("votes for"), min=0, max=10000, width=70),
                    item("money", "ocd_vote_pack2_price", symbol, min=0, width=90),
                ]),
                item("number", "ocd_vote_organizer_share", _("Share of the organiser"),
                     _("Of the money collected, paid after the results; the rest for OCD Live (with the fees of "
                       "the Mobile Money)."), suffix="%", min=0, max=100, width=70),
                item("number", "ocd_vote_hide_hours", _("Ranking hidden at the end"),
                     _("The order stays, the numbers are hidden until the results: the suspense of the final. "
                       "0: always shown."), suffix=_("last hours"), min=0, max=72, width=70),
                item("number", "ocd_vote_pay_minutes", _("Time to pay the votes"),
                     _("Past it, the votes not paid are cancelled; a payment checked by the team keeps waiting."),
                     suffix=_("minutes"), min=2, max=1440, width=70),
            ],
        }
