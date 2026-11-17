"""The figures of a vendor (chantier 3 of the roadmap, with 3.3 « Sales per product » of the plan of
« My products », design MesChiffres). One calculation, read by the page « My figures », the card of
« My space », the line « Sold » of each product in « My products », the summary of the week on
WhatsApp and the back office:

- Sales: the confirmed orders (paid, or to pay at the door), without the cancelled ones nor the
  parcels returned; the price of the products of the vendor, without the delivery. An order of
  several vendors counts for each their part. The evolution compares with the period before of
  the same length.
- The lives: « Opened from OCD » are the taps on « Watch » (cards of the feed, boutique, messages
  to the followers), the visits of the boutique during the live are the ones of the control room,
  the sales of a live are the orders of the visitors who came during the live, placed during it or
  in the hours after (setting): the cart remembers the live, the lines of the vendor are noted with
  it when the order is confirmed.
- Visits of the boutique: one per phone and per day; WhatsApp contacts and the stores: the taps
  already counted under each product and store (ocd_live: ocd.vendor.count; ocd.vendor.place.tap).
- Best hours: the hour of the orders at the hour of the vendor. Loyal customers: 2 orders or more
  in 12 months (setting), shown by their first name and initial only, never their number.

The detail is for OCD Business (offered during the launch); the sales and the pieces stay for all."""
import math
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.http import request
from odoo.tools.misc import format_amount, formatLang

from odoo.addons.ocd_live import tools

# The periods of the page: days
PERIODS = (7, 30, 90)
DEFAULT_PERIOD = 30
# The loyal customers and the last sale of a product look back this far
YEAR_DAYS = 365
# The best hours look back this far
HOURS_DAYS = 90
# The slots of the day: (from hour, local hour of a live proposed for it)
SLOTS = ((0, 10), (12, 13), (15, 16), (18, 19))
# A product with this many WhatsApp contacts and no sale: « a lot of interest, no sale »
INTEREST_CONTACTS = 5
# The products of the page
PRODUCTS_SHOWN = 50
# The loyal customers shown before « See the N »
LOYAL_SHOWN = 3
# The summary of the week leaves in one run of the scheduled task: the others the next hour
SUMMARY_BATCH = 200


