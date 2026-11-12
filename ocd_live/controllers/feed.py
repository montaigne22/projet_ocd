"""The feed of the lives (/lives): one card per live, full screen, the country of the person first,
then the other countries, the most active first. When no live is checked now, the next lives
booked at the studio and the replays fill it: the feed is never empty.

The whole order is computed for each page (a few hundred items at most) and cut into pages:
the first one comes with the page (it works without JavaScript), the next ones are loaded while
the person scrolls (feed.js)."""

from collections import defaultdict
from datetime import timedelta

from odoo import fields
from odoo.http import request

from .. import tools
from . import common

PAGE_SIZE = 8
MAX_ITEMS = 240
NEXT_DAYS = 14
REPLAY_DAYS = 30
KIND_ORDER = {"live": 0, "studio": 1, "next": 2, "replay": 3}


def first_country(code=None):
    """The country shown first: the one asked (?pays=), else the one of the vendor, else the
    one of the visitor (address of the connection, time zone of the phone)."""
    Country = request.env["res.country"].sudo()
    if code and len(code) == 2:
        country = Country.search([("code", "=", code.upper())], limit=1)
        if country:
            return country
    vendor = common.current_vendor()
    return (vendor.country_id if vendor else Country) or common.default_country()


def _raw_items(now):
    """The items of the feed, without their order: (key, kind, record, country, moment)."""
    env = request.env
    Booking = env["ocd.live.booking"].sudo()
    listings, _counts = common.live_counts()
    items = []
    live_vendors = set()
    for listing in listings:
        items.append(("l%s" % listing.id, "live", listing, listing.country_id or listing.partner_id.country_id,
                      listing.checked_at or listing.window_start or now))
        live_vendors.add(listing.partner_id.id)
    vendor_ok = [("partner_id.ocd_is_vendor", "=", True), ("partner_id.ocd_vendor_state", "=", "approved")]
    studio = Booking.search([
        ("state", "=", "confirmed"), ("start_datetime", "<=", now), ("end_datetime", ">", now), *vendor_ok,
    ], order="start_datetime")
    for booking in studio.filtered(lambda b: b.partner_id.id not in live_vendors):
        items.append(("s%s" % booking.id, "studio", booking, booking.partner_id.country_id, booking.start_datetime))
    # One card per vendor for what comes and for what can be watched again: its next live, its
    # last replay (the others are in its boutique), so that a busy country does not push the
    # lives of the other countries far down the feed
    coming = Booking.search([
        ("state", "=", "confirmed"), ("start_datetime", ">", now),
        ("start_datetime", "<", now + timedelta(days=NEXT_DAYS)), *vendor_ok,
    ], order="start_datetime")
    for booking in _first_per_vendor(coming):
        items.append(("n%s" % booking.id, "next", booking, booking.partner_id.country_id, booking.start_datetime))
    replays = Booking.search([
        ("replay_published", "=", True), ("replay_url", "!=", False), ("end_datetime", "<=", now),
        ("end_datetime", ">", now - timedelta(days=REPLAY_DAYS)), *vendor_ok,
    ], order="end_datetime desc")
    for booking in _first_per_vendor(replays):
        items.append(("r%s" % booking.id, "replay", booking, booking.partner_id.country_id, booking.end_datetime))
    return items


def _first_per_vendor(bookings):
    """The first live of each vendor among `bookings` (in their order), at most MAX_ITEMS."""
    seen = set()
    first = []
    for booking in bookings:
        if booking.partner_id.id not in seen:
            seen.add(booking.partner_id.id)
            first.append(booking)
            if len(first) >= MAX_ITEMS:
                break
    return first


def _sort_moment(kind, moment):
    """Lives now: the last checked first; next lives: the soonest first; replays: the last."""
    stamp = moment.timestamp() if moment else 0
    return stamp if kind == "next" else -stamp


