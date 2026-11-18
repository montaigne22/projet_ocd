"""The programme of the lives (chantier 7, design ProgrammeSoirees): the lives of the next 7 days
known in advance (booked at the studio or remote, on the accounts of OCD Live), by day and by hour
at the hour of the phone of the visitor, the lives of now first; on a computer, a TV guide with one
line per account of OCD Live. « Tell me » is « Follow » the vendor for their lives (chantier 1)."""
from datetime import datetime, time, timedelta
from urllib.parse import urlencode

import pytz

from odoo import http
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from .vendor_follow import follow_url, visitor_follows

# The days of the programme, today included
DAYS = 7
# The TV guide is cut in quarters of an hour
QUARTER = 15


def local_bounds(day, tz_name):
    """The start and the end of `day` at the hour `tz_name`, in UTC (naive)."""
    zone = pytz.timezone(tz_name)
    start = zone.localize(datetime.combine(day, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
    end = zone.localize(datetime.combine(day + timedelta(days=1), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
    return start, end


def hour_text(env, local):
    if (env.lang or "").startswith("fr"):
        return f"{local.hour} h" if not local.minute else f"{local.hour} h {local.minute:02d}"
    return f"{local:%H:%M}"


class OcdProgramme(http.Controller):

    def _url(self, **params):
        query = {key: value for key, value in params.items() if value}
        return "/lives/programme" + (f"?{urlencode(query)}" if query else "")

    def _days(self, today, chosen, tz_name):
        env = request.env
        rows = []
        evenings = self._ocd_evening_days(today, today + timedelta(days=DAYS - 1), tz_name)
        for index in range(DAYS):
            day = today + timedelta(days=index)
            rows.append({
                "day": day,
                "label": tools.day_text(env, day, "EEE", capital=True),
                "number": day.day,
                "on": day == chosen,
                "evening": evenings.get(day),
                "key": day.isoformat(),
            })
        return rows

    def _ocd_evening_days(self, first, last, tz_name):
        """{day: name of the big evening of that day} (ocd_soirees)."""
        return {}

    def _ocd_evening_band(self, day, tz_name):
        """The band of the big evening to come shown on the programme (ocd_soirees)."""
        return False

    def _bookings(self, start, end, country, category):
        domain = [
            ("state", "=", "confirmed"), ("start_datetime", "<", end), ("end_datetime", ">", start),
            ("partner_id.ocd_is_vendor", "=", True), ("partner_id.ocd_vendor_state", "=", "approved"),
        ]
        if country:
            domain.append(("partner_id.country_id", "=", country.id))
        if category:
            domain.append(("partner_id.ocd_category_id", "=", category.id))
        return request.env["ocd.live.booking"].sudo().search(domain, order="start_datetime, id")

    def _row(self, booking, tz_name, now, followed, back):
        env = request.env
        vendor = booking.partner_id
        local = tools.to_tz(booking.start_datetime, tz_name)
        local_end = tools.to_tz(booking.end_datetime, tz_name)
        account = booking.account_id
        platform = account.platform_id.name if account else ""
        where = env._("at the studio") if booking.mode == "studio" else env._("remote")
        return {
            "booking": booking,
            "vendor": vendor,
            "name": vendor.name,
            "initials": common.initials(vendor.name),
            "hour": f"{local:%H:%M}",
            "end": f"{local_end:%H:%M}",
            "local": local,
            "local_end": local_end,
            "live": booking.start_datetime <= now < booking.end_datetime,
            "line": " · ".join(part for part in (
                vendor.ocd_category_id.name, " ".join(part for part in (platform, account.name) if part), where,
            ) if part),
            "channel": account,
            "watch_url": f"/ocd/regarder/{booking.id}?d=programme" if booking._ocd_watch_url() else False,
            "boutique_url": f"/ocd/boutique/{vendor.id}",
            "followed": vendor.id in followed,
            "follow_url": follow_url(vendor, back=back, source="programme"),
            "bell_label": env._("%s: told at each live", vendor.name) if vendor.id in followed
            else env._("Tell me when %s is live", vendor.name),
        }

    def _guide(self, rows, tz_name):
        """The TV guide of the day: one line per account of OCD Live (« OCD Live Togo · TikTok »),
        the lives placed on quarters of an hour."""
        env = request.env
        if not rows:
            return False
        first = min(row["local"] for row in rows)
        last = max(row["local_end"] for row in rows)
        start_hour = max(min(first.hour, 18), 0)
        end_hour = min(max(last.hour + (1 if last.minute or last.second else 0), start_hour + 4), 24)
        columns = (end_hour - start_hour) * 60 // QUARTER
        day_start = first.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        channels = {}
        for row in rows:
            key = row["channel"].id or 0
            account = row["channel"]
            modes = {"studio": env._("studio"), "remote": env._("remote")}
            channel = channels.setdefault(key, {
                "name": account.name or "OCD Live",
                "sub": " · ".join(part for part in (
                    account.platform_id.name if account else "", modes.get(account.mode, "") if account else "",
                ) if part),
                "sequence": (account.sequence if account else 999, key),
                "blocks": [],
            })
            begin = max(int((row["local"] - day_start).total_seconds() // 60 // QUARTER), 0)
            finish = min(max(int((row["local_end"] - day_start).total_seconds() // 60 // QUARTER), begin + 1), columns)
            if begin >= columns:
                continue
            channel["blocks"].append({**row, "column": begin + 2, "span": max(finish - begin, 1)})
        hours = [{"label": hour_text(env, day_start.replace(hour=h)) if h < 24 else "", "column": (h - start_hour) * 4 + 2}
                 for h in range(start_hour, end_hour)]
        # Two lives of one account at once (moved by the team, a test): one under the other
        next_row = 2
        ordered = sorted(channels.values(), key=lambda channel: channel["sequence"])
        for channel in ordered:
            lanes = []
            for block in sorted(channel["blocks"], key=lambda block: block["column"]):
                lane = next((index for index, end in enumerate(lanes) if end <= block["column"]), len(lanes))
                if lane == len(lanes):
                    lanes.append(0)
                lanes[lane] = block["column"] + block["span"]
                block["row"] = next_row + lane
            channel["row"] = next_row
            channel["lanes"] = max(len(lanes), 1)
            next_row += channel["lanes"]
        return {
            "columns": columns,
            "hours": hours,
            "channels": ordered,
        }

    @http.route("/lives/programme", type="http", auth="public", website=True, sitemap=True, methods=["GET"],
                ocd_cache=30, ocd_cache_params=("jour", "pays", "categorie"))
    def programme(self, jour=None, pays=None, categorie=None, **kwargs):
        env = request.env
        tz_name = common.viewer_tz() or "Africa/Lome"
        now = common.now()
        today = tools.to_tz(now, tz_name).date()
        chosen = common.parse_day(jour) if jour else today
        if not chosen or not today <= chosen < today + timedelta(days=DAYS):
            chosen = today
        Country = env["res.country"].sudo()
        all_countries = pays == "tous"
        country = False
        if not all_countries:
            country = Country.search([("code", "=", (pays or "").upper())], limit=1) if pays else False
            country = country or common.default_country()
        categories = env["ocd.live.category"].sudo().search([])
        category = categories.filtered(lambda c: str(c.id) == str(categorie))[:1]
        start, end = local_bounds(chosen, tz_name)
        if chosen == today:
            start = min(start, now)
        bookings = self._bookings(start, end, country, category)
        back = self._url(jour=chosen.isoformat() if chosen != today else None, pays=pays, categorie=categorie)
        followed = {follow.vendor_id.id for follow in visitor_follows() if follow.active and follow.lives}
        rows = [self._row(booking, tz_name, now, followed, back) for booking in bookings]
        live_rows = [row for row in rows if row["live"]] if chosen == today else []
        later = [row for row in rows if not row["live"] and row["booking"].end_datetime > now]
        # The lives of now on the accounts of the vendors themselves (the directory)
        directory = []
        if chosen == today:
            listings, _counts = common.live_counts()
            if country:
                listings = listings.filtered(lambda listing: (listing.country_id or listing.partner_id.country_id) == country)
            if category:
                listings = listings.filtered(lambda listing: listing.category_id == category)
            booked = {row["vendor"].id for row in live_rows}
            directory = [{
                "name": listing.title or listing.partner_id.name,
                "initials": common.initials(listing.title or listing.partner_id.name),
                "line": " · ".join(part for part in (listing.category_id.name, listing.platform_id.name) if part),
                "url": f"/ocd/boutique/{listing.partner_id.id}",
            } for listing in listings if listing.partner_id.id not in booked]
        country_code = (country.code or "").lower() if country else ""
        country_chips = [{
            "label": country.name if country else env._("All the countries"),
            "flag": country_code,
            "href": self._url(jour=jour, pays="tous" if country else None, categorie=categorie),
            "toggle": env._("All the countries") if country else (common.default_country().name or ""),
        }]
        return request.render("ocd_live_shop.programme", common.page_values(
            False,
            nav="lives",
            back="/lives",
            header_title=env._("Programme"),
            days=[{**day, "href": self._url(jour=day["key"] if day["day"] != today else None, pays=pays,
                                            categorie=categorie)} for day in self._days(today, chosen, tz_name)],
            chosen=chosen,
            is_today=chosen == today,
            day_title=env._("Today") if chosen == today else tools.day_text(env, chosen, "EEEE d MMMM", capital=True),
            country=country,
            country_flag=country_code,
            country_chips=country_chips,
            all_href=self._url(jour=jour, pays="tous", categorie=categorie),
            mine_href=self._url(jour=jour, categorie=categorie),
            categories=[{"label": env._("All the categories"), "href": self._url(jour=jour, pays=pays), "on": not category}]
            + [{"label": c.name, "href": self._url(jour=jour, pays=pays, categorie=c.id), "on": c == category}
               for c in categories],
            live_rows=live_rows,
            directory=directory,
            later=later,
            guide=self._guide(rows, tz_name),
            evening=self._ocd_evening_band(chosen, tz_name),
            zone_line=env._("Hours of your phone (%s).", tools.zone_text(env, tz_name)),
        ))
