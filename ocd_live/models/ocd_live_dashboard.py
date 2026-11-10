import math
from collections import Counter
from datetime import datetime, time, timedelta

from odoo import api, fields, models
from babel.numbers import get_currency_name

from odoo.tools.misc import babel_locale_parse, format_amount

from ..tools import day_text

# Order of the tags of "To do now": red first, then yellow, then grey
TONES = {"red": 10, "yellow": 20, "grey": 30}
CHART_DAYS = 14
UPCOMING_ROWS = 6


class OcdLiveDashboard(models.AbstractModel):
    """Dashboard of the team, as in the validated design (BoDashboard): figures of the day,
    bookings received per day, what to do now, money received and what comes today. The other
    modules (shop, WhatsApp) add their figures through the `_ocd_*` methods."""

    _name = "ocd.live.dashboard"
    _description = "OCD Live Dashboard"

    @api.model
    def get_dashboard_data(self):
        company = self.env.company
        now = company._ocd_to_local(fields.Datetime.now())
        todos = sorted(self._ocd_todos(), key=lambda todo: TONES.get(todo["tone"], 99))
        return {
            "today": day_text(self.env, now.date(), "EEE d MMM"),
            "updated_at": now.strftime("%H:%M"),
            "tiles": sorted(self._ocd_tiles(), key=lambda tile: tile["sequence"]),
            "chart": self._ocd_chart(),
            "todos": todos,
            "revenue": self._ocd_revenue(),
            "upcoming": self._ocd_upcoming()[:UPCOMING_ROWS],
        }

    # === HELPERS === #

    @api.model
    def _ocd_day_bounds(self, day=None):
        """Return the start and the end (naive UTC) of `day` (today by default) at the studio."""
        company = self.env.company
        tz = company._ocd_tz()
        midnight = tz.localize(datetime.combine(day or company._ocd_local_today(), time()))
        start = company._ocd_to_utc(midnight)
        return start, start + timedelta(days=1)

    @api.model
    def _ocd_action(self, xmlid, domain=None, name=None):
        """Return the action `xmlid` to open from the dashboard, limited to `domain`."""
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        if action.get("type") == "ir.actions.act_window":
            if domain is not None:
                action["domain"] = domain
                action["context"] = {}
            if name:
                action["name"] = name
        return action

    @api.model
    def _ocd_record_action(self, record):
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "res_id": record.id,
            "views": [[False, "form"]],
            "target": "current",
        }

    @api.model
    def _ocd_money(self, amount, currency=None):
        return format_amount(self.env, amount, currency or self.env.company.currency_id)

    @api.model
    def _ocd_local_time(self, value):
        return self.env.company._ocd_to_local(value).strftime("%H:%M")

    @api.model
    def _ocd_local_day(self, value):
        return day_text(self.env, self.env.company._ocd_to_local(value).date(), "EEE d MMM")

    # === FIGURES OF THE DAY === #

    @api.model
    def _ocd_tiles(self):
        """Return the figures of the top: dicts with `key`, `sequence`, `label`, `value`, `sub`,
        `tone` ("red", "yellow" or "") and `action`."""
        company = self.env.company
        start, end = self._ocd_day_bounds()
        lives_domain = [
            ("company_id", "=", company.id),
            ("state", "in", ("confirmed", "done")),
            ("start_datetime", ">=", start),
            ("start_datetime", "<", end),
        ]
        lives = self.env["ocd.live.booking"].search(lives_domain)
        studio = len(lives.filtered(lambda booking: booking.mode == "studio"))
        passes_domain = [("company_id", "=", company.id), ("state", "=", "active")]
        passes = self.env["ocd.directory.pass"].search(passes_domain)
        reminder_days = company.ocd_pass_reminder_days
        limit = company._ocd_local_today() + timedelta(days=reminder_days)
        ending = passes.filtered(lambda directory_pass: directory_pass.date_end <= limit)
        return [
            {
                "key": "lives",
                "sequence": 10,
                "label": self.env._("Lives today"),
                "value": str(len(lives)),
                "sub": self.env._(
                    "%(studio)s at the studio · %(remote)s remote", studio=studio, remote=len(lives) - studio
                ),
                "tone": "",
                "action": self._ocd_action("ocd_live.ocd_live_booking_action", lives_domain, self.env._("Lives today")),
            },
            {
                "key": "passes",
                "sequence": 20,
                "label": self.env._("Active directory passes"),
                "value": str(len(passes)),
                "sub": self.env._("%(count)s end within %(days)s days", count=len(ending), days=reminder_days),
                "tone": "",
                "action": self._ocd_action(
                    "ocd_live.ocd_directory_pass_action", passes_domain, self.env._("Active directory passes")
                ),
            },
        ]

    # === BOOKINGS PER DAY === #

    @api.model
    def _ocd_chart(self):
        """Paid bookings received each day of the last 14 days."""
        company = self.env.company
        today = company._ocd_local_today()
        first = today - timedelta(days=CHART_DAYS - 1)
        start, _end = self._ocd_day_bounds(first)
        bookings = self.env["ocd.live.booking"].search([
            ("company_id", "=", company.id),
            ("state", "in", ("confirmed", "done")),
            ("create_date", ">=", start),
        ])
        per_day = Counter(company._ocd_to_local(booking.create_date).date() for booking in bookings)
        days = [first + timedelta(days=offset) for offset in range(CHART_DAYS)]
        values = [per_day.get(day, 0) for day in days]
        step = self._ocd_nice_step(max(values) / 4)
        top = step * 4
        subtitle = self.env._("Last %(days)s days · %(count)s bookings", days=CHART_DAYS, count=sum(values))
        open_date = company.ocd_booking_open_date
        if open_date and open_date > today:
            subtitle = self.env._(
                "%(subtitle)s · lives open on %(day)s", subtitle=subtitle, day=day_text(self.env, open_date, "d MMM")
            )
        return {
            "subtitle": subtitle,
            "bars": [
                {
                    "key": day.isoformat(),
                    "label": day_text(self.env, day, "d"),
                    "full": day_text(self.env, day, "EEE d MMM"),
                    "value": value,
                    "height": round(value / top * 100, 1),
                    "last": index == CHART_DAYS - 1,
                }
                for index, (day, value) in enumerate(zip(days, values))
            ],
            "ticks": [step * index for index in range(5)],
            "action": self._ocd_action("ocd_live.ocd_live_booking_action"),
        }

    @api.model
    def _ocd_nice_step(self, value):
        """Return the round step (1, 2, 5, 10, 20, 50…) of an axis, at least `value`."""
        value = max(value, 1)
        power = 10 ** math.floor(math.log10(value))
        for factor in (1, 2, 5, 10):
            if factor * power >= value:
                return int(factor * power)
        return int(10 * power)

    # === TO DO NOW === #

    @api.model
    def _ocd_todos(self):
        """Return what the team has to do now: dicts with `key`, `tag`, `tone` ("red", "yellow"
        or "grey"), `text` and `action`."""
        todos = []
        parts = [part for part in self._ocd_check_parts() if part[0]]
        if parts:
            texts = [part[1] for part in parts]
            text = texts[0]
            if len(texts) > 1:
                text = self.env._("%(first)s and %(last)s", first=", ".join(texts[:-1]), last=texts[-1])
            todos.append({
                "key": "to_check",
                "tag": self.env._("To check"),
                "tone": "yellow",
                "text": text,
                "action": parts[0][2],
            })
        hostless = self.env["ocd.live.booking"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("needs_host", "=", True),
                ("state", "=", "confirmed"),
                ("start_datetime", ">=", fields.Datetime.now()),
            ],
            order="start_datetime",
            limit=2,
        )
        for booking in hostless:
            todos.append({
                "key": f"host_{booking.id}",
                "tag": self.env._("Host"),
                "tone": "grey",
                "text": self.env._(
                    "Live of %(vendor)s, %(day)s: no host",
                    vendor=booking.partner_id.name,
                    day=self._ocd_local_day(booking.start_datetime),
                ),
                "action": self._ocd_record_action(booking),
            })
        return todos

    @api.model
    def _ocd_check_parts(self):
        """Return what waits for a check of the team, as (count, text, action) tuples."""
        listing_domain = [("company_id", "=", self.env.company.id), ("state", "=", "to_check")]
        links = self.env["ocd.directory.listing"].search_count(listing_domain)
        vendor_domain = [("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "to_check")]
        vendors = self.env["res.partner"].search_count(vendor_domain)
        return [
            (
                links,
                self.env._("%s lives", links) if links > 1 else self.env._("1 live"),
                self._ocd_action("ocd_live.ocd_directory_listing_action", listing_domain, self.env._("Lives to check")),
            ),
            (
                vendors,
                self.env._("%s new vendors", vendors) if vendors > 1 else self.env._("1 new vendor"),
                self._ocd_action("ocd_live.res_partner_action_ocd_vendor", vendor_domain, self.env._("New vendors")),
            ),
        ]

    # === MONEY RECEIVED === #

    @api.model
    def _ocd_revenue(self):
        """Money received since the first payment, by kind, in the currency of the company."""
        company = self.env.company
        currency = company.currency_id
        # sudo: totals only, the team does not need the rights on the sales
        lines = self.env["sale.order.line"].sudo().search([
            ("company_id", "=", company.id),
            ("order_id.state", "=", "sale"),
            ("product_id.ocd_product_kind", "in", ("live_package", "hour_price", "directory_pass")),
        ])
        first_date = min(lines.order_id.mapped("date_order"), default=False)
        rows = [
            {
                "key": "packages",
                "label": self.env._("Live packages"),
                "amount": self._ocd_convert(
                    lines.filtered(lambda line: line.product_id.ocd_product_kind in ("live_package", "hour_price"))
                ),
            },
            {
                "key": "passes",
                "label": self.env._("Directory passes"),
                "amount": self._ocd_convert(
                    lines.filtered(lambda line: line.product_id.ocd_product_kind == "directory_pass")
                ),
            },
        ]
        rows += self._ocd_revenue_rows()
        top = max([row["amount"] for row in rows] + [1])
        for row in rows:
            row["value"] = self._ocd_money(row["amount"], currency)
            row["width"] = round(row["amount"] / top * 100, 1)
        period = day_text(self.env, company._ocd_local_today(), "d MMM")
        if first_date:
            start = day_text(self.env, company._ocd_to_local(first_date).date(), "d MMM")
            period = self.env._("%(start)s – %(end)s", start=start, end=period)
        return {
            "subtitle": self.env._("%(period)s · in %(currency)s", period=period, currency=self._ocd_currency_name(currency)),
            "rows": rows,
        }

    @api.model
    def _ocd_currency_name(self, currency):
        """Return the name of the currency in the language of the user, e.g. "francs CFA (BCEAO)"."""
        try:
            return get_currency_name(currency.name, count=2, locale=babel_locale_parse(self.env.lang or "en_US"))
        except (ValueError, LookupError):
            return currency.name

    @api.model
    def _ocd_revenue_rows(self):
        """Hook: other rows of the money received, as dicts with `key`, `label` and `amount`
        (in the currency of the company)."""
        return []

    @api.model
    def _ocd_convert(self, lines):
        """Return the total of the sale order lines in the currency of the company."""
        company = self.env.company
        total = 0.0
        for line in lines:
            total += line.currency_id._convert(
                line.price_total, company.currency_id, company, line.order_id.date_order or fields.Date.today()
            )
        return company.currency_id.round(total)

    # === TODAY, NEXT === #

    @api.model
    def _ocd_upcoming(self):
        """Return what comes today at the studio and in the directory, from now: dicts with
        `time`, `name`, `detail` and `action`, in the order of the day."""
        company = self.env.company
        now = fields.Datetime.now()
        rows = []
        Booking = self.env["ocd.live.booking"]
        _start, end = self._ocd_day_bounds()
        bookings = Booking.search(
            [
                ("company_id", "=", company.id),
                ("state", "in", ("draft", "confirmed", "done")),
                ("end_datetime", ">", now),
                ("start_datetime", "<", end),
            ],
            order="start_datetime",
        )
        needs = dict(Booking._fields["studio_need"]._description_selection(self.env))
        planning = self._ocd_action("ocd_live.ocd_live_booking_action")
        for booking in bookings:
            if booking.state == "draft":
                name = self.env._("Held")
                detail = self.env._("payment in progress")
                if booking.hold_until:
                    detail = self.env._(
                        "payment in progress, released at %s if not paid", self._ocd_local_time(booking.hold_until)
                    )
            elif booking.mode == "studio":
                name = booking.partner_id.name
                detail = self.env._("studio")
                if booking.studio_need and booking.studio_need != "none":
                    detail = self.env._("studio, %s", needs[booking.studio_need].lower())
            else:
                name = booking.partner_id.name
                host = booking.animatrice_id.name or self.env._("no host")
                country = booking.vendor_country_id.name
                detail = (
                    self.env._("remote, %(country)s, %(host)s", country=country, host=host)
                    if country
                    else self.env._("remote, %s", host)
                )
            rows.append({
                "sort": booking.start_datetime,
                "time": self._ocd_local_time(booking.start_datetime),
                "name": name,
                "detail": detail,
                "action": self._ocd_record_action(booking),
            })
        # The next free slot of today, when somebody waits for one
        today = company._ocd_local_today()
        waiting = self.env["ocd.live.waitlist"].search_count(
            [("company_id", "=", company.id), ("day", "=", today), ("state", "=", "waiting")]
        )
        if waiting:
            taken = set(bookings.mapped("start_datetime"))
            free = next((start for start in company._ocd_slot_starts(today) if start > now and start not in taken), None)
            if free:
                rows.append({
                    "sort": free,
                    "time": self._ocd_local_time(free),
                    "name": self.env._("Free"),
                    "detail": self.env._("%s people on the waiting list", waiting)
                    if waiting > 1
                    else self.env._("1 person on the waiting list"),
                    "action": planning,
                })
        # The checking window of the directory, when it is still to come today
        found = self.env["ocd.directory.window"]._ocd_find(company=company)
        if found and found[1] < end:
            window, window_start, window_end = found
            passes = self.env["ocd.directory.pass"].search_count(
                [("company_id", "=", company.id), ("state", "=", "active")]
            )
            rows.append({
                "sort": window_start,
                "time": f"{self._ocd_local_time(window_start)} – {self._ocd_local_time(window_end)}",
                "name": self.env._("Directory"),
                "detail": self.env._("%(window)s window, %(count)s active passes", window=window.name.lower(), count=passes),
                "action": self._ocd_action("ocd_live.ocd_directory_listing_action"),
            })
        rows.sort(key=lambda row: row["sort"])
        for row in rows:
            del row["sort"]
        return rows
