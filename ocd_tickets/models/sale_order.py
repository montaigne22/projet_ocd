import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    """An order of tickets: its lines are the kinds of tickets (event_sale); the tickets are created
    when its payment confirms it, never before. Its seats are held while it is paid."""

    _inherit = "sale.order"

    ocd_ticket_event_id = fields.Many2one(
        comodel_name="event.event", string="Event Of The Tickets", index="btree_not_null", readonly=True, copy=False
    )
    ocd_ticket_holder_name = fields.Char(string="Name On The Tickets", copy=False)
    ocd_ticket_source = fields.Selection(
        selection=[("page", "Page"), ("live", "During a live"), ("door", "At the door")],
        string="Tickets Sold", copy=False, readonly=True,
    )
    ocd_ticket_live_id = fields.Many2one(
        comodel_name="ocd.live.booking", string="Sold During The Live", copy=False, readonly=True
    )
    ocd_ticket_controller_id = fields.Many2one(
        comodel_name="ocd.ticket.controller", string="Sold At The Door By", copy=False, readonly=True
    )
    ocd_ticket_cash_state = fields.Selection(
        selection=[("none", "No cash"), ("to_collect", "Cash to collect"), ("collected", "Cash collected"),
                   ("lost", "Cash not received")],
        string="Cash At The Door", default="none", copy=False, tracking=True,
    )
    ocd_ticket_hold_until = fields.Datetime(string="Seats Held Until", copy=False, readonly=True)
    ocd_ticket_amount_company = fields.Monetary(
        string="Amount Of The Tickets", currency_field="ocd_ticket_currency_id", copy=False, readonly=True,
        help="In the currency of the company.",
    )
    ocd_ticket_currency_id = fields.Many2one(related="company_id.currency_id", string="Currency Of The Company")
    ocd_ticket_registration_ids = fields.One2many(
        comodel_name="event.registration", inverse_name="sale_order_id", string="Tickets"
    )
    ocd_ticket_token = fields.Char(string="Secret Of My Tickets", copy=False, groups="base.group_system")

    # === BUY === #

    @api.model
    def _ocd_ticket_create(self, event, quantities, partner, name, source="page", controller=None):
        """`partner` buys tickets of `event`: {ticket: quantity}. The order to pay, its seats held
        for the time to pay (setting)."""
        event = event.sudo()
        env = self.env
        company = event.company_id
        now = fields.Datetime.now()
        if source == "door":
            if not (controller and controller.can_sell and event._ocd_door_open(now)):
                raise UserError(env._("The sale at the door is not open for this event."))
        elif not event._ocd_on_sale(now):
            raise UserError(env._("The tickets of %s are not on sale.", event.name))
        quantities = {ticket: int(count or 0) for ticket, count in quantities.items() if int(count or 0) > 0}
        if not quantities:
            raise UserError(env._("Choose at least one ticket."))
        total = sum(quantities.values())
        most = max(company.ocd_ticket_max_per_order, 1)
        if total > most:
            raise UserError(env._("%s tickets at most per order.", most))
        left = event._ocd_left()
        for ticket, count in quantities.items():
            if ticket.event_id != event:
                raise UserError(env._("This ticket is not for this event."))
            available = left.get(ticket.id)
            if available is not None and count > available:
                raise UserError(env._("Only %(left)s « %(kind)s » tickets left.", left=available, kind=ticket.name)
                                if available else env._("« %s » is sold out.", ticket.name))
        if event.seats_limited and total > max(event.seats_available - sum(event._ocd_held().values()), 0):
            raise UserError(env._("Not enough seats left for %s tickets.", total))
        live = event._ocd_live_now(now) if source != "door" else event.browse()
        if live and source == "page":
            source = "live"
        lines, amount = [], 0.0
        for ticket, count in sorted(quantities.items(), key=lambda item: item[0].sequence):
            ticket._ocd_ensure_product()
            price = ticket._ocd_price(live=live)
            amount += price * count
            lines.append((ticket, count, price))
        order = self.sudo().with_company(company).create({
            "partner_id": partner.id,
            "company_id": company.id,
            "require_signature": False,
            # A positive prepayment makes the payment form ask for the payment of the order
            "prepayment_percent": 1.0,
            "ocd_ticket_event_id": event.id,
            "ocd_ticket_holder_name": name or partner.name,
            "ocd_ticket_source": source,
            "ocd_ticket_live_id": live.id if live else False,
            "ocd_ticket_controller_id": controller.id if controller else False,
            "ocd_ticket_hold_until": now + timedelta(minutes=max(company.ocd_ticket_hold_minutes, 1)),
            "ocd_ticket_amount_company": amount,
            "ocd_ticket_token": secrets.token_urlsafe(18),
            "order_line": [fields.Command.create({
                "product_id": ticket.product_id.id,
                "event_id": event.id,
                "event_ticket_id": ticket.id,
                "product_uom_qty": count,
                "name": env._("%(kind)s ticket · %(event)s · %(when)s", kind=ticket.name, event=event.name,
                              when=event._ocd_short_when()),
                "tax_ids": [fields.Command.clear()],
            }) for ticket, count, _price in lines],
        })
        for line, (_ticket, _count, price) in zip(order.order_line, lines):
            line.price_unit = company.currency_id._convert(price, order.currency_id, company, fields.Date.today())
        return order

    def _ocd_ticket_holding(self, now=None):
        """Whether this order still holds its seats: within the time to pay, or while a payment is
        on its way (a Mobile Money checked by the team, a provider that confirms later)."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.state not in ("draft", "sent"):
            return False
        if self.ocd_ticket_hold_until and self.ocd_ticket_hold_until > now:
            return True
        return bool(self.transaction_ids.filtered(lambda tx: tx.state in ("pending", "authorized", "done")))

    @api.model
    def _ocd_cancel_unpaid_tickets(self, now=None):
        """The orders of tickets not paid in time are cancelled: their seats go back on sale."""
        now = now or fields.Datetime.now()
        orders = self.sudo().search([
            ("ocd_ticket_event_id", "!=", False), ("state", "in", ("draft", "sent")),
            ("ocd_ticket_hold_until", "<", now),
        ])
        for order in orders.filtered(lambda order: not order._ocd_ticket_holding(now)):
            order._action_cancel()

    def _ocd_check_ticket_token(self, token):
        self.ensure_one()
        stored = self.sudo().ocd_ticket_token or ""
        return bool(stored and token and len(stored) == len(str(token))) and secrets.compare_digest(stored, str(token))

    def _ocd_tickets_path(self):
        """« My tickets »: the payment, then the tickets of this order."""
        self.ensure_one()
        return f"/billets/commande/{self.id}?t={self.sudo().ocd_ticket_token}"

    # === PAID === #

    def action_confirm(self):
        """Override of `event_sale`: the tickets of OCD Tickets paid are created even when the last
        seats went meanwhile (the money is received), with their codes; a ticket sold at the door
        enters at once."""
        tickets = self.filtered("ocd_ticket_event_id")
        if not tickets:
            return super().action_confirm()
        result = super(SaleOrder, self.with_context(ocd_tickets_paid=True)).action_confirm()
        for order in tickets.sudo():
            registrations = order.ocd_ticket_registration_ids.filtered(lambda reg: reg.state != "cancel")
            # event_sale keeps the registrations of one order confirmed in the back office « to
            # confirm » (for the names of the attendees): a ticket paid is a ticket
            registrations.filtered(lambda reg: reg.state == "draft").with_context(ocd_tickets_paid=True).write(
                {"state": "open"})
            registrations._ocd_prepare(order)
            if order.ocd_ticket_source == "door":
                for registration in registrations:
                    registration._ocd_let_in(order.ocd_ticket_controller_id)
            order.message_post(body=self.env._("%s tickets created by the payment.", len(registrations)))
            if registrations and self.env["ocd.automation"]._ocd_enabled("tickets_paid"):
                registrations._ocd_first_of_each_holder()._ocd_tell_ready()
        return result

    def _ocd_ticket_sell_cash(self):
        """Sold at the door for cash: the order is confirmed at once, the cash counted with the
        controller at the end of the evening."""
        self.ensure_one()
        order = self.sudo()
        order.write({"ocd_ticket_cash_state": "to_collect"})
        order.action_confirm()
        return order
