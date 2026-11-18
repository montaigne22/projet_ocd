from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_ticket_organizer_share = fields.Float(string="Share Of The Organiser Of An Event (%)", default=90)
    ocd_ticket_max_per_order = fields.Integer(string="Tickets Per Order", default=10)
    ocd_ticket_hold_minutes = fields.Integer(
        string="Seats Held During The Payment", default=10,
        help="Minutes; past them, the tickets not paid are given back for sale (a payment checked by the team "
        "keeps them).",
    )
    ocd_ticket_sale_end_hours = fields.Integer(
        string="End Of The Online Sales", default=0,
        help="Hours before the start of the event; 0: at the start. The sale at the door goes on.",
    )
    ocd_ticket_refund_days = fields.Integer(
        string="Refund On Request After A Move", default=7,
        help="Days after an event is moved during which a buyer who cannot come asks for a refund.",
    )