def ordered(first, now=None):
    """The items of the feed in their order, with a card per country between the countries:
    a list of dicts {key, kind, record, country}. The country of the person comes first (with a
    card that says when it has no live), then the other countries, the most lives first."""
    now = now or common.now()
    by_country = defaultdict(list)
    for key, kind, record, country, moment in _raw_items(now):
        by_country[country].append({"key": key, "kind": kind, "record": record, "country": country, "moment": moment})
    for rows in by_country.values():
        rows.sort(key=lambda item: (KIND_ORDER[item["kind"]], _sort_moment(item["kind"], item["moment"])))

    def activity(country):
        rows = by_country[country]
        return (-sum(1 for item in rows if item["kind"] in ("live", "studio")), -len(rows), country.name or "")

    countries = sorted((c for c in by_country if c != first), key=activity)
    feed = []
    windows = common.windows_info(now)
    if not windows["open"]:
        feed.append({"key": "closed", "kind": "closed", "country": first})
    first_rows = by_country.get(first, [])
    if first and not first_rows:
        feed.append({"key": f"none-{first.code}", "kind": "none", "country": first})
    feed += first_rows
    for country in countries:
        feed.append({"key": f"c-{(country.code or 'xx').lower()}", "kind": "country", "country": country,
                     "rows": by_country[country]})
        feed += by_country[country]
    feed = feed[:MAX_ITEMS]
    feed.append({"key": "end", "kind": "end", "country": first})
    return feed


def country_bar(first, feed):
    """The countries of the bar above the feed: the one of the person, then the others in the
    order of the feed, each with its number of lives now."""
    counts = defaultdict(int)
    order = [first] if first else []
    for item in feed:
        country = item.get("country")
        if item["kind"] in ("live", "studio"):
            counts[country] += 1
        if country and item["kind"] in ("live", "studio", "next", "replay") and country not in order:
            order.append(country)
    return [
        {
            "country": country,
            "flag": (country.code or "").lower(),
            "count": counts[country],
            "href": f"/lives?pays={(country.code or '').lower()}",
            "on": country == first,
        }
        for country in order if country
    ]


