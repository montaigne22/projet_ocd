import re
from datetime import date, timedelta

from odoo import fields
from odoo.http import request
from odoo.tools import format_date

MODES = ("studio", "remote")
NAME_MAX = 80
SESSION_VENDOR = "ocd_vendor_id"


def parse_day(value):
    """Return the date of a `YYYY-MM-DD` string, or None."""
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def clean_text(value, size=NAME_MAX):
    return re.sub(r"\s+", " ", (value or "")).strip()[:size]


def company():
    return request.env.website.company_id or request.env.company


def first_bookable_day():
    current = company()
    today = current._ocd_local_today()
    open_date = current.ocd_booking_open_date
    return max(today, open_date) if open_date else today


def day_label(day):
    return format_date(request.env, day, date_format="EEEE d MMMM")


def calendar_weeks(slot_count, mode, weeks=6):
    """Return the weeks of the booking calendar: each day with its free starts."""
    current = company()
    first = first_bookable_day()
    start = first - timedelta(days=first.weekday())
    days = [start + timedelta(days=offset) for offset in range(weeks * 7)]
    counts = request.env["ocd.live.booking"].sudo()._ocd_get_free_counts(
        [day for day in days if day >= first], slot_count=slot_count, company=current, mode=mode
    )
    rows = []
    for week in range(weeks):
        rows.append([
            {
                "day": day,
                "iso": day.isoformat(),
                "number": day.day,
                "month": format_date(request.env, day, date_format="MMM"),
                "free": counts.get(day, 0),
                "past": day < first,
                "closed": not current._ocd_is_open_day(day),
            }
            for day in days[week * 7:(week + 1) * 7]
        ])
    return rows


def packages():
    """Return the live packages sold on the website, in their order."""
    return request.env["product.product"].sudo().search(
        [("ocd_product_kind", "=", "live_package"), ("sale_ok", "=", True), ("active", "=", True)],
        order="sequence, id",
    )


def find_start(day, label):
    """Return the start (naive UTC) of the slot of `day` whose local hour is `label`
    (HHMM), or None."""
    current = company()
    for start in current._ocd_slot_starts(day):
        if current._ocd_to_local(start).strftime("%H%M") == label:
            return start
    return None


def current_vendor(token=None):
    """Return the vendor of the visitor: from the personal link (link mode), from the code
    checked on this browser (code mode), or from the logged-in user (password mode)."""
    Partner = request.env["res.partner"].sudo()
    login = company().ocd_vendor_login
    if token and token != "moi":
        vendor = Partner._ocd_find_by_space_token(token) if login == "link" else Partner
        if vendor:
            # The personal link opens the space on this browser for the next pages
            request.session[SESSION_VENDOR] = vendor.id
        return vendor
    if login in ("link", "whatsapp_code"):
        vendor_id = request.session.get(SESSION_VENDOR)
        vendor = Partner.browse(vendor_id).exists() if vendor_id else Partner
        return vendor if vendor.ocd_is_vendor else Partner
    if login == "password" and not request.env.user._is_public():
        partner = request.env.user.partner_id.sudo()
        vendor = partner if partner.ocd_is_vendor else partner.commercial_partner_id
        return vendor if vendor.ocd_is_vendor else Partner
    return Partner


def space_prefix(vendor, token=None):
    """Return the base url of the space of `vendor`."""
    return "/ocd/espace/moi"


def voice_languages():
    return request.env["ocd.voice.language"].sudo().search([])


def page_values(voice_key, **values):
    """Values shared by all the pages: the key of the voice and the voice languages."""
    return {"voice_key": voice_key, "voice_languages": voice_languages(), **values}


def now():
    return fields.Datetime.now()
