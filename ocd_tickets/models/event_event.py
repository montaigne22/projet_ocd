"""OCD Tickets (chantier 6 of the roadmap, design OcdTickets): tickets of concerts and events, sold
on the page of the event and during the lives, paid with the payment form of OCD Live. The event is
the one of the Events application of Odoo (its date, its place, its kinds of tickets and their
seats); a ticket is a registration of Odoo, created when its payment is confirmed, with one QR per
person signed by the server."""
import re
import time
import unicodedata
from datetime import timedelta
from urllib.parse import quote_plus

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules import module as odoo_module
from odoo.tools.misc import format_amount, formatLang

from odoo.addons.ocd_live import tools

STATES = [
    ("draft", "Being prepared"),
    ("to_check", "To check"),
    ("approved", "On sale"),
    ("cancelled", "Cancelled"),
]
PAYOUT_STATES = [("none", "Not yet"), ("to_pay", "To pay"), ("paid", "Paid")]
# The organiser is paid this many days after the event
PAYOUT_DAYS = 3
# The reminder goes this many hours before the start, once
REMINDER_HOURS = 24
# The addresses of the pages of OCD Tickets, never the address of an event
RESERVED_SLUGS = {"entree", "commande", "billet", "image"}
# « Tickets » in the menu: {database: (until, shown)}
_menu_cache = {}


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60] or "evenement"


