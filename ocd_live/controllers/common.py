import re
from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import format_date

from .. import tools

MODES = ("studio", "remote")
NAME_MAX = 80
SESSION_VENDOR = "ocd_vendor_id"
# Vendor whose space a person of the team opened from the back office (« See the space »)
SESSION_TEAM_VIEW = "ocd_team_view_vendor_id"


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
    return day_text(day, capital=True)


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


def account_vendor():
    """Vendor of the Odoo account logged in on this browser: a vendor given an access with a
    password, or the account of a person of the vendor's company. Empty for the visitors, the
    team and the customers of the shop."""
    Partner = request.env["res.partner"].sudo()
    user = request.env.user
    if user._is_public():
        return Partner
    partner = user.partner_id.sudo()
    vendor = partner if partner.ocd_is_vendor else partner.commercial_partner_id
    return vendor if vendor.ocd_is_vendor else Partner


def team_view_vendor():
    """Vendor whose space a person of the team opened from the back office (« See the space »),
    as long as this person is logged in and in the team of OCD Live."""
    Partner = request.env["res.partner"].sudo()
    vendor_id = request.session.get(SESSION_TEAM_VIEW)
    if not vendor_id:
        return Partner
    vendor = Partner.browse(vendor_id).exists()
    if vendor.ocd_is_vendor and request.env.user.has_group("ocd_live.group_ocd_live_user"):
        return vendor
    request.session.pop(SESSION_TEAM_VIEW, None)
    return Partner


def current_vendor_and_source(token=None):
    """Return the vendor of the visitor and how it was found:

    - "link": the personal link of the vendor (link mode), which opens the space on this browser;
    - "team": a person of the team who opened the space of the vendor from the back office;
    - "browser": the vendor opened on this browser with its personal link or a WhatsApp code;
    - "account": the vendor of the Odoo account logged in, whatever the way the vendors log in
      (an account checked by a password needs no link and no code).
    """
    Partner = request.env["res.partner"].sudo()
    login = company().ocd_vendor_login
    if token and token != "moi":
        vendor = Partner._ocd_find_by_space_token(token) if login == "link" else Partner
        if vendor:
            # The personal link opens the space on this browser for the next pages
            request.session[SESSION_VENDOR] = vendor.id
            request.session.pop(SESSION_TEAM_VIEW, None)
        return vendor, "link" if vendor else False
    vendor = team_view_vendor()
    if vendor:
        return vendor, "team"
    if login in ("link", "whatsapp_code"):
        vendor_id = request.session.get(SESSION_VENDOR)
        vendor = Partner.browse(vendor_id).exists() if vendor_id else Partner
        if vendor.ocd_is_vendor:
            return vendor, "browser"
    vendor = account_vendor()
    return vendor, "account" if vendor else False


def current_vendor(token=None):
    """Return the vendor of the visitor (see current_vendor_and_source)."""
    return current_vendor_and_source(token)[0]


def space_prefix(vendor, token=None):
    """Return the base url of the space of `vendor`."""
    return "/ocd/espace/moi"


def voice_languages():
    return request.env["ocd.voice.language"].sudo().search([])


def page_values(voice_key, **values):
    """Values shared by all the pages: the voice of the page (key, languages and the sentence
    shown while it speaks) and the setting of the vendor login."""
    prompt = request.env["ocd.voice.prompt"].sudo()
    if voice_key:
        prompt = prompt.search([("key", "=", voice_key)], limit=1)
    return {
        "voice_key": voice_key if prompt else False,
        "voice_languages": voice_languages(),
        "voice_caption": prompt.with_context(lang=request.env.lang).text if prompt else "",
        "ocd_company": company(),
        "ocd_team_view": team_view_vendor(),
        **values,
    }


def now():
    return fields.Datetime.now()

