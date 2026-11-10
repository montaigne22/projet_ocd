import logging
from datetime import timedelta

import psycopg2

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, format_date, format_datetime

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
        moving = any(key in vals for key in ("start_datetime", "slot_count", "company_id"))
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
            vals_list.extend(
                {"booking_id": booking.id, "company_id": booking.company_id.id, "start_datetime": start}
                for start in booking._ocd_slot_datetimes()
            )
        if not vals_list:
            return
        # sudo: slots are technical rows, the booking itself was checked by the access rules
        Slot = self.env["ocd.live.booking.slot"].sudo()
        taken = Slot.search_count(
            [
                ("company_id", "in", self.company_id.ids),
                ("start_datetime", "in", [vals["start_datetime"] for vals in vals_list]),
                ("booking_id", "not in", self.ids),
            ],
            limit=1,
        )
        if taken:
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
        bookings.sudo().slot_ids.unlink()
        bookings.write({"state": "cancelled", "hold_until": False})
        bookings.activity_unlink([HOST_ACTIVITY])
        orders = bookings.sale_order_id.filtered(
            lambda o: o.state in ("draft", "sent")
            and all(b.state == "cancelled" for b in o.ocd_booking_ids)
        )
        if orders:
            orders.sudo()._action_cancel()
        return True

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

    def _ocd_local_labels(self):
        """Return the day and the hours of the live in the time zone of the studio."""
        self.ensure_one()
        tz_name = self.company_id.ocd_studio_tz or "Africa/Lome"
        day = format_datetime(self.env, self.start_datetime, tz=tz_name, dt_format="EEEE d MMMM")
        start = format_datetime(self.env, self.start_datetime, tz=tz_name, dt_format="HH:mm")
        end = format_datetime(self.env, self.end_datetime, tz=tz_name, dt_format="HH:mm")
        return day, start, end

    def _ocd_notify_team(self):
        """Announce the booking in the team channel: who, which business, when, where."""
        self.ensure_one()
        channel = self.company_id.ocd_lives_channel_id
        if not channel:
            return
        day, start, end = self._ocd_local_labels()
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
    def _ocd_get_day_slots(self, day, slot_count=1, company=None):
        """Return the slots of `day` for the website, each with its availability.

        A start is available when the `slot_count` slots from it are free, inside the day,
        not before the opening date and far enough in the future.
        """
        company = company or self.env.company
        starts = company._ocd_slot_starts(day)
        # sudo: public page, only the starts of the taken slots are read
        taken = set(
            self.env["ocd.live.booking.slot"].sudo().search(
                [("company_id", "=", company.id), ("start_datetime", "in", starts)]
            ).mapped("start_datetime")
        )
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
            local = company._ocd_to_local(start)
            local_end = local + timedelta(hours=company.ocd_slot_hours * slot_count)
            slots.append({
                "start": start,
                "label": local.strftime("%H:%M"),
                "end_label": local_end.strftime("%H:%M"),
                "taken": start in taken,
                "available": available,
            })
        return slots

    @api.model
    def _ocd_get_free_counts(self, days, slot_count=1, company=None):
        """Return {day: number of available starts} for the website calendar."""
        company = company or self.env.company
        all_starts = {day: company._ocd_slot_starts(day) for day in days}
        flat = [start for starts in all_starts.values() for start in starts]
        taken = set(
            self.env["ocd.live.booking.slot"].sudo().search(
                [("company_id", "=", company.id), ("start_datetime", "in", flat)]
            ).mapped("start_datetime")
        )
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
        """Create the quotation of the package and hold the chosen slot until it is paid."""
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
        return self.sudo().create({
            "partner_id": partner.id,
            "company_id": company.id,
            "mode": mode,
            "start_datetime": start,
            "slot_count": product.ocd_slot_count,
            "product_id": product.id,
            "sale_line_id": order.order_line[:1].id,
            "studio_need": studio_need or "none",
        })

    @api.model
    def _ocd_book_with_credit(self, credit, start, mode, studio_need="none"):
        """Place a live paid with a package bought before: confirmed at once."""
        credit.ensure_one()
        # Lock the credit row so that two simultaneous placements cannot both take its
        # last live.
        self.env.cr.execute(SQL("SELECT id FROM ocd_live_credit WHERE id = %s FOR UPDATE", credit.id))
        credit.invalidate_recordset(["used", "remaining", "state"])
        credit._ocd_check_usable()
        booking = self.sudo().create({
            "partner_id": credit.partner_id.id,
            "company_id": credit.company_id.id,
            "mode": mode,
            "start_datetime": start,
            "slot_count": credit.product_id.ocd_slot_count,
            "product_id": credit.product_id.id,
            "credit_id": credit.id,
            "studio_need": studio_need or "none",
        })
        booking._ocd_confirm()
        return booking

    # === CRONS === #

    @api.model
    def _cron_release_expired_holds(self):
        """Release the held slots that were not paid in time."""
        now = fields.Datetime.now()
        expired = self.search([("state", "=", "draft"), ("hold_until", "<", now)])
        to_cancel = self.browse()
        for booking in expired:
            order = booking.sale_order_id
            if order.state == "sale":
                booking._ocd_confirm()
                continue
            transactions = order.transaction_ids
            if transactions.filtered(lambda t: t.state == "done"):
                continue  # the order is confirmed by the payment flow
            if transactions.filtered(lambda t: t.state in ("pending", "authorized")):
                manual_limit = booking.create_date + timedelta(hours=booking.company_id.ocd_manual_hold_hours)
                if now < manual_limit:
                    continue
            to_cancel |= booking
        if to_cancel:
            _logger.info("Releasing %s unpaid live slots", len(to_cancel))
            to_cancel.action_cancel()

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