class EventEvent(models.Model):
    _inherit = "event.event"

    ocd_ticketing = fields.Boolean(
        string="Sold On OCD Tickets", index=True, copy=True,
        help="Its tickets are sold on the site of OCD Live, paid like the rest of OCD Live, checked at the entrance "
        "by the controllers.",
    )
    ocd_state = fields.Selection(
        selection=STATES, string="State On OCD Tickets", default="draft", required=True, tracking=True, index=True,
        copy=False,
    )
    ocd_slug = fields.Char(
        string="Address Of The Page", copy=False, index=True, help="The end of the address of its page: /billets/<address>."
    )
    ocd_organizer_id = fields.Many2one(
        comodel_name="res.partner", string="Organiser On OCD Tickets", index=True, tracking=True,
        help="Empty: an event of OCD Live. The organiser logs in with their number, like for OCD Vote.",
    )
    ocd_organizer_verified = fields.Boolean(related="ocd_organizer_id.ocd_vote_organizer_verified")
    ocd_kind = fields.Char(string="Kind", help="« Concert », « Gala », « Festival »: shown above the name.")
    ocd_poster = fields.Image(string="Poster", max_width=1600, max_height=1600)
    ocd_about = fields.Text(string="About The Event", help="What the event is, in a few sentences.")
    ocd_doors_at = fields.Datetime(string="Doors Open At")
    ocd_organizer_share = fields.Float(
        string="Share Of The Organiser (%)", tracking=True,
        default=lambda self: self.env.company.ocd_ticket_organizer_share,
    )
    ocd_door_sale = fields.Boolean(
        string="Sale At The Door", help="The controllers who may sell sell tickets at the entrance (cash or Mobile Money)."
    )
    ocd_booking_ids = fields.Many2many(
        comodel_name="ocd.live.booking", relation="event_event_ocd_live_booking_rel", column1="event_event_id",
        column2="ocd_live_booking_id", string="Lives Selling The Tickets",
        help="During these lives, the control room shows the tickets like products, at their live price if any.",
    )
    ocd_controller_ids = fields.One2many(
        comodel_name="ocd.ticket.controller", inverse_name="event_id", string="Controllers"
    )
    ocd_order_ids = fields.One2many(comodel_name="sale.order", inverse_name="ocd_ticket_event_id", string="Orders")
    ocd_moved_from = fields.Datetime(string="Planned Before At", readonly=True, copy=False)
    ocd_moved_at = fields.Datetime(string="Moved On", readonly=True, copy=False)
    ocd_reminded_at = fields.Datetime(string="Reminder Sent At", readonly=True, copy=False)
    ocd_sold_count = fields.Integer(string="Tickets Sold", compute="_compute_ocd_totals")
    ocd_entered_count = fields.Integer(string="Entered", compute="_compute_ocd_totals")
    ocd_amount_total = fields.Monetary(
        string="Collected", compute="_compute_ocd_totals", currency_field="ocd_currency_id"
    )
    ocd_live_amount = fields.Monetary(
        string="Collected During The Lives", compute="_compute_ocd_totals", currency_field="ocd_currency_id"
    )
    ocd_organizer_amount = fields.Monetary(
        string="Share Of The Organiser", compute="_compute_ocd_totals", currency_field="ocd_currency_id"
    )
    ocd_currency_id = fields.Many2one(related="company_id.currency_id", string="Currency Of OCD Tickets")
    ocd_payout_state = fields.Selection(
        selection=PAYOUT_STATES, string="Payout", default="none", tracking=True, copy=False
    )
    ocd_payout_due = fields.Date(string="Payout Before", readonly=True, copy=False)
    ocd_payout_momo = fields.Char(string="Mobile Money Of The Organiser", tracking=True)
    ocd_payout_reference = fields.Char(string="Transfer Reference", tracking=True, copy=False)
    ocd_payout_date = fields.Date(string="Paid On", tracking=True, copy=False)

    _unique_ocd_slug = models.UniqueIndex("(ocd_slug) WHERE ocd_slug IS NOT NULL", "Another event has this address.")

    # === COMPUTE === #

    @api.depends("registration_ids.state", "registration_ids.ocd_refund_state", "ocd_organizer_share",
                 "ocd_order_ids.state")
    def _compute_ocd_totals(self):
        Registration = self.env["event.registration"].sudo()
        sold = dict(Registration._read_group(
            [("event_id", "in", self.ids), ("state", "in", ("open", "done")), ("ocd_refund_state", "=", "none")],
            ["event_id"], ["__count"],
        ))
        entered = dict(Registration._read_group(
            [("event_id", "in", self.ids), ("state", "=", "done")], ["event_id"], ["__count"],
        ))
        for event in self:
            orders = event._ocd_paid_orders()
            amount = sum(orders.mapped("ocd_ticket_amount_company"))
            event.ocd_sold_count = sold.get(event._origin, 0)
            event.ocd_entered_count = entered.get(event._origin, 0)
            event.ocd_amount_total = amount
            event.ocd_live_amount = sum(orders.filtered("ocd_ticket_live_id").mapped("ocd_ticket_amount_company"))
            event.ocd_organizer_amount = event.ocd_currency_id.round(amount * event.ocd_organizer_share / 100)

    def _ocd_paid_orders(self):
        """The orders of tickets paid and not refunded."""
        self.ensure_one()
        return self.sudo().ocd_order_ids.filtered(
            lambda order: order.state == "sale" and order.ocd_ticket_cash_state != "lost"
            and any(reg.ocd_refund_state == "none" for reg in order.ocd_ticket_registration_ids)
        )

    @api.constrains("ocd_organizer_share")
    def _check_ocd_share(self):
        for event in self:
            if not 0 <= event.ocd_organizer_share <= 100:
                raise ValidationError(self.env._("The share of the organiser is between 0 and 100 %."))

    # === CREATE === #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("ocd_ticketing"):
                vals["ocd_slug"] = self._ocd_free_slug(vals.get("ocd_slug") or vals.get("name"))
                # The tickets and the reminders go on WhatsApp: no e-mail of the Events application
                vals.setdefault("event_mail_ids", [fields.Command.clear()])
        events = super().create(vals_list)
        events.filtered("ocd_ticketing").event_ticket_ids._ocd_ensure_product()
        return events

    def write(self, vals):
        if "ocd_slug" in vals and vals["ocd_slug"]:
            vals["ocd_slug"] = self._ocd_free_slug(vals["ocd_slug"], exclude=self)
        if vals.get("ocd_ticketing"):
            for event in self.filtered(lambda event: not event.ocd_slug):
                event.ocd_slug = self._ocd_free_slug(vals.get("name") or event.name)
        locked = {"date_begin", "date_end"} & set(vals)
        if locked and not self.env.context.get("ocd_tickets_move"):
            for event in self.filtered(lambda event: event.ocd_ticketing and event.ocd_state == "approved"):
                if event.ocd_sold_count:
                    raise UserError(self.env._(
                        "%s has tickets sold: use « Move » so that the buyers are told and may ask for a refund.",
                        event.name,
                    ))
        result = super().write(vals)
        if "ocd_ticketing" in vals or "event_ticket_ids" in vals:
            self.filtered("ocd_ticketing").event_ticket_ids._ocd_ensure_product()
        if "ocd_poster" in vals:
            products = self.filtered("ocd_ticketing").event_ticket_ids.product_id
            products.sudo().write({"image_1920": vals["ocd_poster"] or False})
        return result

    @api.model
    def _ocd_free_slug(self, text, exclude=None):
        base = slugify(text)
        slug, index = base, 1
        domain = [("id", "not in", exclude.ids)] if exclude else []
        while slug in RESERVED_SLUGS or self.sudo().with_context(active_test=False).search_count(
                domain + [("ocd_slug", "=", slug)]):
            index += 1
            slug = f"{base}-{index}"
        return slug

    # === STATE === #

    @api.model
    def _ocd_menu_shown(self):
        """Whether « Tickets » is in the menu: an event on sale, not over. Read again at most once a
        minute by each worker (every page asks)."""
        now = time.monotonic()
        key = self.env.cr.dbname
        cached = _menu_cache.get(key)
        if cached and cached[0] > now and not odoo_module.current_test:
            return cached[1]
        shown = bool(self.sudo().search_count([
            ("ocd_ticketing", "=", True), ("ocd_state", "=", "approved"), ("date_end", ">", fields.Datetime.now()),
        ], limit=1))
        _menu_cache[key] = (now + 60, shown)
        return shown

    def _ocd_public(self):
        """Whether the page of the event is shown: on sale (also once passed), or cancelled (to say
        it)."""
        self.ensure_one()
        return self.ocd_ticketing and self.ocd_state in ("approved", "cancelled")

    def _ocd_passed(self, now=None):
        self.ensure_one()
        return (now or fields.Datetime.now()) >= self.date_end

    def _ocd_sale_end(self):
        """When the sale on the site stops: the start, or some hours before (setting)."""
        self.ensure_one()
        return self.date_begin - timedelta(hours=max(self.company_id.ocd_ticket_sale_end_hours, 0))

    def _ocd_on_sale(self, now=None):
        """Whether the public may buy now on the site."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        return self.ocd_ticketing and self.ocd_state == "approved" and now < self._ocd_sale_end()

    def _ocd_door_open(self, now=None):
        """Whether the controllers may sell at the door now: allowed by the organiser, until the end."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        return self.ocd_door_sale and self.ocd_state == "approved" and now < self.date_end

    def action_ocd_send_to_check(self):
        """The organiser sends the event to the team."""
        for event in self:
            if event.ocd_state != "draft":
                continue
            event._ocd_check_ready()
            event.ocd_state = "to_check"
            event.message_post(body=self.env._("Sent to OCD Live to check."))
        return True

    def _ocd_check_ready(self):
        self.ensure_one()
        if not self.event_ticket_ids:
            raise UserError(self.env._("Add the kinds of tickets first (Standard, VIP...)."))
        if any(ticket.price <= 0 for ticket in self.event_ticket_ids):
            raise UserError(self.env._("Each kind of ticket has a price: OCD Tickets sells no free ticket."))
        if not self.address_id:
            raise UserError(self.env._("Write the place of the event."))

    def action_ocd_approve(self):
        """« Check and put on sale »: the page of the event opens, its tickets are on sale."""
        for event in self:
            if event.ocd_state not in ("draft", "to_check"):
                continue
            event._ocd_check_ready()
            event.write({"ocd_ticketing": True, "ocd_state": "approved"})
            event.message_post(body=self.env._("Checked by %s: on sale.", self.env.user.name))
        return True

    def action_ocd_refuse(self, reason=None):
        for event in self:
            event.ocd_state = "draft"
            event.message_post(body=self.env._("Sent back to the organiser: %s",
                                               reason.message or reason.name if reason else "-"))
        return True

    def action_ocd_cancel(self):
        """« Cancel and refund »: the event no longer takes place; every ticket paid is to refund, the
        tickets waiting for their payment are cancelled, the buyers are told."""
        for event in self:
            if event.ocd_state == "cancelled":
                continue
            event.ocd_state = "cancelled"
            registrations = event._ocd_valid_registrations()
            registrations.write({"ocd_refund_state": "to_refund"})
            for order in event.sudo().ocd_order_ids.filtered(lambda order: order.state in ("draft", "sent")):
                order._action_cancel()
            event.write({"ocd_payout_state": "none"})
            event.message_post(body=self.env._("Cancelled by %(user)s: %(count)s tickets to refund.",
                                               user=self.env.user.name, count=len(registrations)))
            if registrations and self.env["ocd.automation"]._ocd_enabled("tickets_changed"):
                registrations._ocd_first_of_each_holder()._ocd_tell_changed("cancelled")
        return True

    def action_ocd_open_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Move %s", self.name),
            "res_model": "ocd.ticket.move",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_event_id": self.id,
                "default_date_begin": self.date_begin,
                "default_date_end": self.date_end,
                "default_doors_at": self.ocd_doors_at,
            },
        }

    def _ocd_move(self, date_begin, date_end, doors_at=False):
        """The event moves: the tickets stay valid at the new date, the buyers are told and may ask
        for a refund for a few days (setting)."""
        self.ensure_one()
        if date_end <= date_begin:
            raise UserError(self.env._("The event ends after it starts."))
        before = self.date_begin
        self.with_context(ocd_tickets_move=True).write({
            "date_begin": date_begin,
            "date_end": date_end,
            "ocd_doors_at": doors_at or False,
            "ocd_moved_from": before,
            "ocd_moved_at": fields.Datetime.now(),
            "ocd_reminded_at": False,
        })
        self.message_post(body=self.env._("Moved by %(user)s to %(when)s.", user=self.env.user.name,
                                          when=self._ocd_when_text()))
        registrations = self._ocd_valid_registrations()
        if registrations and self.env["ocd.automation"]._ocd_enabled("tickets_changed"):
            registrations._ocd_first_of_each_holder()._ocd_tell_changed("moved")
        return True

    def _ocd_refund_until(self):
        """Until when a buyer who cannot come after a move asks for a refund (False: no move)."""
        self.ensure_one()
        if not self.ocd_moved_at:
            return False
        return self.ocd_moved_at + timedelta(days=max(self.company_id.ocd_ticket_refund_days, 0))

    def action_ocd_payout_paid(self):
        for event in self:
            if event.ocd_payout_state != "to_pay":
                continue
            if not event.ocd_payout_reference:
                raise UserError(self.env._("Write the reference of the transfer first."))
            event.write({"ocd_payout_state": "paid", "ocd_payout_date": fields.Date.context_today(event)})
        return True

    def action_ocd_view_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Tickets of %s", self.name),
            "res_model": "event.registration",
            "view_mode": "list,form",
            "views": [(self.env.ref("ocd_tickets.event_registration_view_list_ocd").id, "list"), (False, "form")],
            "domain": [("event_id", "=", self.id)],
            "context": {"default_event_id": self.id},
        }

    def action_ocd_view_entries(self):
        action = self.action_ocd_view_tickets()
        action["name"] = self.env._("Entries of %s", self.name)
        action["domain"] = [("event_id", "=", self.id), ("state", "=", "done")]
        return action

    def action_ocd_open_page(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": f"/billets/{self.ocd_slug}", "target": "new"}

    def _ocd_valid_registrations(self):
        """The tickets paid that let in (or let in already), not refunded."""
        self.ensure_one()
        return self.env["event.registration"].sudo().search([
            ("event_id", "=", self.id), ("state", "in", ("open", "done")), ("ocd_refund_state", "=", "none"),
        ])

    # === SCHEDULED TASK === #

    @api.model
    def _cron_ocd_tickets(self):
        """Every few minutes: the tickets not paid in time are given back for sale; the buyers are
        reminded the day before; the share of the organiser is due a few days after the event."""
        now = fields.Datetime.now()
        Automation = self.env["ocd.automation"]
        self.env["sale.order"].sudo()._ocd_cancel_unpaid_tickets(now)
        events = self.sudo().search([("ocd_ticketing", "=", True), ("ocd_state", "=", "approved")])
        if Automation._ocd_enabled("tickets_reminder"):
            for event in events.filtered(lambda event: not event.ocd_reminded_at
                                         and now < event.date_begin <= now + timedelta(hours=REMINDER_HOURS)):
                event.ocd_reminded_at = now
                registrations = event._ocd_valid_registrations()
                if registrations:
                    registrations._ocd_first_of_each_holder()._ocd_tell_reminder()
        if Automation._ocd_enabled("tickets_payout"):
            for event in events.filtered(lambda event: event.ocd_payout_state == "none" and event.date_end <= now):
                if event.ocd_organizer_id and event.ocd_organizer_amount > 0:
                    event.write({
                        "ocd_payout_state": "to_pay",
                        "ocd_payout_due": fields.Date.context_today(event) + timedelta(days=PAYOUT_DAYS),
                    })
                    event.message_post(body=self.env._("Event passed: the share of the organiser is to pay."))

    # === SEATS === #

    def _ocd_held(self, now=None):
        """{ticket id: seats held by the orders waiting for their payment}: until the end of the
        time to pay, or while a payment checked by the team waits."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        held = {}
        for order in self.sudo().ocd_order_ids.filtered(lambda order: order.state in ("draft", "sent")):
            if not order._ocd_ticket_holding(now):
                continue
            for line in order.order_line.filtered("event_ticket_id"):
                held[line.event_ticket_id.id] = held.get(line.event_ticket_id.id, 0) + int(line.product_uom_qty)
        return held

    def _ocd_left(self, held=None):
        """{ticket id: tickets left for sale (None: no limit)}: the seats of each kind and of the
        whole event, less the tickets sold and the ones being paid."""
        self.ensure_one()
        held = self._ocd_held() if held is None else held
        event_left = None
        if self.seats_limited:
            event_left = max(self.seats_available - sum(held.values()), 0)
        left = {}
        for ticket in self.event_ticket_ids:
            value = None
            if ticket.seats_max:
                value = max(ticket.seats_available - held.get(ticket.id, 0), 0)
            if event_left is not None:
                value = event_left if value is None else min(value, event_left)
            left[ticket.id] = value
        return left

    def _ocd_seats_line(self):
        """« 1,264 tickets sold » and « 336 left » (the second empty without a limit)."""
        self.ensure_one()
        env = self.env
        sold = self.ocd_sold_count
        sold_text = env._("1 ticket sold") if sold == 1 else env._("%s tickets sold", self._ocd_number(sold))
        values = [value for value in self._ocd_left().values()]
        if values and all(value is not None for value in values):
            total = sum(values) if not self.seats_limited else min(sum(values), max(self.seats_available, 0))
            if total <= 0:
                return sold_text, env._("Sold out")
            return sold_text, env._("1 left") if total == 1 else env._("%s left", self._ocd_number(total))
        return sold_text, ""

    # === TEXTS AND ADDRESSES === #

    def _ocd_local(self, value):
        self.ensure_one()
        return tools.to_tz(value, self.date_tz or self.company_id.ocd_studio_tz or "Africa/Lome")

    def _ocd_hour(self, local):
        if (self.env.lang or "").startswith("fr"):
            return f"{local.hour} h {local.minute:02d}" if local.minute else f"{local.hour} h"
        return f"{local:%H:%M}"

    def _ocd_when_text(self, pattern="EEEE d MMMM", capital=True):
        """« Saturday 12 December · 20:00 », at the hour of the place of the event."""
        self.ensure_one()
        local = self._ocd_local(self.date_begin)
        return self.env._("%(day)s · %(hour)s", day=tools.day_text(self.env, local.date(), pattern, capital=capital),
                          hour=self._ocd_hour(local))

    def _ocd_when_sentence(self):
        """« Saturday 12 December at 20:00 », for the messages."""
        self.ensure_one()
        local = self._ocd_local(self.date_begin)
        return self.env._("%(day)s at %(hour)s", day=tools.day_text(self.env, local.date(), "EEEE d MMMM"),
                          hour=self._ocd_hour(local))

    def _ocd_short_when(self):
        """« Sat 12 Dec · 20:00 », on the tickets."""
        return self._ocd_when_text("EEE d MMM", capital=True)

    def _ocd_doors_text(self):
        """« Doors open at 18:30 (time of Douala) »."""
        self.ensure_one()
        if not self.ocd_doors_at:
            return self.env._("Time of %s", self._ocd_city() or self.date_tz)
        return self.env._("Doors open at %(hour)s (time of %(city)s)",
                          hour=self._ocd_hour(self._ocd_local(self.ocd_doors_at)),
                          city=self._ocd_city() or self.date_tz)

    def _ocd_doors_short(self):
        """« doors 18:30 », on the tickets."""
        self.ensure_one()
        return self.env._("doors %s", self._ocd_doors_hour()) if self.ocd_doors_at else ""

    def _ocd_doors_hour(self):
        self.ensure_one()
        return self._ocd_hour(self._ocd_local(self.ocd_doors_at)) if self.ocd_doors_at else False

    def _ocd_city(self):
        self.ensure_one()
        return self.address_id.city or ""

    def _ocd_place_text(self):
        """« Palais des Sports, Douala »."""
        self.ensure_one()
        address = self.address_id
        name = address.name or ""
        city = address.city or ""
        if city and city.lower() not in name.lower():
            return f"{name}, {city}" if name else city
        return name or city

    def _ocd_district(self):
        """The street or the district of the place (« Warda »)."""
        self.ensure_one()
        return self.address_id.street or ""

    def _ocd_route_url(self):
        """The way to the place, in the maps of the phone."""
        self.ensure_one()
        address = self.address_id
        parts = [address.name, address.street, address.city, address.country_id.name]
        query = ", ".join(part for part in parts if part)
        if address.partner_latitude and address.partner_longitude:
            query = f"{address.partner_latitude},{address.partner_longitude}"
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}" if query else False

    def _ocd_organizer_line(self):
        self.ensure_one()
        return self.env._("By %s", self.ocd_organizer_id.name) if self.ocd_organizer_id else self.env._("By OCD Live")

    def _ocd_money(self, amount):
        self.ensure_one()
        return format_amount(self.env, amount, self.ocd_currency_id)

    def _ocd_number(self, value):
        return formatLang(self.env, value, digits=0)

    def _ocd_public_path(self):
        self.ensure_one()
        return f"/billets/{self.ocd_slug}"

    def _ocd_poster_url(self):
        self.ensure_one()
        if not self.ocd_poster:
            return False
        return f"/billets/image/{self.id}?v={self.write_date:%Y%m%d%H%M%S}"

    def _ocd_code_prefix(self):
        """The 3 letters of the codes of its tickets: « NAB » for « Nuit de l'Afrobeat »."""
        self.ensure_one()
        words = re.findall(r"[A-Za-z0-9]+", unicodedata.normalize("NFKD", self.name or "")
                           .encode("ascii", "ignore").decode())
        long_words = [word.upper() for word in words if len(word) > 2] or [word.upper() for word in words]
        letters = "".join(word[0] for word in long_words)[:3]
        if long_words and len(letters) < 3:
            # « Nuit de l'Afrobeat »: N, A, then the next letters of the last word (NAF)
            letters = (letters + long_words[-1][1:])[:3]
        return (letters or "OCD").ljust(3, "X")

    def _ocd_live_now(self, now=None):
        """The live selling its tickets now, if any."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        return self.sudo().ocd_booking_ids.filtered(
            lambda booking: booking.state == "confirmed" and booking.start_datetime <= now < booking.end_datetime
        )[:1]
