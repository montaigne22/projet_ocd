import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import consteq
from odoo.tools.misc import hmac

from odoo.addons.ocd_live import tools

# The characters of the codes of the tickets: no 0/O, 1/I/L, read aloud at the door
CODE_LETTERS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class EventRegistration(models.Model):
    """A ticket of OCD Tickets: one person, one QR signed by the server, valid once. It exists when
    its payment is confirmed (a registration of Odoo created by the order). « Give this ticket »
    puts it in the name of a friend with a new QR: the old one no longer works."""

    _inherit = "event.registration"

    ocd_code = fields.Char(string="Code Of The Ticket", index=True, copy=False, readonly=True)
    ocd_version = fields.Integer(string="Version Of The QR", default=1, copy=False, readonly=True)
    ocd_source = fields.Selection(
        selection=[("page", "Page"), ("live", "During a live"), ("door", "At the door"), ("team", "Team")],
        string="Sold", copy=False, readonly=True,
    )
    ocd_entered_at = fields.Datetime(string="Entered At", readonly=True, copy=False)
    ocd_controller_id = fields.Many2one(
        comodel_name="ocd.ticket.controller", string="Let In By", readonly=True, copy=False, index="btree_not_null"
    )
    ocd_gate = fields.Char(string="Gate", readonly=True, copy=False)
    ocd_refund_state = fields.Selection(
        selection=[("none", "No"), ("to_refund", "To refund"), ("refunded", "Refunded")],
        string="Refund", default="none", required=True, tracking=True, copy=False, index=True,
    )
    ocd_given_by_id = fields.Many2one(comodel_name="res.partner", string="Given By", readonly=True, copy=False)
    ocd_amount_company = fields.Monetary(
        string="Paid", compute="_compute_ocd_amount", currency_field="ocd_currency_id",
        help="The price of the ticket, in the currency of the company.",
    )
    ocd_currency_id = fields.Many2one(related="company_id.currency_id", string="Currency Of OCD Tickets")
    ocd_payment_reference = fields.Char(compute="_compute_ocd_payment", string="Payment Reference")
    ocd_payment_method = fields.Char(compute="_compute_ocd_payment", string="Paid With")

    _unique_ocd_code = models.UniqueIndex("(ocd_code) WHERE ocd_code IS NOT NULL", "Another ticket has this code.")

    @api.depends("sale_order_line_id.price_unit", "sale_order_id.ocd_ticket_amount_company")
    def _compute_ocd_amount(self):
        for registration in self:
            order = registration.sale_order_id
            line = registration.sale_order_line_id
            amount = 0.0
            if order and line and order.amount_total:
                share = line.price_total / order.amount_total
                amount = order.ocd_ticket_amount_company * share / max(int(line.product_uom_qty), 1)
            registration.ocd_amount_company = amount

    @api.depends("sale_order_id.transaction_ids.state")
    def _compute_ocd_payment(self):
        for registration in self:
            order = registration.sale_order_id
            tx = order.transaction_ids.filtered(lambda tx: tx.state == "done")[:1]
            if order.ocd_ticket_cash_state in ("to_collect", "collected"):
                registration.ocd_payment_method = self.env._("Cash at the door")
                registration.ocd_payment_reference = order.name
                continue
            registration.ocd_payment_reference = tx.provider_reference or tx.reference or order.name or False
            registration.ocd_payment_method = tx.payment_method_id.name or tx.provider_id.name or False

    @api.constrains("active", "state", "event_id", "event_slot_id", "event_ticket_id")
    def _check_seats_availability(self):
        """Override of `event`: a ticket paid is always created, even when the last seats went
        meanwhile (the money is received: the team sees it on the event)."""
        if self.env.context.get("ocd_tickets_paid"):
            return
        return super()._check_seats_availability()

    # === THE CODE AND THE QR === #

    @api.model
    def _ocd_new_code(self, event):
        """« NAB-7K2Q-41 »: 3 letters of the event, 4 drawn by lot, 2 of control."""
        prefix = event._ocd_code_prefix()
        while True:
            middle = "".join(secrets.choice(CODE_LETTERS) for _index in range(4))
            check = hmac(self.env(su=True), "ocd_tickets.code", f"{prefix}{middle}")
            tail = "".join(CODE_LETTERS[int(check[i:i + 2], 16) % len(CODE_LETTERS)] for i in (0, 2))
            code = f"{prefix}-{middle}-{tail}"
            if not self.sudo().with_context(active_test=False).search_count([("ocd_code", "=", code)], limit=1):
                return code

    @api.model
    def _ocd_clean_code(self, text):
        """A code typed at the door, without spaces nor case: « nab 7k2q 41 » → « NAB-7K2Q-41 »."""
        raw = "".join(char for char in (text or "").upper() if char.isalnum())
        if len(raw) != 9:
            return False
        return f"{raw[:3]}-{raw[3:7]}-{raw[7:]}"

    def _ocd_signature(self):
        """The secret of the QR: the ticket, its code and its version are in it."""
        self.ensure_one()
        message = f"{self.id}:{self.event_id.id}:{self.sudo().ocd_code}:{self.sudo().ocd_version}"
        return hmac(self.env(su=True), "ocd_tickets.ticket", message)[:24]

    def _ocd_check_signature(self, signature):
        self.ensure_one()
        return bool(signature) and bool(self.sudo().ocd_code) and consteq(self._ocd_signature(), str(signature))

    def _ocd_ticket_path(self):
        """The page of this ticket alone (the QR opens it too): for a friend who received it."""
        self.ensure_one()
        return f"/billets/billet/{self.id}/{self._ocd_signature()}"

    def _ocd_qr(self):
        return tools.qr_data_uri(f"{self.get_base_url()}{self._ocd_ticket_path()}", box_size=8)

    def _ocd_holder_path(self):
        """Where the holder sees their tickets: the page of the order for the buyer, the page of the
        ticket for a friend."""
        self.ensure_one()
        order = self.sudo().sale_order_id
        if order and self.partner_id == order.partner_id and not self.ocd_given_by_id:
            return order._ocd_tickets_path()
        return self._ocd_ticket_path()

    def _ocd_first_of_each_holder(self):
        """One ticket for each holder and each order: one message, which opens all their tickets."""
        seen, first = set(), self.browse()
        for registration in self.sorted("id"):
            given = bool(registration.ocd_given_by_id)
            key = (registration.partner_id.id, registration.sale_order_id.id, registration.id if given else 0)
            if key not in seen:
                seen.add(key)
                first |= registration
        return first

    # === PAID === #

    def _ocd_prepare(self, order):
        """The tickets of `order` just created by its payment: their codes, the name on them."""
        name = order.ocd_ticket_holder_name or order.partner_id.name
        source = order.ocd_ticket_source or "page"
        for registration in self.sudo():
            values = {"ocd_source": source}
            if not registration.ocd_code:
                values["ocd_code"] = self._ocd_new_code(registration.event_id)
            if name and registration.name != name:
                values["name"] = name
            if order.partner_id.phone and not registration.phone:
                values["phone"] = order.partner_id.phone
            registration.write(values)

    def _ocd_valid(self):
        """Whether this ticket lets in: paid, not refunded, for an event on sale."""
        self.ensure_one()
        return (
            self.active and self.state in ("open", "done") and self.ocd_refund_state == "none"
            and bool(self.ocd_code) and self.event_id.ocd_state == "approved"
        )

    def _ocd_index_text(self):
        """« Ticket 1 of 2 · Standard »."""
        self.ensure_one()
        siblings = self.sudo().sale_order_id.ocd_ticket_registration_ids.filtered(
            lambda registration: registration.ocd_given_by_id == self.ocd_given_by_id
            and registration.partner_id == self.partner_id
        ).sorted("id")
        if len(siblings) > 1 and self in siblings:
            return self.env._("Ticket %(index)s of %(count)s · %(kind)s", index=list(siblings).index(self) + 1,
                              count=len(siblings), kind=self.event_ticket_id.name)
        return self.event_ticket_id.name or ""

    # === GIVE THIS TICKET === #

    def _ocd_give(self, partner, name):
        """Give this ticket to `partner` (a friend): a new code and a new QR in their name; the old
        QR no longer works. Return the ticket."""
        self.ensure_one()
        registration = self.sudo()
        if not registration._ocd_valid() or registration.state == "done":
            raise UserError(self.env._("This ticket can no longer be given."))
        if registration.event_id._ocd_passed():
            raise UserError(self.env._("The event is over."))
        if partner == registration.partner_id:
            raise UserError(self.env._("This ticket is already in this name."))
        before = registration.partner_id
        registration.with_context(ocd_tickets_paid=True).write({
            "partner_id": partner.id,
            "name": name or partner.name,
            "phone": partner.phone,
            "ocd_given_by_id": before.id,
            "ocd_code": self._ocd_new_code(registration.event_id),
            "ocd_version": registration.ocd_version + 1,
        })
        registration.message_post(body=self.env._("Given by %(before)s to %(after)s: a new QR, the old one no longer "
                                                  "works.", before=before.name, after=registration.name))
        if self.env["ocd.automation"]._ocd_enabled("tickets_paid"):
            registration._ocd_tell_ready()
        return registration

    # === AT THE ENTRANCE === #

    @api.model
    def _ocd_find(self, text):
        """The ticket of a QR read (its address) or of a code typed; with whether its QR is the
        current one. (ticket, current)."""
        text = (text or "").strip()
        Registration = self.sudo().with_context(active_test=False)
        if "/billets/billet/" in text:
            tail = text.split("/billets/billet/", 1)[1].split("?", 1)[0].strip("/").split("/")
            if len(tail) >= 2 and tail[0].isdigit():
                registration = Registration.browse(int(tail[0])).exists()
                if registration:
                    return registration, registration._ocd_check_signature(tail[1])
            return Registration.browse(), False
        code = self._ocd_clean_code(text)
        if not code:
            return Registration.browse(), False
        registration = Registration.search([("ocd_code", "=", code)], limit=1)
        return registration, bool(registration)

    def _ocd_let_in(self, controller, at=None):
        """The controller lets this ticket in (at `at`, for an entry made without the network)."""
        self.ensure_one()
        # Entering never fails because of the seats: the ticket is paid
        self.sudo().with_context(ocd_tickets_paid=True).write({
            "state": "done",
            "ocd_entered_at": at or fields.Datetime.now(),
            "ocd_controller_id": controller.id if controller else False,
            "ocd_gate": controller.gate if controller else False,
        })

    # === MESSAGES (ocd_tickets_whatsapp) === #

    def _ocd_tell_ready(self):
        """Hook: the tickets are paid (or given): they leave on WhatsApp."""

    def _ocd_tell_reminder(self):
        """Hook: the reminder the day before."""

    def _ocd_tell_changed(self, change):
        """Hook: the event is cancelled (`cancelled`) or moved (`moved`)."""

    def action_ocd_refunded(self):
        """The team refunded the ticket: it no longer lets in."""
        for registration in self.filtered(lambda registration: registration.ocd_refund_state == "to_refund"):
            registration.ocd_refund_state = "refunded"
            registration.message_post(body=self.env._("Refunded by %s.", self.env.user.name))
        return True

    def action_ocd_to_refund(self):
        """The team decides to refund a ticket not used."""
        for registration in self.filtered(lambda registration: registration.ocd_refund_state == "none"):
            if registration.state == "done":
                raise UserError(self.env._("%s already entered: no refund.", registration.name))
            registration.ocd_refund_state = "to_refund"
        return True
