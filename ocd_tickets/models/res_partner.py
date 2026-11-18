from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # The same account organises contests (OCD Vote) and events (OCD Tickets)
    ocd_vote_organizer = fields.Boolean(
        string="Organiser (Contests And Events)",
        help="Logs in with their number on /vote/organisateur, like the vendors: their contests and their events.",
    )
    ocd_ticket_event_ids = fields.One2many(
        comodel_name="event.event", inverse_name="ocd_organizer_id", string="Events"
    )
    ocd_ticket_controller_ids = fields.One2many(
        comodel_name="ocd.ticket.controller", inverse_name="partner_id", string="Controls Of Events"
    )

    def action_ocd_view_events(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ocd_tickets.event_event_action_ocd")
        action["domain"] = [("ocd_organizer_id", "=", self.id)]
        action["context"] = {"default_ocd_organizer_id": self.id, "default_ocd_ticketing": True}
        return action
