from datetime import timedelta

import pytz

from odoo import api, fields, models

from ..tools import day_text, hour_text

# Kinds of the cells of the planning, as in the legend of the design
KIND_STUDIO = "studio"  # at the studio, paid
KIND_REMOTE = "remote"  # remote, paid
KIND_TO_CHECK = "to_check"  # paid by hand (Mobile Money checked by the team), to check
KIND_HELD = "held"  # held during an online payment
KIND_FREE = "free"
KIND_CLOSED = "closed"


class OcdLivePlanning(models.AbstractModel):
    """Planning of the week for the team, as in the validated design (BoReservations): the
    hours of the studio in rows, the days in columns, one cell per slot, and the detail of
    the chosen slot beside it."""

    _name = "ocd.live.planning"
    _description = "OCD Live Planning"

    @api.model
    def get_planning_data(self, week_start=None):
        company = self.env.company
        today = company._ocd_local_today()
        open_date = company.ocd_booking_open_date
        if week_start:
            first = fields.Date.to_date(week_start)
        else:
            # Before the opening of the bookings, the first week of lives
            first = max(today, open_date) if open_date else today
        first -= timedelta(days=first.weekday())
        days = [first + timedelta(days=offset) for offset in range(7)]
        starts_by_day = {day: company._ocd_slot_starts(day) for day in days}
        times = [
            company._ocd_to_local(start).strftime("%H:%M")
            for start in next((starts for starts in starts_by_day.values() if starts), [])
        ] or [
            hour_text(company.ocd_first_slot_hour + index * company.ocd_slot_hours)
            for index in range(company.ocd_slots_per_day)
        ]
        by_start = self._ocd_bookings_by_start(company, days[0])
        now = fields.Datetime.now()
        rows, details = [], {}
        Booking = self.env["ocd.live.booking"]
        for index, time_label in enumerate(times):
            cells = []
            for day in days:
                starts = starts_by_day[day]
                key = f"{day.isoformat()}|{time_label}"
                if index >= len(starts):
                    cells.append({"key": key, "kind": KIND_CLOSED, "label": self.env._("Closed") if index == 0 else ""})
                    continue
                start = starts[index]
                bookings = by_start.get(start, Booking)
                if not bookings and open_date and day < open_date:
                    label = ""
                    if index == 0:
                        label = self.env._("Lives open on %s", day_text(self.env, open_date, "d MMM"))
                    cells.append({"key": key, "kind": KIND_CLOSED, "label": label})
                    continue
                past = start < now
                if not bookings:
                    cells.append({"key": key, "kind": KIND_FREE, "label": self.env._("Free"), "sub": "", "past": past})
                    details[key] = self._ocd_free_detail(company, day, start)
                    continue
                booking = bookings.sorted("start_datetime")[0]
                kind = self._ocd_kind(booking)
                cells.append({
                    "key": key,
                    "kind": kind,
                    "label": self.env._("Held") if kind == KIND_HELD else booking.partner_id.name,
                    "sub": self.env._("continued") if booking.start_datetime != start else self._ocd_sub(booking, kind),
                    "more": len(bookings) - 1,
                    "past": past,
                })
                details[key] = self._ocd_booking_detail(booking, kind)
            rows.append({"time": time_label, "cells": cells})
        return {
            "week_start": days[0].isoformat(),
            "previous": (days[0] - timedelta(days=7)).isoformat(),
            "next": (days[0] + timedelta(days=7)).isoformat(),
            "this_week": today in days,
            "range": self.env._(
                "%(start)s – %(end)s",
                start=day_text(self.env, days[0], "d MMM"),
                end=day_text(self.env, days[-1], "d MMM y"),
            ),
            "days": [
                {"key": day.isoformat(), "label": day_text(self.env, day, "EEE d", capital=True), "today": day == today}
                for day in days
            ],
            "rows": rows,
            "details": details,
            "default_key": self._ocd_default_key(rows, details, today),
            "hosts": [
                {"id": host.id, "name": host.name}
                for host in self.env["hr.employee"].search(
                    [("ocd_is_animatrice", "=", True), ("company_id", "in", (company.id, False))]
                )
            ],
            "note": self.env._(
                "One live at a time on the account of the studio. Hours of %s.", company.ocd_studio_city or "Lomé"
            ),
            "regie_action": self._ocd_regie_action(),
            "can_manage": self.env.user.has_group("ocd_live.group_ocd_live_manager"),
        }

    @api.model
    def _ocd_bookings_by_start(self, company, first_day):
        """Return {start of a slot: bookings} for the week starting on `first_day`, past lives
        included (they no longer hold their slots)."""
        week_start, _end = self.env["ocd.live.dashboard"]._ocd_day_bounds(first_day)
        week_end = week_start + timedelta(days=7)
        bookings = self.env["ocd.live.booking"].search([
            ("company_id", "=", company.id),
            ("state", "in", ("draft", "confirmed", "done")),
            ("start_datetime", "<", week_end),
            ("end_datetime", ">", week_start),
        ])
        by_start = {}
        for booking in bookings:
            for index in range(booking.slot_count or 1):
                start = booking.start_datetime + timedelta(hours=company.ocd_slot_hours * index)
                by_start[start] = by_start.get(start, booking.browse()) | booking
        return by_start

    @api.model
    def _ocd_default_key(self, rows, details, today):
        """The cell shown first: the live of now or the next one, else the first live of the week."""
        booked = sorted(
            (cell["key"] for row in rows for cell in row["cells"] if cell["kind"] not in (KIND_CLOSED, KIND_FREE)),
        )
        coming = [key for key in booked if key >= today.isoformat() and not details[key]["past"]]
        return (coming or booked or [False])[0]

    @api.model
    def _ocd_regie_action(self):
        """Hook: the action of the live control room (added by the shop)."""
        return False

    # === CELLS === #

    @api.model
    def _ocd_kind(self, booking):
        if booking.state == "draft":
            # sudo: only the state of the payments is read
            pending = booking.sudo().sale_order_id.transaction_ids.filtered(lambda tx: tx.state == "pending")
            return KIND_TO_CHECK if pending else KIND_HELD
        return KIND_STUDIO if booking.mode == "studio" else KIND_REMOTE

    @api.model
    def _ocd_sub(self, booking, kind):
        if kind == KIND_HELD:
            return self.env._("payment in progress")
        if kind == KIND_TO_CHECK:
            return self.env._("payment to check")
        if kind == KIND_STUDIO:
            needs = dict(booking._fields["studio_need"]._description_selection(self.env))
            if booking.studio_need and booking.studio_need != "none":
                return self.env._("Studio · %s", needs[booking.studio_need].lower())
            return self.env._("Studio")
        return self.env._("Remote · %s", booking.vendor_country_id.name or "")

    # === DETAIL OF A CELL === #

    @api.model
    def _ocd_when(self, company, start, end):
        local = company._ocd_to_local(start)
        return self.env._(
            "%(day)s · %(start)s – %(end)s (time of %(city)s)",
            day=day_text(self.env, local.date(), "EEE d MMM"),
            start=local.strftime("%H:%M"),
            end=company._ocd_to_local(end).strftime("%H:%M"),
            city=company.ocd_studio_city or "Lomé",
        )

    @api.model
    def _ocd_free_detail(self, company, day, start):
        waiting = self.env["ocd.live.waitlist"].search_count(
            [("company_id", "=", company.id), ("day", "=", day), ("state", "=", "waiting")]
        )
        return {
            "kind": KIND_FREE,
            "tag": self.env._("Free"),
            "title": self.env._("Free"),
            "when": self._ocd_when(company, start, start + timedelta(hours=company.ocd_slot_hours)),
            "rows": [
                {
                    "label": self.env._("Waiting list"),
                    "value": self.env._("%s people", waiting) if waiting > 1
                    else (self.env._("1 person") if waiting else self.env._("Nobody")),
                },
                {"label": self.env._("Price"), "value": self.env._("Depends on the package chosen")},
            ],
            "start": fields.Datetime.to_string(start),
            "waiting": waiting,
            "past": start < fields.Datetime.now(),
        }

    @api.model
    def _ocd_booking_detail(self, booking, kind):
        company = booking.company_id
        tags = {
            KIND_STUDIO: self.env._("At the studio of %s", company.ocd_studio_city or "Lomé"),
            KIND_REMOTE: self.env._("Remote"),
            KIND_TO_CHECK: self.env._("Payment to check"),
            KIND_HELD: self.env._("Held during a payment"),
        }
        rows = []
        if kind == KIND_HELD:
            rows.append({"label": self.env._("Vendor"), "value": booking.partner_id.name})
            if booking.hold_until:
                rows.append({
                    "label": self.env._("Released at"),
                    "value": self.env._(
                        "%s if not paid", company._ocd_to_local(booking.hold_until).strftime("%H:%M")
                    ),
                })
        else:
            country = booking.vendor_country_id.name
            rows.append({
                "label": self.env._("Vendor"),
                "value": f"{booking.partner_id.name} · {country}" if country else booking.partner_id.name,
            })
        if booking.product_id:
            rows.append({"label": self.env._("Package"), "value": self._ocd_package_text(booking)})
        rows.append({"label": self.env._("Payment"), "value": self._ocd_payment_text(booking)})
        if booking.mode == "studio":
            needs = dict(booking._fields["studio_need"]._description_selection(self.env))
            rows.append({"label": self.env._("At the studio"), "value": needs.get(booking.studio_need) or "—"})
        else:
            rows.append({"label": self.env._("At the vendor"), "value": self._ocd_time_gap(booking)})
        now = fields.Datetime.now()
        return {
            "kind": kind,
            "tag": tags[kind],
            "title": self.env._("Held slot") if kind == KIND_HELD else booking.partner_id.name,
            "when": self._ocd_when(company, booking.start_datetime, booking.end_datetime),
            "rows": rows,
            "booking_id": booking.id,
            "remote": booking.mode == "remote",
            "host_id": booking.animatrice_id.id or False,
            "live_now": booking.state == "confirmed" and booking.start_datetime <= now < booking.end_datetime,
            "can_move": booking.state in ("draft", "confirmed") and booking.start_datetime > now,
            "can_cancel": booking.state in ("draft", "confirmed"),
            "past": booking.end_datetime <= now,
        }

    @api.model
    def _ocd_package_text(self, booking):
        credit = booking.credit_id
        if not credit or credit.quantity <= 1:
            return booking.product_id.name
        placed = credit.booking_ids.filtered(lambda b: b.state != "cancelled").sorted("start_datetime")
        position = (placed.ids.index(booking.id) + 1) if booking.id in placed.ids else len(placed)
        return self.env._(
            "%(package)s · live %(position)s of %(count)s",
            package=booking.product_id.name,
            position=position,
            count=credit.quantity,
        )

    @api.model
    def _ocd_payment_text(self, booking):
        # sudo: only the state and the provider of the payments are read
        transactions = booking.sudo().sale_order_id.transaction_ids
        done = transactions.filtered(lambda tx: tx.state == "done")[:1]
        pending = transactions.filtered(lambda tx: tx.state == "pending")[:1]
        if booking.state == "draft":
            if pending:
                return self.env._("To check · %s", pending.provider_id.name)
            return self.env._("Payment in progress")
        if done:
            return self.env._("Paid · %s", done.provider_id.name)
        if booking.credit_id and booking.credit_id.sale_line_id.order_id != booking.sale_order_id:
            return self.env._("Paid with the package")
        return self.env._("Paid")

    @api.model
    def _ocd_time_gap(self, booking):
        """Return the hour of the vendor compared to the studio, e.g. "1 h later than in Lomé"."""
        company = booking.company_id
        city = company.ocd_studio_city or "Lomé"
        zones = pytz.country_timezones.get((booking.vendor_country_id.code or "").upper())
        if not zones:
            return "—"
        start = pytz.utc.localize(booking.start_datetime)
        gap = (
            start.astimezone(pytz.timezone(zones[0])).utcoffset() - start.astimezone(company._ocd_tz()).utcoffset()
        ).total_seconds() / 3600
        if not gap:
            return self.env._("Same time as in %s", city)
        hours = f"{abs(gap):g}"
        if gap > 0:
            return self.env._("%(hours)s h later than in %(city)s", hours=hours, city=city)
        return self.env._("%(hours)s h earlier than in %(city)s", hours=hours, city=city)

    # === ACTIONS OF THE PANEL === #

    @api.model
    def ocd_offer_free_slot(self, start):
        """Tell the waiting list of the day that this slot is free."""
        company = self.env.company
        start = fields.Datetime.to_datetime(start)
        day = company._ocd_to_local(start).date()
        Waitlist = self.env["ocd.live.waitlist"]
        domain = [("company_id", "=", company.id), ("day", "=", day), ("state", "=", "waiting")]
        count = Waitlist.search_count(domain)
        Waitlist._ocd_notify_free(company, day, "studio")
        return count
