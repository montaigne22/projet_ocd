from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_vote_price = fields.Monetary(
        string="Price Of A Vote", currency_field="currency_id", default=100,
        help="For a new contest; changed on the contest before its opening.",
    )
    ocd_vote_pack1_votes = fields.Integer(string="First Pack: Votes", default=10)
    ocd_vote_pack1_price = fields.Monetary(string="First Pack: Price", currency_field="currency_id", default=900)
    ocd_vote_pack2_votes = fields.Integer(string="Second Pack: Votes", default=50)
    ocd_vote_pack2_price = fields.Monetary(string="Second Pack: Price", currency_field="currency_id", default=4000)
    ocd_vote_organizer_share = fields.Float(string="Share Of The Organiser (%)", default=60)
    ocd_vote_pay_minutes = fields.Integer(
        string="Time To Pay The Votes", default=10,
        help="Minutes; past them, votes not paid are cancelled (a payment checked by the team keeps waiting).",
    )
    ocd_vote_hide_hours = fields.Integer(
        string="Ranking Hidden The Last Hours", default=2,
        help="For a new contest: the order stays, the numbers are hidden until the results. 0: always shown.",
    )

    def _ocd_vote_default_packs(self):
        """[(votes, price)] of the packs of a new contest."""
        self.ensure_one()
        packs = [(self.ocd_vote_pack1_votes, self.ocd_vote_pack1_price),
                 (self.ocd_vote_pack2_votes, self.ocd_vote_pack2_price)]
        return [(votes, price) for votes, price in packs if votes and votes > 1 and price and price > 0]
