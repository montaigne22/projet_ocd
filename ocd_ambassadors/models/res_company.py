from odoo import fields, models

OPEN_TO = [
    ("all", "Everybody"),
    ("invited", "Invited by the team"),
    ("closed", "Closed"),
]


class ResCompany(models.Model):
    """The rules of the ambassadors (chantier 11, design Ambassadeurs), on the settings page of
    OCD Live. A rule changed counts for the orders that come after: the rate and the cap are
    written on each order when it is confirmed."""

    _inherit = "res.company"

    ocd_ambassador_open = fields.Selection(
        selection=OPEN_TO, string="Ambassadors: Program", default="all", required=True,
        help="Everybody: the account opens once the number is checked. Invited: the team opens it. Closed: no new "
             "gain (the gains already due are paid).",
    )
    ocd_ambassador_rate = fields.Float(
        string="Ambassadors: Gain (%)", default=5.0,
        help="Of the articles of the order (not the delivery), never more than the commission of OCD on the article.",
    )
    ocd_ambassador_cap = fields.Float(string="Ambassadors: At Most Per Parcel", default=3000.0, help="0: no cap.")
    ocd_ambassador_link_days = fields.Integer(
        string="Ambassadors: The Link Counts (Days)", default=7,
        help="An order placed this long after the link was opened counts for the ambassador (the last link opened).",
    )
    ocd_ambassador_confirm_days = fields.Integer(
        string="Ambassadors: Confirmed After (Days)", default=7,
        help="After the delivery with the code: the gain is then paid. A return later is taken from the next payout.",
    )
    ocd_ambassador_min_payout = fields.Float(
        string="Ambassadors: Minimum Payout", default=2000.0,
        help="Below, the gains wait for the next payout day.",
    )
    ocd_ambassador_id_above = fields.Float(
        string="Ambassadors: Identity Checked Above", default=50000.0,
        help="Gains confirmed since the start: above, the team sees an identity document before the next payout. "
             "0: never.",
    )
    ocd_ambassador_pause_rate = fields.Integer(
        string="Ambassadors: Paused Above (% Of Returns)", default=30,
        help="Parcels refused at the door or returned, on the last parcels of the ambassador. 0: never.",
    )
    ocd_ambassador_pause_min = fields.Integer(
        string="Ambassadors: Paused From (Parcels)", default=10,
        help="The rate of returns counts from this number of parcels.",
    )
    ocd_ambassador_customer_month = fields.Integer(
        string="Ambassadors: Orders Of A Customer Per Month", default=5,
        help="The orders of the same customer that count for the same ambassador in a month. 0: no limit.",
    )
    ocd_ambassador_momo_hold_hours = fields.Integer(
        string="Ambassadors: New Payout Number Waits (Hours)", default=48,
        help="Before the first payout on a new number; the number of the account is told on WhatsApp.",
    )
