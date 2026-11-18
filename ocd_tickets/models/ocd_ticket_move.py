from odoo import fields, models


class OcdTicketMove(models.TransientModel):
    """« Move »: the new date of an event; the tickets stay valid, the buyers are told and may ask
    for a refund for a few days."""

    _name = "ocd.ticket.move"
    _description = "Move An Event"

    event_id = fields.Many2one(comodel_name="event.event", required=True)
    date_begin = fields.Datetime(string="New Start", required=True)
    date_end = fields.Datetime(string="New End", required=True)
    doors_at = fields.Datetime(string="Doors Open At")

    def action_move(self):
        self.ensure_one()
        self.event_id._ocd_move(self.date_begin, self.date_end, self.doors_at)
        return {"type": "ir.actions.act_window_close"}
