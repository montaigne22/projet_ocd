import logging
from datetime import timedelta

import psycopg2

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, format_date, format_datetime

from .. import tools

_logger = logging.getLogger(__name__)

HOST_ACTIVITY = "ocd_live.mail_activity_type_choose_host"


class OcdLiveBooking(models.Model):
    _name = "ocd.live.booking"
    _description = "Live Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env._("New"),
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        index=True,
        tracking=True,
        domain=[("ocd_is_vendor", "=", True)],
    )
    business = fields.Char(related="partner_id.ocd_business")
    vendor_country_id = fields.Many2one(
        related="partner_id.country_id", string="Vendor Country", store=True
    )
    vendor_phone = fields.Char(related="partner_id.phone", string="Vendor Phone")
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    mode = fields.Selection(
        selection=[("studio", "At the studio in Lome"), ("remote", "Remote")],
        required=True,
        default="studio",
        tracking=True,
    )
    start_datetime = fields.Datetime(string="Start", required=True, tracking=True)
    slot_count = fields.Integer(
        string="Slots",
        required=True,
        default=1,
        help="Number of consecutive slots of the calendar taken by this live.",
    )
    end_datetime = fields.Datetime(string="End", compute="_compute_end_datetime", store=True)
    state = fields.Selection(
        selection=[
            ("draft", "Held"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        tracking=True,
        index=True,
    )
    hold_until = fields.Datetime(
        string="Held Until",
        copy=False,
        help="Without payment by then, the slot is released.",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Package",
        domain=[("ocd_product_kind", "=", "live_package")],
        check_company=True,
    )
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Order Line",
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    sale_order_id = fields.Many2one(
        related="sale_line_id.order_id", store=True, string="Order", index="btree_not_null"
    )
    credit_id = fields.Many2one(
        comodel_name="ocd.live.credit",
        string="Credit Used",
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    studio_need = fields.Selection(
        selection=[
            ("none", "Nothing"),
            ("shelf", "A shelf"),
            ("rack", "A clothes rack"),
            ("table", "A table"),
        ],
        string="Needed At The Studio",
        default="none",
    )
    animatrice_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Host",
        domain=[("ocd_is_animatrice", "=", True)],
        tracking=True,
        check_company=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        tracking=True,
        default=lambda self: self.env.company.ocd_live_responsible_id,
    )
    live_url = fields.Char(string="Live Link")
    replay_url = fields.Char(string="Replay Link")
    replay_published = fields.Boolean(string="Replay Published", copy=False, tracking=True)
    slot_ids = fields.One2many(
        comodel_name="ocd.live.booking.slot", inverse_name="booking_id", string="Reserved Slots"
    )
    note = fields.Text()
    needs_host = fields.Boolean(
        string="Host To Choose",
        compute="_compute_needs_host",
        search="_search_needs_host",
    )
    color = fields.Integer(compute="_compute_color")
    ticket_code = fields.Char(string="Ticket", compute="_compute_ticket_code")
    price_percent = fields.Float(
        string="Price Of The Hour (%)",
        readonly=True,
        help="Price change of the hour of the live when it was booked (price of the hours).",
    )

    _check_slot_count = models.Constraint(
        "CHECK (slot_count > 0)",
        "A live takes at least one slot.",
    )

    @api.depends("start_datetime", "slot_count", "company_id.ocd_slot_hours")
    def _compute_end_datetime(self):
        for booking in self:
            if booking.start_datetime:
                hours = (booking.company_id.ocd_slot_hours or 1.5) * booking.slot_count
                booking.end_datetime = booking.start_datetime + timedelta(hours=hours)
            else:
                booking.end_datetime = False

    @api.depends("mode", "animatrice_id", "state")
    def _compute_needs_host(self):
        for booking in self:
            booking.needs_host = (
                booking.mode == "remote"
                and not booking.animatrice_id
                and booking.state in ("draft", "confirmed")
            )

    def _search_needs_host(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        domain = Domain([
            ("mode", "=", "remote"),
            ("animatrice_id", "=", False),
            ("state", "in", ("draft", "confirmed")),
        ])
        return domain if (operator == "=") == value else ~domain

    @api.depends("start_datetime", "mode", "company_id")
    def _compute_ticket_code(self):
        for booking in self:
            if not booking.start_datetime:
                booking.ticket_code = False
                continue
            local = booking.company_id._ocd_to_local(booking.start_datetime)
            suffix = "-D" if booking.mode == "remote" else ""
            booking.ticket_code = f"OCD-{local:%m%d}-{local:%H%M}{suffix}"

    @api.depends("mode", "state")
    def _compute_color(self):
        for booking in self:
            if booking.state == "draft":
                booking.color = 3
            elif booking.mode == "remote":
                booking.color = 4
            else:
                booking.color = 2

    @api.constrains("start_datetime", "slot_count", "state", "product_id")
    def _check_slot_grid(self):
        for booking in self.filtered(lambda b: b.state in ("draft", "confirmed")):
            booking._ocd_slot_datetimes()

    @api.constrains("credit_id", "partner_id", "product_id", "state")
    def _check_credit(self):
        for booking in self.filtered("credit_id"):
            credit = booking.credit_id
            if credit.partner_id != booking.partner_id:
                raise ValidationError(self.env._("A live can only use a credit of its own vendor."))
            if booking.product_id and credit.product_id != booking.product_id:
                raise ValidationError(self.env._("The live does not match the package of the credit."))
            if credit.used > credit.quantity:
                raise ValidationError(
                    self.env._("The package %s has no live left to place.", credit.product_id.display_name)
                )

    # === CRUD === #

    @api.model_create_multi
    def create(self, vals_list):
        default_name = self.env._("New")
        for vals in vals_list:
            if vals.get("name", default_name) == default_name:
                vals["name"] = self.env["ir.sequence"].next_by_code("ocd.live.booking") or default_name
        bookings = super().create(vals_list)
        now = fields.Datetime.now()
        for booking in bookings.filtered(lambda b: b.state == "draft" and not b.hold_until):
            booking.hold_until = now + timedelta(minutes=booking.company_id.ocd_hold_minutes or 30)
        bookings.filtered(lambda b: b.state in ("draft", "confirmed"))._ocd_reserve_slots()
        return bookings

    def write(self, vals):
        moving = any(key in vals for key in ("start_datetime", "slot_count", "company_id", "mode"))
        if moving and self.filtered(lambda b: b.state in ("done", "cancelled")):
            raise UserError(self.env._("A live that took place or was cancelled cannot be moved."))
        result = super().write(vals)
        if moving:
            active = self.filtered(lambda b: b.state in ("draft", "confirmed"))
            active.sudo().slot_ids.unlink()
            active._ocd_reserve_slots()
        if vals.get("animatrice_id"):
            self.activity_feedback([HOST_ACTIVITY])
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if self.filtered(lambda b: b.state in ("confirmed", "done")):
            raise UserError(self.env._("Cancel a confirmed live instead of deleting it."))

    # === SLOTS === #

    def _ocd_slot_datetimes(self):
        """Return the starts of the slots taken by the booking, and check that it fits the
        calendar of the studio."""
        self.ensure_one()
        company = self.company_id
        local_start = company._ocd_to_local(self.start_datetime)
        starts = company._ocd_slot_starts(local_start.date())
        start = self.start_datetime.replace(microsecond=0)
        if not starts:
            raise ValidationError(self.env._("The studio is closed on that day."))
        if start not in starts:
            raise ValidationError(
                self.env._(
                    "A live must start at one of the hours of the studio: %s.",
                    [company._ocd_to_local(s).strftime("%H:%M") for s in starts],
                )
            )
        if self.product_id and self.product_id.ocd_slot_count != self.slot_count:
            raise ValidationError(
                self.env._(
                    "The package %(package)s takes %(count)s slots.",
                    package=self.product_id.display_name,
                    count=self.product_id.ocd_slot_count,
                )
            )
        index = starts.index(start)
        if index + self.slot_count > len(starts):
            raise ValidationError(self.env._("This live would end after the closing of the studio."))
        open_date = company.ocd_booking_open_date
        if open_date and local_start.date() < open_date and self.state == "draft":
            raise ValidationError(
                self.env._("Lives can be booked from %s.", format_date(self.env, open_date))
            )
        return starts[index:index + self.slot_count]

    def _ocd_reserve_slots(self):
        """Insert one row per taken slot; the unique index refuses a slot already taken."""
        vals_list = []
        for booking in self:
            key = booking.company_id._ocd_calendar_key(booking.mode)
            vals_list.extend(
                {
                    "booking_id": booking.id,
                    "company_id": booking.company_id.id,
                    "calendar_key": key,
                    "start_datetime": start,
                }
                for start in booking._ocd_slot_datetimes()
            )
        if not vals_list:
            return
        # sudo: slots are technical rows, the booking itself was checked by the access rules
        Slot = self.env["ocd.live.booking.slot"].sudo()
        existing = Slot.search([
            ("company_id", "in", self.company_id.ids),
            ("start_datetime", "in", [vals["start_datetime"] for vals in vals_list]),
            ("booking_id", "not in", self.ids),
        ])
        # An unpaid live whose hold is over frees its slot now, without waiting for the
        # scheduled release
        expired = existing.booking_id._ocd_expired_holds()
        existing = existing.filtered(lambda slot: slot.booking_id not in expired)
        if expired:
            expired.action_cancel()
        taken_keys = {(s.company_id.id, s.calendar_key, s.start_datetime) for s in existing}
        if any((v["company_id"], v["calendar_key"], v["start_datetime"]) in taken_keys for v in vals_list):
            raise ValidationError(self.env._("This time slot is already taken. Please choose another one."))
        try:
            with self.env.cr.savepoint():
                Slot.create(vals_list)
                Slot.flush_model()
        except psycopg2.errors.UniqueViolation:
            raise ValidationError(
                self.env._("This time slot has just been taken. Please choose another one.")
            ) from None

    # === ACTIONS === #

    def action_confirm(self):
        """Confirm held lives without payment (payment received by hand)."""
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of the lives can confirm a live without payment."))
        for booking in self:
            if booking.sale_order_id and booking.sale_order_id.state in ("draft", "sent"):
                booking.sale_order_id.action_confirm()
        self.filtered(lambda b: b.state == "draft")._ocd_confirm()
        return True

    def action_ocd_mark_paid(self):
        """The team checked the payment (Mobile Money checked by hand, cash at the studio):
        the pending payment is done, and the held lives are confirmed."""
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of the lives can confirm a payment."))
        # sudo: the payments are confirmed by a manager of the lives
        pending = self.sudo().sale_order_id.transaction_ids.filtered(lambda tx: tx.state == "pending")
        if pending:
            pending._set_done()
            pending._post_process()
        held = self.filtered(lambda b: b.state == "draft")
        if held:
            held.action_confirm()
        return True

    def action_ocd_team_move(self, start):
        """Move a live from the planning of the team, at any time, to the free slot `start`."""
        self.ensure_one()
        if self.state not in ("draft", "confirmed"):
            raise UserError(self.env._("Only a coming live can be moved."))
        start = fields.Datetime.to_datetime(start)
        old_day = self.company_id._ocd_to_local(self.start_datetime).date()
        self.start_datetime = start
        self.env["ocd.live.waitlist"]._ocd_notify_free(self.company_id, old_day, self.mode)
        day, hour, _end = self._ocd_studio_labels()
        self.message_post(body=self.env._("The team moved the live to %(day)s at %(hour)s.", day=day, hour=hour))
        if self.state == "confirmed":
            self._ocd_ticket_changed()
        return True

    def _ocd_confirm(self):
        """Confirm held lives once paid: notify the team and ask for a host when needed."""
        bookings = self.filtered(lambda b: b.state == "draft")
        bookings.write({"state": "confirmed", "hold_until": False})
        for booking in bookings:
            booking._ocd_notify_team()
        bookings._ocd_schedule_host_activity()
        return bookings

    def action_cancel(self):
        bookings = self.filtered(lambda b: b.state in ("draft", "confirmed"))
        released = [
            (booking.company_id, booking.company_id._ocd_to_local(booking.start_datetime).date(), booking.mode)
            for booking in bookings
        ]
        bookings.sudo().slot_ids.unlink()
        bookings.write({"state": "cancelled", "hold_until": False})
        bookings.activity_unlink([HOST_ACTIVITY])
        orders = bookings.sale_order_id.filtered(
            lambda o: o.state in ("draft", "sent")
            and all(b.state == "cancelled" for b in o.ocd_booking_ids)
        )
        if orders:
            orders.sudo()._action_cancel()
        Waitlist = self.env["ocd.live.waitlist"]
        for company, day, mode in set(released):
            Waitlist._ocd_notify_free(company, day, mode)
        return True

    def _ocd_move(self, start):
        """Move a confirmed live to `start`, until the limit of hours before the live."""
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(self.env._("Only a confirmed live can be moved."))
        limit = self.company_id.ocd_move_limit_hours
        if self.start_datetime - fields.Datetime.now() < timedelta(hours=limit):
            raise UserError(self.env._("A live can be moved until %s hours before it starts.", limit))
        percent = self.env["ocd.live.price.rule"]._ocd_percent(self.company_id, start, self.mode, self.product_id)
        if percent > (self.price_percent or 0.0):
            raise UserError(self.env._("This hour costs more: choose another hour, or book it apart."))
        old_day = self.company_id._ocd_to_local(self.start_datetime).date()
        self.start_datetime = start
        self.env["ocd.live.waitlist"]._ocd_notify_free(self.company_id, old_day, self.mode)
        self.message_post(body=self.env._("The vendor moved the live."))
        self._ocd_ticket_changed()
        return True

    def _ocd_send_ticket(self):
        """Send the ticket of the live to the vendor. Return whether it is on its way.
        Extended by ocd_live_whatsapp."""
        return False

    def _ocd_ticket_path(self):
        """Path of the ticket page with its secret (the one of the order), for a message."""
        self.ensure_one()
        order = self.sudo().sale_order_id
        if not order:
            return f"ocd/ticket/{self.id}"
        return f"ocd/ticket/{self.id}?access_token={order._portal_ensure_token()}"

    def action_mark_done(self):
        self.filtered(lambda b: b.state == "confirmed").write({"state": "done"})
        return True

    def action_publish_replay(self):
        for booking in self:
            if not booking.replay_url or not booking.replay_url.startswith("https://"):
                raise UserError(self.env._("Paste the https link of the replay video first."))
        self.write({"replay_published": True})
        return True

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "view_mode": "form",
        }

    # === NOTIFICATIONS === #

    def _ocd_local_labels(self, tz_name=None):
        """Return the day and the hours of the live in `tz_name`, by default the time zone of
        the vendor: their messages give their own hours (see _ocd_studio_labels for the team)."""
        self.ensure_one()
        tz_name = tz_name or self.partner_id._ocd_tz_name()
        day = format_datetime(self.env, self.start_datetime, tz=tz_name, dt_format="EEEE d MMMM")
        start = format_datetime(self.env, self.start_datetime, tz=tz_name, dt_format="HH:mm")
        end = format_datetime(self.env, self.end_datetime, tz=tz_name, dt_format="HH:mm")
        return day, start, end

    def _ocd_studio_labels(self):
        """The day and the hours of the live in the time of the studio, for the team."""
        self.ensure_one()
        return self._ocd_local_labels(self.company_id.ocd_studio_tz or "Africa/Lome")

    def _ocd_notify_team(self):
        """Announce the booking in the team channel: who, which business, when, where."""
        self.ensure_one()
        channel = self.company_id.ocd_lives_channel_id
        if not channel or not self.env["ocd.automation"]._ocd_enabled("booking_confirmed"):
            return
        day, start, end = self._ocd_studio_labels()
        mode = dict(self._fields["mode"]._description_selection(self.env))[self.mode]
        body = self.env._(
            "%(vendor)s (%(business)s, %(country)s) booked a live: %(mode)s, %(day)s, %(start)s - %(end)s. Ref. %(ref)s",
            vendor=self.partner_id.name,
            business=self.business or "-",
            country=self.vendor_country_id.name or "-",
            mode=mode,
            day=day,
            start=start,
            end=end,
            ref=self.name,
        )
        if self.studio_need and self.studio_need != "none":
            need = dict(self._fields["studio_need"]._description_selection(self.env))[self.studio_need]
            body = self.env._("%(body)s To prepare: %(need)s.", body=body, need=need)
        # sudo: the announcement is posted by the system, also from the payment flow
        channel.sudo().message_post(
            body=body, message_type="comment", subtype_xmlid="mail.mt_comment"
        )

    def _ocd_activity_user(self):
        self.ensure_one()
        return (
            self.user_id
            or self.company_id.ocd_live_responsible_id
            or self.env.ref("base.user_admin", raise_if_not_found=False)
        )

    def _ocd_schedule_host_activity(self):
        if not self.env["ocd.automation"]._ocd_enabled("remote_host"):
            return
        today = fields.Date.context_today(self)
        for booking in self:
            if (
                booking.mode != "remote"
                or booking.animatrice_id
                or not booking.company_id.ocd_require_animatrice
                or booking.state not in ("draft", "confirmed")
            ):
                continue
            activity_type = self.env.ref(HOST_ACTIVITY)
            if booking.activity_ids.filtered(lambda a: a.activity_type_id == activity_type):
                continue
            local_day = booking.company_id._ocd_to_local(booking.start_datetime).date()
            user = booking._ocd_activity_user()
            booking.activity_schedule(
                HOST_ACTIVITY,
                date_deadline=max(today, local_day - timedelta(days=1)),
                user_id=user.id if user else self.env.uid,
            )

    # === WEBSITE HELPERS === #

    @api.model
    def _ocd_taken_starts(self, starts, mode, company):
        """Return the starts among `starts` already taken in the calendar of `mode`."""
        if not starts:
            return set()
        # sudo: public pages, only the starts of the taken slots are read
        slots = self.env["ocd.live.booking.slot"].sudo().search([
            ("company_id", "=", company.id),
            ("calendar_key", "=", company._ocd_calendar_key(mode)),
            ("start_datetime", "in", starts),
        ])
        # An unpaid live whose hold is over does not take its slot any more
        expired = slots.booking_id._ocd_expired_holds()
        return set(slots.filtered(lambda slot: slot.booking_id not in expired).mapped("start_datetime"))

    @api.model
    def _ocd_get_day_slots(self, day, slot_count=1, company=None, mode="studio", tz_name=None):
        """Return the slots of `day` (a day of the studio) for the website, each with its
        availability, its hours in the time zone `tz_name` (the one of the person who books,
        else the studio's) and its code: the hour of the studio, "1430", key of the pages.

        A start is available when the `slot_count` slots from it are free in the calendar of
        `mode`, inside the day, not before the opening date and far enough in the future.
        """
        company = company or self.env.company
        tz_name = tz_name or company.ocd_studio_tz or "Africa/Lome"
        starts = company._ocd_slot_starts(day)
        taken = self._ocd_taken_starts(starts, mode, company)
        limit = fields.Datetime.now() + timedelta(hours=company.ocd_min_notice_hours)
        open_date = company.ocd_booking_open_date
        slots = []
        for index, start in enumerate(starts):
            span = starts[index:index + slot_count]
            available = (
                len(span) == slot_count
                and not taken.intersection(span)
                and start >= limit
                and (not open_date or day >= open_date)
            )
            local = tools.to_tz(start, tz_name)
            local_end = local + timedelta(hours=company.ocd_slot_hours * slot_count)
            slots.append({
                "start": start,
                "code": company._ocd_to_local(start).strftime("%H%M"),
                "label": local.strftime("%H:%M"),
                "end_label": local_end.strftime("%H:%M"),
                "local_day": local.date(),
                "taken": start in taken,
                "available": available,
            })
        return slots

    @api.model
    def _ocd_get_free_counts(self, days, slot_count=1, company=None, mode="studio"):
        """Return {day: number of available starts} for the website calendar."""
        company = company or self.env.company
        all_starts = {day: company._ocd_slot_starts(day) for day in days}
        flat = [start for starts in all_starts.values() for start in starts]
        taken = self._ocd_taken_starts(flat, mode, company)
        limit = fields.Datetime.now() + timedelta(hours=company.ocd_min_notice_hours)
        open_date = company.ocd_booking_open_date
        counts = {}
        for day, starts in all_starts.items():
            count = 0
            if not open_date or day >= open_date:
                for index, start in enumerate(starts):
                    span = starts[index:index + slot_count]
                    if len(span) == slot_count and not taken.intersection(span) and start >= limit:
                        count += 1
            counts[day] = count
        return counts

    @api.model
    def _ocd_book_from_website(self, partner, product, start, mode, studio_need="none"):
        """Create the quotation of the package and hold the chosen slot until it is paid. When
        the hour of the live costs more or less (price of the hours), the change is a line of
        the quotation."""
        company = self.env.company
        # sudo: called by the public booking pages once the inputs are validated
        order = self.env["sale.order"].sudo().create({
            "partner_id": partner.id,
            "company_id": company.id,
            "require_signature": False,
            # A positive prepayment makes the portal ask for the payment of the order
            "prepayment_percent": 1.0,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
        })
        package_line = order.order_line[:1]
        percent = self.env["ocd.live.price.rule"]._ocd_percent(company, start, mode, product)
        if percent:
            per_live = package_line.price_unit / max(product.ocd_live_count, 1)
            order._ocd_add_hour_price_line(start, mode, percent, per_live)
        return self.sudo().create({
            "partner_id": partner.id,
            "company_id": company.id,
            "mode": mode,
            "start_datetime": start,
            "slot_count": product.ocd_slot_count,
            "product_id": product.id,
            "sale_line_id": package_line.id,
            "studio_need": studio_need or "none",
            "price_percent": percent,
        })

    @api.model
    def _ocd_book_with_credit(self, credit, start, mode, studio_need="none"):
        """Place a live paid with a package bought before: confirmed at once. On an hour that
        costs more (price of the hours), the live is held until the difference is paid; a
        cheaper hour gives nothing back, the package being already paid."""
        credit.ensure_one()
        # Lock the credit row so that two simultaneous placements cannot both take its
        # last live.
        self.env.cr.execute(SQL("SELECT id FROM ocd_live_credit WHERE id = %s FOR UPDATE", credit.id))
        credit.invalidate_recordset(["used", "remaining", "state"])
        credit._ocd_check_usable()
        product = credit.product_id
        percent = self.env["ocd.live.price.rule"]._ocd_percent(credit.company_id, start, mode, product)
        vals = {
            "partner_id": credit.partner_id.id,
            "company_id": credit.company_id.id,
            "mode": mode,
            "start_datetime": start,
            "slot_count": product.ocd_slot_count,
            "product_id": product.id,
            "credit_id": credit.id,
            "studio_need": studio_need or "none",
            "price_percent": max(percent, 0.0),
        }
        if percent > 0:
            order = credit._ocd_hour_price_order(start, mode, percent)
            vals["sale_line_id"] = order.order_line[:1].id
            return self.sudo().create(vals)
        booking = self.sudo().create(vals)
        booking._ocd_confirm()
        return booking

    # === CRONS === #

    @api.model
    def _cron_release_expired_holds(self):
        """Release the held slots that were not paid in time."""
        now = fields.Datetime.now()
        held = self.search([("state", "=", "draft"), ("hold_until", "<", now)])
        paid = held.filtered(lambda booking: booking.sale_order_id.state == "sale")
        paid._ocd_confirm()
        expired = (held - paid)._ocd_expired_holds(now)
        if expired:
            _logger.info("Releasing %s unpaid live slots", len(expired))
            expired.action_cancel()

    # === HOLD OF AN UNPAID LIVE === #

    def _ocd_hold_end(self):
        """When the hour of this unpaid live is free again: after the time given to pay
        (« Slot Held During The Payment »), counted again from a payment started (it confirms
        itself within minutes), and, for a payment the vendor says sent, after the time given to
        the team to check it (« Slot Held For A Payment Checked By The Team »). A payment only
        started, or a method chosen then left, keeps the hour no longer."""
        self.ensure_one()
        company = self.company_id
        order = self.sale_order_id
        end = self.hold_until or self.create_date
        given = timedelta(minutes=company.ocd_hold_minutes or 10)
        for transaction in order.transaction_ids.filtered(lambda t: t.state in ("pending", "authorized")):
            end = max(end, transaction.create_date + given)
        for asked in (order.ocd_payment_declared_date, order.ocd_payment_help_date):
            if asked:
                end = max(end, asked + timedelta(hours=company.ocd_manual_hold_hours))
        return end

    def _ocd_expired_holds(self, now=None):
        """The unpaid lives among these whose hold is over: their hours can be booked again."""
        now = now or fields.Datetime.now()
        return self.filtered(lambda booking: (
            booking.state == "draft"
            and booking.sale_order_id.state != "sale"
            and not booking.sale_order_id.transaction_ids.filtered(lambda t: t.state == "done")
            and booking._ocd_hold_end() <= now
        ))

    @api.model
    def _cron_mark_done(self):
        self.search([("state", "=", "confirmed"), ("end_datetime", "<=", fields.Datetime.now())]).write(
            {"state": "done"}
        )

    @api.model
    def _cron_check_hosts(self):
        """Remind the team of the remote lives of the next 24 hours that have no host."""
        now = fields.Datetime.now()
        self.search([
            ("needs_host", "=", True),
            ("state", "=", "confirmed"),
            ("start_datetime", ">=", now),
            ("start_datetime", "<=", now + timedelta(hours=24)),
        ])._ocd_schedule_host_activity()