# Countries of the directory: dialing code and number of digits of a mobile number
COUNTRY_PHONES = {
    "TG": ("+228", 8),
    "CM": ("+237", 9),
    "BJ": ("+229", 10),
    "CI": ("+225", 10),
    "SN": ("+221", 9),
}


def directory_countries():
    countries = request.env["res.country"].sudo().search([("code", "in", list(COUNTRY_PHONES))])
    order = list(COUNTRY_PHONES)
    return countries.sorted(lambda c: order.index(c.code))


def dial_rows(selected=None):
    """Return the countries of the phone fields: flag, dialing code and size of the number."""
    rows = []
    for country in directory_countries():
        dial, size = COUNTRY_PHONES[country.code]
        rows.append({
            "country": country,
            "flag": country.code.lower(),
            "dial": dial,
            "size": size,
            "selected": selected == country,
        })
    if rows and not any(row["selected"] for row in rows):
        rows[0]["selected"] = True
    return rows


def default_country():
    """Return the country to propose first: the one of the visitor, else the one of the studio."""
    countries = directory_countries()
    geoip_code = request.geoip.country_code
    return (
        countries.filtered(lambda c: c.code == geoip_code)
        or (company().country_id & countries)
        or countries.filtered(lambda c: c.code == "TG")
    )[:1]


def normalize_phone(country, phone):
    """Return the number with its dialing code, or False when it has not the right length."""
    digits = re.sub(r"\D", "", phone or "")
    dial, size = COUNTRY_PHONES.get(country.code, ("", 8)) if country else ("", 8)
    dial_digits = dial.lstrip("+")
    if dial_digits and digits.startswith(dial_digits) and len(digits) == len(dial_digits) + size:
        digits = digits[len(dial_digits):]
    if len(digits) != size:
        return False
    return f"{dial} {digits}"


def local_digits(country, phone):
    """Return the number without its dialing code, as the vendor types it."""
    digits = re.sub(r"\D", "", phone or "")
    dial = COUNTRY_PHONES.get(country.code, ("", 8))[0].lstrip("+") if country else ""
    if dial and digits.startswith(dial):
        digits = digits[len(dial):]
    return digits


def steps(flow, page):
    """Return the number of the step of `page` in the booking flow (5 steps)."""
    order = ["day", "hour", "package", "infos", "pay"]
    if flow == "package_first":
        order = ["package", "day", "hour", "infos", "pay"]
    return order.index(page) + 1


def day_text(day, pattern="EEEE d MMMM", capital=False):
    """Return `day` written for the vendor, e.g. "Mardi 1er décembre" or "mar. 1er déc."."""
    return tools.day_text(request.env, day, pattern, capital)


def short_day(day, capital=False):
    return day_text(day, "EEE d MMM", capital=capital)


def money(amount, currency):
    """Return the amount in `currency`, written by Odoo for the language of the visitor."""
    from odoo.tools.misc import format_amount

    return format_amount(request.env, amount, currency)


def pricelist(vendor=None, country=None):
    """Return the pricelist Odoo applies to the vendor, or to a contact of `country` (the one
    of the visitor by default): its currency is the currency of the quotation. Empty when the
    pricelists are not used: the prices are then the sales prices, in the company currency."""
    Pricelist = request.env["product.pricelist"].sudo().with_company(company())
    if vendor:
        return vendor.sudo().with_company(company()).property_product_pricelist or Pricelist
    if not request.env["res.groups"].sudo()._is_feature_enabled("product.group_product_pricelist"):
        return Pricelist
    country = country or default_country()
    if not country:
        return Pricelist
    return Pricelist._get_country_pricelist_multi([country.id]).get(country.id) or Pricelist


def package_price(product, prices):
    """Return what is paid for one `product` with the pricelist `prices`, taxes included as on
    the quotation, and the currency."""
    if prices:
        amount, currency = prices._get_product_price(product, 1.0), prices.currency_id
    else:
        amount, currency = product.list_price, product.currency_id
    taxes = product.sudo().taxes_id._filter_taxes_by_company(company())
    if taxes:
        amount = taxes.compute_all(amount, currency, 1.0, product=product)["total_included"]
    return amount, currency