def _slot(hour):
    for index in range(len(SLOTS) - 1, -1, -1):
        if hour >= SLOTS[index][0]:
            return index
    return 0


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_live_seen_ids = fields.Many2many(
        comodel_name="ocd.live.booking", relation="sale_order_ocd_live_seen_rel", column1="order_id",
        column2="booking_id", string="Lives Seen", copy=False, readonly=True,
        help="The lives whose boutique the customer visited during the live, while the cart was open: "
        "the lines of their vendor count for the live (figures of the vendor).",
    )

    def _ocd_note_lives(self, lives):
        """The cart remembers the lives the customer visited, while they still count: during the
        live and in the hours after (setting)."""
        for order in self.filtered(lambda order: order.state == "draft"):
            kept = lives.filtered(lambda live: live._ocd_sales_open()) - order.ocd_live_seen_ids
            if kept:
                order.sudo().ocd_live_seen_ids = [fields.Command.link(live.id) for live in kept]

    def _verify_cart_after_update(self):
        """The lives of this browser (the boutiques visited during a live) go with the cart."""
        super()._verify_cart_after_update()
        if request and request.session.get("ocd_live_visits"):
            lives = self.env["ocd.live.booking"].sudo().browse(request.session["ocd_live_visits"]).exists()
            self._ocd_note_lives(lives)

    def _action_confirm(self):
        result = super()._action_confirm()
        self._ocd_note_live_lines()
        return result

    def _ocd_note_live_lines(self):
        """Each line of a vendor counts for their last live seen with this cart."""
        for order in self.sudo().filtered("ocd_live_seen_ids"):
            for line in order.order_line.filtered(lambda line: line.ocd_vendor_id and not line.ocd_live_id):
                lives = order.ocd_live_seen_ids.filtered(lambda live: live.partner_id == line.ocd_vendor_id)
                if lives:
                    line.ocd_live_id = lives.sorted("start_datetime")[-1]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ocd_live_id = fields.Many2one(
        comodel_name="ocd.live.booking", string="Sold During The Live", copy=False, readonly=True,
        index="btree_not_null", ondelete="set null",
        help="The customer came to the boutique during this live and ordered during it or in the hours after.",
    )


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    def _ocd_sales_open(self, now=None):
        """Whether an order placed now still counts for the live: during it, or in the hours after
        its end (setting)."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        hours = (self.company_id or self.env.company).ocd_live_sales_hours
        return self.state in ("confirmed", "done") and self.start_datetime <= now <= self.end_datetime + timedelta(hours=hours)


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_live_sales_hours = fields.Integer(
        string="Sales Of A Live",
        default=3,
        help="The orders of the visitors of a live count for it when placed during the live or until "
        "this many hours after its end.",
    )
    ocd_loyal_orders = fields.Integer(
        string="Loyal Customers",
        default=2,
        help="A customer who ordered this many times or more in 12 months is a loyal customer of the vendor.",
    )
    ocd_week_summary_weekday = fields.Selection(
        selection=[("0", "Monday"), ("1", "Tuesday"), ("2", "Wednesday"), ("3", "Thursday"), ("4", "Friday"),
                   ("5", "Saturday"), ("6", "Sunday")],
        string="Day Of The Summary Of The Week",
        default="0",
        help="The vendors who asked for it receive their week on WhatsApp on this day, at their hour.",
    )
    ocd_week_summary_hour = fields.Integer(
        string="Hour Of The Summary Of The Week",
        default=9,
        help="At the hour of the vendor.",
    )


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_week_summary = fields.Boolean(
        string="Summary Of The Week On WhatsApp",
        copy=False,
        help="The vendor asked for their week on WhatsApp (« My figures »): sales, visits, the best seller.",
    )
    ocd_week_summary_sent_at = fields.Datetime(string="Summary Sent At", copy=False, readonly=True)

    def action_ocd_view_figures(self):
        """« Figures » of the form of the vendor: their page « My figures », as they see it, like
        « See the space »."""
        action = self.action_ocd_view_space()
        action["url"] += "&vers=chiffres"
        return action

    # === THE SUMMARY OF THE WEEK === #

    def _ocd_week_summary_due(self, now):
        """Whether the summary of the vendor leaves now: they asked for it, their day, from the hour
        of the settings at their hour, not sent today already."""
        self.ensure_one()
        if not self.ocd_week_summary:
            return False
        company = self.company_id or self.env.company
        tz = pytz.timezone(self._ocd_tz_name())
        local = pytz.utc.localize(now).astimezone(tz)
        if local.weekday() != int(company.ocd_week_summary_weekday or 0) or local.hour < company.ocd_week_summary_hour:
            return False
        if self.ocd_week_summary_sent_at:
            last = pytz.utc.localize(self.ocd_week_summary_sent_at).astimezone(tz).date()
            if last == local.date():
                return False
        return True

    @api.model
    def _ocd_send_week_summaries(self, now=None):
        """The summary of the week to the vendors who asked for it (scheduled task, every hour)."""
        if not self.env["ocd.automation"]._ocd_enabled("week_summary"):
            return
        now = now or fields.Datetime.now()
        vendors = self.sudo().search([("ocd_is_vendor", "=", True), ("ocd_week_summary", "=", True),
                                      ("ocd_vendor_state", "=", "approved")], order="id")
        sent = 0
        for vendor in vendors:
            if sent >= SUMMARY_BATCH:
                break
            if not vendor._ocd_week_summary_due(now):
                continue
            vendor.ocd_week_summary_sent_at = now
            summary = self.env["ocd.vendor.figures"]._ocd_week_summary(vendor, now)
            if summary:
                vendor._ocd_tell_week_summary(summary)
            sent += 1

    def _ocd_tell_week_summary(self, summary):
        """Send the summary of the week to the vendor (ocd_live_shop_whatsapp)."""


class OcdVendorFigures(models.AbstractModel):
    """The one calculation of the figures of a vendor."""

    _name = "ocd.vendor.figures"
    _description = "Figures Of A Vendor"

    # === THE SALES === #

    @api.model
    def _ocd_lines(self, vendor, start, end=None):
        """The lines sold by `vendor` in orders confirmed from `start` to `end` (included), without the
        delivery, the cancelled orders and the parcels returned."""
        domain = [
            ("ocd_vendor_id", "=", vendor.id), ("state", "=", "sale"), ("is_delivery", "=", False),
            ("display_type", "=", False), ("order_id.date_order", ">=", start),
        ]
        if end:
            # Up to now included: an order confirmed this very second counts
            domain.append(("order_id.date_order", "<=", end))
        lines = self.env["sale.order.line"].sudo().search(domain)
        return lines.filtered(lambda line: not self._ocd_line_returned(line))

    @api.model
    def _ocd_line_returned(self, line):
        """A line whose parcels all came back (or whose moves were all cancelled) is not a sale."""
        moves = line.move_ids
        if not moves:
            return False
        if all(move.state == "cancel" for move in moves):
            return True
        pickings = moves.picking_id
        return bool(pickings) and all(picking.ocd_stage in ("returned", "cancelled") for picking in pickings)

    @api.model
    def _ocd_amount(self, line, currency):
        """The price paid for `line` (taxes included, without the delivery) in `currency`."""
        amount = line.price_total
        if line.currency_id and line.currency_id != currency:
            company = line.company_id or self.env.company
            amount = line.currency_id._convert(amount, currency, company, line.order_id.date_order.date())
        return amount

    @api.model
    def _ocd_sums(self, lines, currency):
        """{amount, pieces, orders} of `lines`."""
        return {
            "amount": sum(self._ocd_amount(line, currency) for line in lines),
            "pieces": int(sum(lines.mapped("product_uom_qty"))),
            "orders": len(lines.order_id),
        }

    @api.model
    def _ocd_currency(self, vendor):
        return (vendor.company_id or self.env.company).currency_id

    @api.model
    def _ocd_money(self, amount, currency):
        return format_amount(self.env, amount, currency)

    @api.model
    def _ocd_number(self, value):
        """« 1 240 »: a count written for the language of the page."""
        return formatLang(self.env, value, digits=0)

    # === EVOLUTION === #

    @api.model
    def _ocd_evolution(self, now, before, days=None):
        """{"cls", "text"}: « ▲ 18 % », « ▼ 5 % », « = as before », « New »; with `days`, the
        whole sentence of the first tile: « ▲ 18 % compared with the 30 days before »."""
        _ = self.env._
        if not before:
            if not now:
                return {"cls": "flat", "text": _("= as before")}
            return {"cls": "up", "text": _("▲ new")}
        percent = round((now - before) * 100 / before)
        if percent == 0:
            return {"cls": "flat", "text": _("= as before")}
        arrow = "▲" if percent > 0 else "▼"
        text = f"{arrow} {abs(percent)} %"
        if days:
            text = {
                7: _("%s compared with the 7 days before", text),
                30: _("%s compared with the 30 days before", text),
                90: _("%s compared with the 3 months before", text),
            }.get(days, text)
        return {"cls": "up" if percent > 0 else "down", "text": text, "percent": percent}

    # === THE PAGE === #

    @api.model
    def _ocd_period(self, value):
        value = int(value) if str(value or "").isdigit() else DEFAULT_PERIOD
        return value if value in PERIODS else DEFAULT_PERIOD

    @api.model
    def _ocd_figures(self, vendor, days=DEFAULT_PERIOD, now=None, detail=True):
        """Everything « My figures » shows for the last `days` days: the tiles and their evolution;
        with `detail` (OCD Business), the lives, the best hours, the loyal customers, the products
        and the stores."""
        vendor = vendor.sudo()
        now = now or fields.Datetime.now()
        days = self._ocd_period(days)
        start, before = now - timedelta(days=days), now - timedelta(days=2 * days)
        currency = self._ocd_currency(vendor)
        year_lines = self._ocd_lines(vendor, now - timedelta(days=max(YEAR_DAYS, 2 * days)), now)
        lines = year_lines.filtered(lambda line: line.order_id.date_order >= start)
        lines_before = year_lines.filtered(lambda line: before <= line.order_id.date_order < start)
        sums, sums_before = self._ocd_sums(lines, currency), self._ocd_sums(lines_before, currency)
        Count = self.env["ocd.vendor.count"]
        today = tools.to_tz(now, vendor._ocd_tz_name()).date()
        first, first_before = today - timedelta(days=days - 1), today - timedelta(days=2 * days - 1)
        visits = Count._ocd_totals(vendor, "visit", first, today)
        visits_before = Count._ocd_totals(vendor, "visit", first_before, first - timedelta(days=1))
        contacts_by = Count._ocd_totals(vendor, "contact", first, today, by_record=True)
        contacts = sum(contacts_by.values())
        contacts_before = Count._ocd_totals(vendor, "contact", first_before, first - timedelta(days=1))
        _ = self.env._
        figures = {
            "days": days,
            "currency": currency,
            "sales": sums,
            "amount": self._ocd_money(sums["amount"], currency),
            "amount_evolution": self._ocd_evolution(sums["amount"], sums_before["amount"], days),
            "pieces_line": _("1 order") if sums["orders"] == 1 else _("%s orders", sums["orders"]),
            "visits": visits,
            "visits_text": self._ocd_number(visits),
            "visits_evolution": self._ocd_evolution(visits, visits_before),
            "contacts": contacts,
            "contacts_text": self._ocd_number(contacts),
            "pieces_text": self._ocd_number(sums["pieces"]),
            "contacts_evolution": self._ocd_evolution(contacts, contacts_before),
            "detail": detail,
        }
        if not detail:
            return figures
        lives = self._ocd_lives(vendor, start, now, currency)
        figures.update({
            "lives": lives,
            "idea": self._ocd_idea(sums["amount"], lives, days),
            "hours": self._ocd_hours(vendor, year_lines.filtered(
                lambda line: line.order_id.date_order >= now - timedelta(days=HOURS_DAYS)
            ), now, currency),
            "loyal": self._ocd_loyal(vendor, year_lines.filtered(
                lambda line: line.order_id.date_order >= now - timedelta(days=YEAR_DAYS)
            ), currency),
            "products": self._ocd_products(vendor, lines, year_lines, contacts_by, currency, now, days),
            "stores": self._ocd_stores(vendor, start, now),
        })
        return figures

    # --- The lives --- #

    @api.model
    def _ocd_lives(self, vendor, start, now, currency):
        """The lives of the vendor in the period, the newest first: when, opened from OCD, visits
        of the boutique, pieces and amount sold, new followers, best seller, replay."""
        _ = self.env._
        bookings = self.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id), ("state", "in", ("confirmed", "done")),
            ("start_datetime", ">=", start), ("start_datetime", "<=", now),
        ], order="start_datetime desc")
        if not bookings:
            return []
        watched = self.env["ocd.vendor.count"]._ocd_record_totals(vendor, "watch", bookings.ids)
        lines = self.env["sale.order.line"].sudo().search([
            ("ocd_live_id", "in", bookings.ids), ("state", "=", "sale"), ("is_delivery", "=", False),
        ]).filtered(lambda line: not self._ocd_line_returned(line))
        by_live = lines.grouped("ocd_live_id")
        Follower = self.env["ocd.vendor.follower"].sudo().with_context(active_test=False)
        hours = (vendor.company_id or self.env.company).ocd_live_sales_hours
        tz_name = vendor._ocd_tz_name()
        rows = []
        for booking in bookings:
            sold = by_live.get(booking, self.env["sale.order.line"])
            pieces = defaultdict(float)
            for line in sold:
                pieces[line.product_id.product_tmpl_id] += line.product_uom_qty
            star = max(pieces, key=pieces.get) if pieces else booking.moment_ids[:1].product_tmpl_id
            local = tools.to_tz(booking.start_datetime, tz_name)
            minutes = int((booking.end_datetime - booking.start_datetime).total_seconds() // 60)
            amount = sum(self._ocd_amount(line, currency) for line in sold)
            count = int(sum(pieces.values()))
            followers = Follower.search_count([
                ("vendor_id", "=", vendor.id), ("followed_at", ">=", booking.start_datetime),
                ("followed_at", "<=", booking.end_datetime + timedelta(hours=hours)),
            ])
            rows.append({
                "booking": booking,
                "when": " · ".join([
                    tools.day_text(self.env, local.date(), "EEE d MMM", capital=True),
                    self._ocd_hour(local.hour, local.minute),
                    self._ocd_duration(minutes),
                ]),
                "opened": self._ocd_number(watched.get(booking.id, 0)),
                "visits": self._ocd_number(booking.ocd_visit_count),
                "pieces": count,
                "pieces_text": _("1 piece") if count == 1 else _("%s pieces", count),
                "amount_value": amount,
                "amount": self._ocd_money(amount, currency),
                "followers": f"+{followers}" if followers else "0",
                "star": star.name or "-",
                "replay": f"/ocd/boutique/{vendor.id}/replay?live={booking.id}"
                if booking.replay_published and booking.replay_url else False,
                "best": False,
                "local": local,
            })
        if len(rows) > 1:
            best = max(rows, key=lambda row: row["amount_value"])
            if best["amount_value"] > 0:
                best["best"] = True
        return rows

    @api.model
    def _ocd_hour(self, hour, minute=0):
        """« 19 h », « 13 h 30 » (French), « 19:00 »."""
        if (self.env.lang or "").startswith("fr"):
            return f"{hour} h {minute:02d}" if minute else f"{hour} h"
        return f"{hour:02d}:{minute:02d}"

    @api.model
    def _ocd_duration(self, minutes):
        """« 45 min », « 1 h », « 1 h 10 »."""
        if minutes < 60:
            return self.env._("%s min", minutes)
        return f"{minutes // 60} h {minutes % 60:02d}" if minutes % 60 else f"{minutes // 60} h"

    @api.model
    def _ocd_idea(self, amount, lives, days):
        """The sentence of help under the tiles: « 82 % of your sales come from your lives. Your live
        of Saturday 9 November alone made 41 % of these 30 days. »"""
        _ = self.env._
        live_amount = sum(row["amount_value"] for row in lives)
        if amount <= 0:
            if lives:
                return _("No sale on these days yet: show your best products in your next live.")
            return False
        if live_amount <= 0:
            return _("Your sales come from your boutique: a live shows your products to many more customers.")
        share = min(round(live_amount * 100 / amount), 100)
        text = _("%s %% of your sales come from your lives.", share)
        best = max(lives, key=lambda row: row["amount_value"])
        best_share = round(best["amount_value"] * 100 / amount)
        if len(lives) > 1 and best_share >= 25:
            day = tools.day_text(self.env, best["local"].date(), "EEEE d MMMM")
            text = " ".join([text, {
                7: _("Your live of %(day)s alone made %(share)s %% of these 7 days.", day=day, share=best_share),
                30: _("Your live of %(day)s alone made %(share)s %% of these 30 days.", day=day, share=best_share),
                90: _("Your live of %(day)s alone made %(share)s %% of these 3 months.", day=day, share=best_share),
            }[days]])
        return text

    # --- The best hours --- #

    @api.model
    def _ocd_hours(self, vendor, lines, now, currency):
        """When the customers order, at the hour of the vendor, over 3 months: {"rows": [{"label",
        "cells": [level 0 to 4] × 7}], "days": [initials], "line", "lives_line", "book": {weekday,
        hour, label}}."""
        _ = self.env._
        tz_name = vendor._ocd_tz_name()
        grid = [[0] * 7 for _slot_row in SLOTS]
        for order in lines.order_id:
            local = tools.to_tz(order.date_order, tz_name)
            grid[_slot(local.hour)][local.weekday()] += 1
        top = max(max(row) for row in grid)
        labels = [_("Morning"), _("Noon"), _("Afternoon"), _("Evening")]
        monday = (tools.to_tz(now, tz_name).date() - timedelta(days=tools.to_tz(now, tz_name).weekday()))
        initials = [tools.day_text(self.env, monday + timedelta(days=day), "EEEEE", capital=True) for day in range(7)]
        names = [tools.day_text(self.env, monday + timedelta(days=day), "EEEE") for day in range(7)]
        result = {
            "days": initials,
            "rows": [{
                "label": labels[index],
                "cells": [{"level": math.ceil(4 * count / top) if top and count else 0, "count": count,
                           "title": f"{names[day]} · {labels[index]} · {count}"} for day, count in enumerate(grid[index])],
            } for index in range(len(SLOTS))],
            "legend": _("Morning until 12:00 · Noon 12:00 to 15:00 · Afternoon 15:00 to 18:00 · Evening from 18:00"),
            "enough": len(lines.order_id) >= 5,
            "line": False,
            "lives_line": False,
            "book": False,
        }
        if not top:
            return result
        best_slot, best_day = max(
            ((slot, day) for slot in range(len(SLOTS)) for day in range(7)), key=lambda cell: grid[cell[0]][cell[1]]
        )
        moments = [_("morning"), _("at noon"), _("afternoon"), _("evening")]
        result["line"] = _("Your customers buy mostly on %(day)s %(moment)s.", day=names[best_day], moment=moments[best_slot])
        book_day, book_hour = best_day, SLOTS[best_slot][1]
        # The lives of the same day and hour against the others
        bookings = self.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id), ("state", "in", ("confirmed", "done")),
            ("start_datetime", ">=", now - timedelta(days=HOURS_DAYS)), ("start_datetime", "<=", now),
        ])
        if len(bookings) > 1:
            sold = self.env["sale.order.line"].sudo().search([
                ("ocd_live_id", "in", bookings.ids), ("state", "=", "sale"), ("is_delivery", "=", False),
            ]).filtered(lambda line: not self._ocd_line_returned(line))
            amounts = defaultdict(float)
            for line in sold:
                amounts[line.ocd_live_id] += self._ocd_amount(line, currency)
            groups = defaultdict(list)
            for booking in bookings:
                local = tools.to_tz(booking.start_datetime, tz_name)
                groups[local.weekday(), local.hour].append(amounts[booking])
            if len(groups) > 1:
                (day, hour), values = max(groups.items(), key=lambda item: sum(item[1]) / len(item[1]))
                others = [amount for key, group in groups.items() if key != (day, hour) for amount in group]
                mean, others_mean = sum(values) / len(values), sum(others) / len(others)
                if others_mean > 0 and mean >= 1.5 * others_mean:
                    ratio = mean / others_mean
                    times = str(round(ratio)) if ratio >= 2 else f"{ratio:.1f}".replace(".", "," if (
                        self.env.lang or "").startswith("fr") else ".")
                    result["lives_line"] = _(
                        "Your lives on %(day)s at %(hour)s sell %(times)s times more than the others.",
                        day=names[day], hour=self._ocd_hour(hour), times=times,
                    )
                    book_day, book_hour = day, hour
                elif mean > 0 and others_mean == 0:
                    book_day, book_hour = day, hour
        result["book"] = {
            "weekday": book_day,
            "hour": book_hour,
            "label": _("Book a live on %(day)s at %(hour)s", day=names[book_day], hour=self._ocd_hour(book_hour)),
        }
        return result

    # --- The loyal customers --- #

    @api.model
    def _ocd_loyal(self, vendor, lines, currency):
        """The customers who ordered 2 times or more in 12 months (setting), the most loyal first:
        their first name and initial only, never their number."""
        _ = self.env._
        threshold = max((vendor.company_id or self.env.company).ocd_loyal_orders, 2)
        stats = defaultdict(lambda: {"orders": set(), "amount": 0.0, "last": None})
        total = 0.0
        for line in lines:
            order = line.order_id
            stat = stats[order.partner_id]
            stat["orders"].add(order.id)
            amount = self._ocd_amount(line, currency)
            stat["amount"] += amount
            total += amount
            stat["last"] = max(stat["last"] or order.date_order, order.date_order)
        loyal = sorted(
            ((partner, stat) for partner, stat in stats.items() if len(stat["orders"]) >= threshold),
            key=lambda item: (-len(item[1]["orders"]), -item[1]["amount"]),
        )
        Review = self.env["ocd.vendor.review"]
        tz_name = vendor._ocd_tz_name()
        rows = []
        for partner, stat in loyal:
            name = Review._ocd_author(partner.name)
            count = len(stat["orders"])
            last = tools.day_text(self.env, tools.to_tz(stat["last"], tz_name).date(), "d MMM")
            rows.append({
                "name": name,
                "initials": "".join(word[0] for word in name.replace(".", "").split()[:2]).upper(),
                "line": _("%(count)s orders · last on %(day)s", count=count, day=last),
                "short": f"{name} ({count})",
                "amount": self._ocd_money(stat["amount"], currency),
            })
        partners = self.env["res.partner"].browse([partner.id for partner, _stat in loyal])
        following = self.env["ocd.vendor.follower"].sudo().search_count([
            ("vendor_id", "=", vendor.id), ("partner_id", "in", partners.ids),
        ]) if partners else 0
        share = round(sum(stat["amount"] for _partner, stat in loyal) * 100 / total) if total else 0
        count = len(rows)
        return {
            "rows": rows,
            "shown": rows[:LOYAL_SHOWN],
            "more": rows[LOYAL_SHOWN:],
            "line": (_("1 customer bought %(times)s times or more: %(share)s %% of your sales.", times=threshold, share=share)
                     if count == 1 else _("%(count)s customers bought %(times)s times or more: %(share)s %% of your sales.",
                                          count=count, times=threshold, share=share)) if count
            else _("No customer has bought %s times from you yet: your followers come back more often.", threshold),
            "see_all": _("See the %s", count),
            "following": (_("1 of them follows you and receives your news.") if following == 1 else
                          _("%s of them follow you and receive your news.", following)) if following else False,
        }

    # --- The products (3.3) --- #

    @api.model
    def _ocd_product_sales(self, vendor, products, now=None, days=30):
        """{product id: (pieces sold in the last `days` days, date of the last sale in 12 months)}:
        the line « Sold » of « My products », the same calculation as the page."""
        now = now or fields.Datetime.now()
        lines = self._ocd_lines(vendor, now - timedelta(days=YEAR_DAYS), now)
        result = {product.id: [0, None] for product in products}
        since = now - timedelta(days=days)
        for line in lines:
            template = line.product_id.product_tmpl_id.id
            if template not in result:
                continue
            row = result[template]
            if line.order_id.date_order >= since:
                row[0] += int(line.product_uom_qty)
            row[1] = max(row[1] or line.order_id.date_order, line.order_id.date_order)
        return {key: tuple(value) for key, value in result.items()}

    @api.model
    def _ocd_when_text(self, vendor, moment, now=None):
        """« today », « yesterday », « 4 days ago », « on 3 Sep. » at the hour of the vendor."""
        _ = self.env._
        tz_name = vendor._ocd_tz_name()
        day = tools.to_tz(moment, tz_name).date()
        today = tools.to_tz(now or fields.Datetime.now(), tz_name).date()
        delta = (today - day).days
        if delta <= 0:
            return _("today")
        if delta == 1:
            return _("yesterday")
        if delta < 30:
            return _("%s days ago", delta)
        return _("on %s", tools.day_text(self.env, day, "d MMM"))

    @api.model
    def _ocd_sold_line(self, vendor, pieces, last, now=None):
        """« Sold: 14 in 30 days · last sale yesterday » under a product of « My products »."""
        _ = self.env._
        if not last:
            return False
        when = self._ocd_when_text(vendor, last, now)
        if pieces == 1:
            return _("Sold: 1 in 30 days · last sale %s", when)
        return _("Sold: %(count)s in 30 days · last sale %(when)s", count=pieces, when=when)

    @api.model
    def _ocd_products(self, vendor, lines, year_lines, contacts_by, currency, now, days=DEFAULT_PERIOD):
        """The products of the vendor in the period: pieces, amount, last sale, WhatsApp contacts,
        sold during the lives, customers waiting; the best sellers first."""
        _ = self.env._
        products = self.env["product.template"].sudo().search([
            ("ocd_vendor_id", "=", vendor.id), ("ocd_review_state", "=", "approved"),
        ])
        stats = {product.id: {"pieces": 0, "amount": 0.0, "live": 0, "last": None} for product in products}
        for line in year_lines:
            stat = stats.get(line.product_id.product_tmpl_id.id)
            if stat is None:
                continue
            stat["last"] = max(stat["last"] or line.order_id.date_order, line.order_id.date_order)
        for line in lines:
            stat = stats.get(line.product_id.product_tmpl_id.id)
            if stat is None:
                continue
            stat["pieces"] += int(line.product_uom_qty)
            stat["amount"] += self._ocd_amount(line, currency)
            if line.ocd_live_id:
                stat["live"] += int(line.product_uom_qty)
        waiting = defaultdict(int)
        if products:
            for variant, count in self.env["ocd.stock.alert"].sudo()._read_group(
                [("product_id", "in", products.product_variant_ids.ids), ("state", "=", "waiting")],
                ["product_id"], ["__count"],
            ):
                waiting[variant.product_tmpl_id.id] += count
        on_sale = products.filtered(lambda product: product.is_published and product.sale_ok and not product.ocd_vendor_retired)
        shown = products.filtered(lambda product: product in on_sale or stats[product.id]["pieces"])
        top = max([stats[product.id]["pieces"] for product in shown] or [0])
        rows = []
        for product in shown:
            stat = stats[product.id]
            contacts = contacts_by.get(product.id, 0)
            pieces = stat["pieces"]
            parts = [_("1 sold") if pieces == 1 else _("%s sold", pieces), self._ocd_money(stat["amount"], currency)]
            if stat["last"]:
                parts.append(_("last sale %s", self._ocd_when_text(vendor, stat["last"], now)))
            facts = []
            if contacts:
                facts.append(_("1 WhatsApp contact") if contacts == 1 else _("%s WhatsApp contacts", contacts))
            if stat["live"]:
                facts.append(_("%s sold during your lives", stat["live"]))
            if waiting[product.id]:
                facts.append(_("1 customer waits for it to be back") if waiting[product.id] == 1
                             else _("%s customers wait for it to be back", waiting[product.id]))
            rows.append({
                "product": product,
                "pieces": pieces,
                "amount_value": stat["amount"],
                "amount": self._ocd_money(stat["amount"], currency),
                "line": " · ".join(parts) if pieces else " · ".join([{
                    7: _("0 sold in 7 days"), 30: _("0 sold in 30 days"), 90: _("0 sold in 3 months"),
                }.get(days, _("0 sold in 30 days"))] + parts[2:]),
                "facts": " · ".join(facts),
                "last": self._ocd_when_text(vendor, stat["last"], now) if stat["last"] else False,
                "contacts": contacts,
                "bar": round(pieces * 100 / top) if top else 0,
                "interest": not pieces and contacts >= INTEREST_CONTACTS,
            })
        rows.sort(key=lambda row: (-row["pieces"], -row["amount_value"], -row["contacts"]))
        return rows

    # --- The stores --- #

    @api.model
    def _ocd_stores(self, vendor, start, now):
        """The stores of the vendor in the period: itineraries, calls, WhatsApp, pick-ups at the
        counter, parcels that left from there."""
        _ = self.env._
        places = self.env["ocd.vendor.place"].sudo().search([("vendor_id", "=", vendor.id), ("kind", "=", "store")])
        if not places:
            return []
        taps = places._ocd_taps(start, now)
        Picking = self.env["stock.picking"].sudo()
        rows = []
        for place in places:
            tap = taps[place.id]
            pickups = Picking.search_count([
                ("ocd_pickup_place_id", "=", place.id), ("ocd_collect", "=", True), ("ocd_stage", "=", "delivered"),
                ("ocd_delivered_at", ">=", start), ("ocd_delivered_at", "<=", now),
            ])
            left = Picking.search_count([
                ("ocd_pickup_place_id", "=", place.id), ("ocd_collect", "=", False),
                "|", "&", ("ocd_picked_at", ">=", start), ("ocd_picked_at", "<=", now),
                "&", "&", ("ocd_picked_at", "=", False), ("ocd_left_at", ">=", start), ("ocd_left_at", "<=", now),
            ])
            rows.append({
                "place": place,
                "taps": " · ".join([
                    _("1 itinerary") if tap["itinerary"] == 1 else _("%s itineraries", tap["itinerary"]),
                    _("1 call") if tap["call"] == 1 else _("%s calls", tap["call"]),
                    _("%s WhatsApp", tap["whatsapp"]),
                ]),
                "parcels": " · ".join([
                    _("1 pick-up at the counter") if pickups == 1 else _("%s pick-ups at the counter", pickups),
                    _("1 parcel left from here") if left == 1 else _("%s parcels left from here", left),
                ]),
            })
        return rows

    # === MY SPACE, THE SUMMARY OF THE WEEK === #

    @api.model
    def _ocd_month(self, vendor, now=None):
        """The card « My figures » of « My space »: the sales of the month so far, against the same
        days of the month before."""
        vendor = vendor.sudo()
        now = now or fields.Datetime.now()
        tz = pytz.timezone(vendor._ocd_tz_name())
        local = pytz.utc.localize(now).astimezone(tz)
        first = local.date().replace(day=1)
        start = tz.localize(datetime.combine(first, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        previous_first = (first - timedelta(days=1)).replace(day=1)
        previous_start = tz.localize(datetime.combine(previous_first, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        previous_end = previous_start + (now - start)
        currency = self._ocd_currency(vendor)
        sums = self._ocd_sums(self._ocd_lines(vendor, start, now), currency)
        before = self._ocd_sums(self._ocd_lines(vendor, previous_start, min(previous_end, start)).filtered(
            lambda line: line.order_id.date_order < start
        ), currency)
        _ = self.env._
        pieces = _("1 piece") if sums["pieces"] == 1 else _("%s pieces", sums["pieces"])
        return {
            "line": _("This month: %(amount)s · %(pieces)s", amount=self._ocd_money(sums["amount"], currency), pieces=pieces),
            "evolution": self._ocd_evolution(sums["amount"], before["amount"]),
        }

    @api.model
    def _ocd_week_summary(self, vendor, now=None):
        """What the summary of the week tells (the 7 days before), or None when nothing happened:
        {pieces, amount, evolution, visits, best}."""
        vendor = vendor.sudo()
        now = now or fields.Datetime.now()
        currency = self._ocd_currency(vendor)
        lines = self._ocd_lines(vendor, now - timedelta(days=7), now)
        before = self._ocd_lines(vendor, now - timedelta(days=14), now - timedelta(days=7)).filtered(
            lambda line: line.order_id.date_order < now - timedelta(days=7)
        )
        sums, sums_before = self._ocd_sums(lines, currency), self._ocd_sums(before, currency)
        today = tools.to_tz(now, vendor._ocd_tz_name()).date()
        visits = self.env["ocd.vendor.count"]._ocd_totals(vendor, "visit", today - timedelta(days=7), today - timedelta(days=1))
        if not sums["pieces"] and not visits:
            return None
        pieces = defaultdict(float)
        for line in lines:
            pieces[line.product_id.product_tmpl_id] += line.product_uom_qty
        best = max(pieces, key=pieces.get) if pieces else False
        evolution = self._ocd_evolution(sums["amount"], sums_before["amount"])
        return {
            "pieces": sums["pieces"],
            "amount": sums["amount"],
            "currency": currency,
            "evolution": evolution,
            "percent": evolution.get("percent"),
            "visits": visits,
            "best": best,
        }

    @api.model
    def _ocd_week_values(self, vendor, summary, lang):
        """The words of the summary of the week in `lang` (the language of a WhatsApp template):
        {amount, trend, best}."""
        env = self.with_context(lang=lang).env if lang and self.env["res.lang"]._ocd_is_active(lang) else self.env
        _ = env._
        percent = summary["percent"]
        if percent is None:
            trend = _("up") if summary["amount"] else _("stable")
        elif percent > 0:
            trend = _("up %s %%", percent)
        elif percent < 0:
            trend = _("down %s %%", abs(percent))
        else:
            trend = _("stable")
        best = summary["best"]
        return {
            "amount": format_amount(env, summary["amount"], summary["currency"]),
            "trend": trend,
            "best": best.with_env(env).name if best else _("none this week"),
        }
