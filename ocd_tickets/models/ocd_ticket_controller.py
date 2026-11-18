from odoo import api, fields, models


class OcdTicketController(models.Model):
    """A controller of an event, added by its organiser: they log in with their number (a code on
    WhatsApp) and scan the tickets at their gate with the camera of their phone. They may sell at
    the door when the organiser allows it; their cash is counted with them at the end of the
    evening, like the cash of the couriers."""

    _name = "ocd.ticket.controller"
    _description = "Controller Of An Event"
    _order = "event_id, gate, name, id"

    event_id = fields.Many2one(comodel_name="event.event", required=True, index=True, ondelete="cascade")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact", required=True, index=True,
                                 ondelete="restrict")
    name = fields.Char(required=True)
    phone = fields.Char(related="partner_id.phone", string="WhatsApp")
    gate = fields.Char(string="Gate", help="« Gate 1 »: shown on the entries let in.")
    can_sell = fields.Boolean(string="Sells At The Door", help="When the organiser allows the sale at the door.")
    active = fields.Boolean(default=True)
    entered_count = fields.Integer(string="Let In", compute="_compute_counts")
    cash_amount = fields.Monetary(string="Cash To Collect", compute="_compute_counts", currency_field="currency_id")
    currency_id = fields.Many2one(related="event_id.company_id.currency_id")

    _unique_controller = models.UniqueIndex("(event_id, partner_id)", "This contact already controls this event.")

    def _compute_counts(self):
        Registration = self.env["event.registration"].sudo()
        entered = dict(Registration._read_group(
            [("ocd_controller_id", "in", self.ids), ("state", "=", "done")], ["ocd_controller_id"], ["__count"]
        ))
        orders = self.env["sale.order"].sudo().search([
            ("ocd_ticket_controller_id", "in", self.ids), ("ocd_ticket_cash_state", "=", "to_collect"),
        ])
        for controller in self:
            controller.entered_count = entered.get(controller, 0)
            controller.cash_amount = sum(
                orders.filtered(lambda order: order.ocd_ticket_controller_id == controller)
                .mapped("ocd_ticket_amount_company")
            )

    @api.depends("name", "gate")
    def _compute_display_name(self):
        for controller in self:
            controller.display_name = " · ".join(part for part in (controller.name, controller.gate) if part)

    @api.model
    def _ocd_of_partner(self, partner):
        """The controls of `partner`, active, for events on sale."""
        return self.sudo().search([
            ("partner_id", "=", partner.id), ("event_id.ocd_state", "=", "approved"),
        ])

    @api.model
    def _ocd_find_by_phone(self, phone):
        """The contact of the controllers whose number ends like `phone`, for the login page."""
        partners = self.sudo().search([("event_id.ocd_state", "=", "approved")]).partner_id
        return self.env["res.partner"]._ocd_find_by_phone(phone, [("id", "in", partners.ids)])

    def _ocd_line(self):
        """« Gate 1 · sells at the door », « Gate 2 · control only »."""
        self.ensure_one()
        what = self.env._("sells at the door") if self.can_sell and self.event_id.ocd_door_sale else self.env._(
            "control only")
        return " · ".join(part for part in (self.gate, what) if part)

    def action_ocd_cash_collected(self):
        """The cash of the door counted with the controller."""
        orders = self.env["sale.order"].sudo().search([
            ("ocd_ticket_controller_id", "in", self.ids), ("ocd_ticket_cash_state", "=", "to_collect"),
        ])
        orders.write({"ocd_ticket_cash_state": "collected"})
        for order in orders:
            order.message_post(body=self.env._("Cash collected by %s.", self.env.user.name))
        return True

    def _ocd_tell_added(self):
        """Hook: tell the controller they were added (ocd_tickets_whatsapp)."""