def studio_city():
    return company().ocd_studio_city or ""


def live_counts():
    """Return the lives of the moment of the directory, and their number per country."""
    listings = request.env["ocd.directory.listing"].sudo().search(
        [("state", "=", "published"), ("window_end", ">", now())],
        order="checked_at desc, id desc",
    )
    counts = {}
    for listing in listings:
        counts[listing.country_id] = counts.get(listing.country_id, 0) + 1
    return listings, counts


def country_chips(counts):
    """Return the countries of the directory, the ones with the most lives first."""
    rows = [
        {"country": country, "flag": country.code.lower(), "count": counts.get(country, 0)}
        for country in directory_countries()
    ]
    rows.sort(key=lambda row: -row["count"])
    return rows


class FormErrors(UserError):
    """The errors of a form, each with the field it is about."""

    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors


def phone_error(country):
    size = COUNTRY_PHONES.get(country.code, ("", 8))[1] if country else 8
    return request.env._("Your number has %s digits.", size)


def find_or_create_vendor(post, need_category=True):
    """Return the vendor of a public form (name, WhatsApp number and its country, category,
    city, opt-in). A known number with the same name is the same vendor; otherwise a new
    vendor is created, checked later by the team. Every error is raised at once, with the
    field it is about."""
    env = request.env
    name = clean_text(post.get("name"))
    country = env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists()
    phone = normalize_phone(country, post.get("phone"))
    category = env["ocd.live.category"].sudo().browse(int(post.get("category_id") or 0)).exists()
    errors = {}
    if len(name) < 2:
        errors["name"] = env._("Write your name.")
    if not phone:
        errors["phone"] = phone_error(country)
    if need_category and not category:
        errors["category"] = env._("Choose what you sell.")
    if errors:
        raise FormErrors(env._("Check the form."), errors)
    Partner = env["res.partner"].sudo()
    optin = bool(post.get("optin"))
    vendor = Partner._ocd_find_vendor_by_phone(phone)
    if vendor and vendor.name.casefold() == name.casefold():
        if optin and not vendor._ocd_whatsapp_consent():
            vendor.ocd_whatsapp_optin = True
        return vendor
    vendor = Partner.create({
        "name": name,
        "ocd_business": category.name if category else False,
        "phone": phone,
        "city": clean_text(post.get("city")),
        "country_id": country.id,
        "ocd_category_id": category.id,
        "ocd_is_vendor": True,
        "ocd_whatsapp_optin": optin,
        "is_company": True,
    })
    if company().ocd_vendor_login in ("link", "whatsapp_code"):
        # A new vendor: this browser opens its space without asking for the code
        request.session[SESSION_VENDOR] = vendor.id
    return vendor


def windows_info(moment=None):
    """Return the checking windows of the directory: whether one is open now, its end, the
    start of the next one, and all the windows of a day."""
    current = company()
    Window = request.env["ocd.directory.window"].sudo()
    now_value = moment or now()
    found = Window._ocd_find(moment=now_value, company=current)
    is_open = bool(found and found[1] <= now_value)
    windows = Window.search([("company_id", "in", (current.id, False))])
    return {
        "open": is_open,
        "end": current._ocd_to_local(found[2]).strftime("%H:%M") if found else False,
        "next": current._ocd_to_local(found[1]).strftime("%H:%M") if found else False,
        "next_start": found[1] if found else False,
        "rows": [
            {
                "name": window.name,
                "hours": "%s – %s" % (_hour_text(window.start_hour), _hour_text(window.end_hour)),
            }
            for window in windows
        ],
    }


def _hour_text(value):
    return tools.hour_text(value)


def initials(name):
    return "".join(word[:1] for word in (name or "").split()[:2]).upper()