def _card(item, tz_name, now):
    """What a card of the feed shows."""
    env = request.env
    kind = item["kind"]
    card = dict(item)
    country = item.get("country")
    card["flag"] = (country.code or "").lower() if country else ""
    card["country_name"] = country.name if country else ""
    if kind in ("closed", "none", "end"):
        return card
    if kind == "country":
        rows = item["rows"]
        lives = sum(1 for row in rows if row["kind"] in ("live", "studio"))
        coming = sum(1 for row in rows if row["kind"] == "next")
        parts = []
        if lives:
            parts.append(env._("%s lives now", lives) if lives > 1 else env._("1 live now"))
        if coming:
            parts.append(env._("%s next lives", coming) if coming > 1 else env._("1 next live"))
        card["line"] = " · ".join(parts) or env._("Replays")
        return card
    record = item["record"]
    vendor = record.partner_id
    shop_path = vendor._ocd_shop_path()
    card.update(_vendor_values(vendor, (record.title if kind == "live" else False) or vendor.name or ""))
    if kind == "live":
        minutes = max(1, int((now - item["moment"]).total_seconds() // 60))
        platform = record.platform_id.name or ""
        card.update({
            "badge": env._("Live"),
            "when": env._("Live for %s min", minutes) if minutes < 120 else env._("Live for %s h", minutes // 60),
            "watch_url": record.url,
            "watch_label": env._("Watch on %s", platform) if platform else env._("Watch the live"),
        })
    elif kind == "studio":
        watch_url = record._ocd_watch_url()
        platform = env["ocd.live.platform"].sudo()._ocd_for_url(watch_url).name if watch_url else ""
        card.update({
            "badge": env._("Live"),
            "when": env._("Live at the OCD Live studio") if record.mode == "studio" else env._("Live from home, with OCD Live"),
            "watch_url": watch_url or card["shop_url"],
            "watch_label": env._("Watch on %s", platform) if platform else env._("Watch the live"),
            "external": bool(watch_url),
        })
    elif kind == "next":
        local = tools.to_tz(record.start_datetime, tz_name)
        card.update({
            "badge": env._("Next live"),
            "when": _day_hour(local, tools.to_tz(now, tz_name).date()),
            "zone": tools.zone_text(env, tz_name),
            "where": env._("At the OCD Live studio") if record.mode == "studio" else env._("From home, with OCD Live"),
        })
    elif kind == "replay":
        local = tools.to_tz(record.start_datetime, tz_name)
        card.update({
            "badge": env._("Replay"),
            "when": env._("Live on %s", common.day_text(local.date(), "EEE d MMM")),
            "watch_url": f"/{shop_path}/replay" if shop_path else record.replay_url,
            "watch_label": env._("Watch again"),
            "external": not shop_path,
        })
    return card


def _day_hour(local, today):
    """« Today at 10:00 », « Tomorrow at 14:30 », else « Thu 19 Nov at 10:00 »."""
    env = request.env
    hour = f"{local:%H:%M}"
    if local.date() == today:
        return env._("Today at %s", hour)
    if local.date() == today + timedelta(days=1):
        return env._("Tomorrow at %s", hour)
    return env._("%(day)s at %(hour)s", day=common.day_text(local.date(), "EEE d MMM", capital=True), hour=hour)


def _vendor_values(vendor, name):
    """What every card of a vendor shows: its name, its media, its boutique."""
    env = request.env
    shop_path = vendor._ocd_shop_path()
    values = {
        "name": name,
        "initials": common.initials(name),
        "category": " · ".join(part for part in (vendor.ocd_category_id.name, vendor.ocd_business) if part),
        "media": vendor._ocd_card_media(),
        "shop_url": f"/{shop_path}" if shop_path else False,
        "share_url": f"{request.httprequest.url_root.rstrip('/')}/{vendor._ocd_public_path()}",
        "watch_url": False,
        "watch_label": "",
        "external": True,
        "where": False,
    }
    if values["media"]["kind"] == "products":
        values["media"]["label"] = env._("The products of %s", vendor.name or name)
    return values


def preview_card(vendor):
    """The card of `vendor` as the feed shows it before its next live, for the page « My card
    in the lives » of its space (a card « next live » even when none is booked)."""
    env = request.env
    now = common.now()
    booking = env["ocd.live.booking"].sudo().search([
        ("partner_id", "=", vendor.id), ("state", "=", "confirmed"), ("start_datetime", ">", now),
    ], order="start_datetime", limit=1)
    country = vendor.country_id
    item = {"key": "preview", "kind": "next", "country": country}
    if booking:
        return _card({**item, "record": booking}, common.viewer_tz(), now)
    card = {
        **item,
        "flag": (country.code or "").lower() if country else "",
        "country_name": country.name if country else "",
        **_vendor_values(vendor, vendor.name or ""),
        "badge": env._("Next live"),
        "when": env._("Your next live"),
    }
    return card


def page(first, offset=0, limit=PAGE_SIZE, now=None):
    """A page of the feed: its cards and where the next page starts (None at the end)."""
    now = now or common.now()
    feed = ordered(first, now)
    tz_name = common.viewer_tz()
    offset = max(0, int(offset or 0))
    limit = min(max(1, int(limit or PAGE_SIZE)), 20)
    cards = [_card(item, tz_name, now) for item in feed[offset:offset + limit]]
    following = offset + limit if offset + limit < len(feed) else None
    return {"feed": feed, "cards": cards, "next": following, "total": len(feed)}


def new_lives_count(since):
    """Lives checked since `since` (a moment of the page), for the « new lives » pill."""
    since = fields.Datetime.to_datetime(since) if since else None
    if not since:
        return 0
    listings, _counts = common.live_counts()
    return len(listings.filtered(lambda listing: listing.checked_at and listing.checked_at > since))
