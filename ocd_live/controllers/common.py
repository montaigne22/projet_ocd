import logging
import re
from datetime import date, datetime, time, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq, format_date
from odoo.tools.misc import hmac

from .. import countries, tools

_logger = logging.getLogger(__name__)

MODES = ("studio", "remote")
NAME_MAX = 80
SESSION_VENDOR = "ocd_vendor_id"
# Personal token of the vendor when the browser opened the space: a new personal link (team)
# ends the browsers opened with the old one
SESSION_VENDOR_TOKEN = "ocd_vendor_token"
# Vendor whose space a person of the team opened from the back office (« See the space »)
SESSION_TEAM_VIEW = "ocd_team_view_vendor_id"
# Cookie of the browser that keeps the vendor opened when the session of Odoo ends (7 days
# without a change) or is replaced: the phone remembers the vendor until « Change number »
# or a new personal link, as promised on the pages
VENDOR_COOKIE = "ocd_vendor"
BROWSER_COOKIE_DAYS = 180


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


def browser_signature(partner, kind):
    """Signature of the cookie that keeps `partner` opened on a browser: made with the secret of
    its personal link, so that a new personal link ends the browsers already opened."""
    token = partner.sudo()._ocd_get_space_token()
    return hmac(request.env(su=True), f"ocd_live-{kind}-browser", f"{partner.id}:{token}")


def remember_browser(cookie, partner, kind):
    """Keep `partner` opened on this browser with a cookie of its own, out of reach of the
    scripts of the page (HttpOnly), sent only by the pages of the site (SameSite)."""
    request.future_response.set_cookie(
        cookie,
        f"{partner.id}.{browser_signature(partner, kind)}",
        max_age=BROWSER_COOKIE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="Lax",
        secure=request.httprequest.scheme == "https",
    )


def forget_browser(cookie):
    request.future_response.set_cookie(cookie, "", max_age=0, expires=0, httponly=True, samesite="Lax")


def browser_partner(cookie, kind):
    """Contact kept on this browser by `cookie`, as long as its signature is the one of its
    current personal link (empty otherwise)."""
    Partner = request.env["res.partner"].sudo()
    partner_id, _sep, signature = (request.httprequest.cookies.get(cookie) or "").partition(".")
    if not partner_id.isdigit() or not signature:
        return Partner
    partner = Partner.browse(int(partner_id)).exists()
    if partner.ocd_space_token and consteq(signature, browser_signature(partner, kind)):
        return partner
    return Partner


def remember_vendor(vendor):
    """This browser opens the space of `vendor` from now on (personal link, code checked, new
    vendor of a booking), until « Change number » or a new personal link: in the session of Odoo,
    and in a cookie of the browser that outlives it."""
    request.session[SESSION_VENDOR] = vendor.id
    request.session[SESSION_VENDOR_TOKEN] = vendor.sudo()._ocd_get_space_token()
    remember_browser(VENDOR_COOKIE, vendor, "vendor")


def forget_vendor():
    request.session.pop(SESSION_VENDOR, None)
    request.session.pop(SESSION_VENDOR_TOKEN, None)
    forget_browser(VENDOR_COOKIE)


def vendor_header_link(source):
    """Button of the header of the pages of the vendor: an Odoo account logs out of Odoo (the
    space would open again by itself otherwise), a browser forgets the vendor and asks for a
    number, the view of the team has its own bar. Both are sent by POST: a link that the browser
    or a proxy loads in advance (prefetch) must never log out."""
    if source == "team":
        return False
    if source == "account":
        return {
            "href": "/web/session/logout", "post": True, "redirect": "/ocd/connexion",
            "label": request.env._("Log out"),
        }
    return {"href": "/ocd/deconnexion", "post": True, "label": request.env._("Change number")}


def local_path(path, default):
    """`path` when it is a page of this site (/…), else `default`: never another site."""
    path = path or ""
    if path.startswith("/") and not path.startswith(("//", "/\\")):
        return path
    return default


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
            remember_vendor(vendor)
            request.session.pop(SESSION_TEAM_VIEW, None)
        return vendor, "link" if vendor else False
    vendor = team_view_vendor()
    if vendor:
        return vendor, "team"
    if login in ("link", "whatsapp_code"):
        vendor_id = request.session.get(SESSION_VENDOR)
        vendor = Partner.browse(vendor_id).exists() if vendor_id else Partner
        token = request.session.get(SESSION_VENDOR_TOKEN) or ""
        if vendor.ocd_is_vendor and vendor.ocd_space_token and consteq(vendor.ocd_space_token, token):
            return vendor, "browser"
        if vendor_id:
            # A new personal link was made (or the vendor is gone): this browser asks again
            forget_vendor()
        else:
            vendor = browser_partner(VENDOR_COOKIE, "vendor")
            if vendor.ocd_is_vendor:
                # The session of Odoo lost the vendor (ended, or replaced by a new one): the
                # cookie of this browser opens the space again
                _logger.info("OCD Live: vendor %s opened again by the cookie of the browser", vendor.id)
                remember_vendor(vendor)
                return vendor, "browser"
    vendor = account_vendor()
    return vendor, "account" if vendor else False


def current_vendor(token=None):
    """Return the vendor of the visitor (see current_vendor_and_source)."""
    return current_vendor_and_source(token)[0]


def studio_tz():
    return company().ocd_studio_tz or "Africa/Lome"


def viewer_tz(partner=None):
    """Time zone of the person who looks at the page, in which the page gives its hours: the
    one of their phone (cookie set by the website), else the one known for the vendor (or the
    courier given as `partner`), else the studio's. The phone of a vendor or of a courier is
    remembered on their contact, for their messages. A person of the team who opened the space
    of a vendor sees the hours of the vendor."""
    if partner is None and getattr(request, "_ocd_viewer_tz", None):
        return request._ocd_viewer_tz
    person, source = (partner, "partner") if partner is not None else current_vendor_and_source()
    if source == "team":
        tz = person._ocd_tz_name()
    else:
        tz = tools.valid_tz(request.httprequest.cookies.get("tz"))
        if tz and person:
            person._ocd_remember_tz(tz)
        tz = tz or (person._ocd_tz_name() if person else studio_tz())
    if partner is None:
        request._ocd_viewer_tz = tz
    return tz


def to_viewer(value, partner=None):
    """A naive UTC datetime in the time zone of the person who looks at the page (aware)."""
    return tools.to_tz(value, viewer_tz(partner))


def viewer_zone(partner=None):
    """Name of the time zone of the page: "Heure : Cameroun"."""
    return tools.zone_text(request.env, viewer_tz(partner))


# Checks of the modules for the visitors who change page without reloading it (see
# fast_navigation): ocd_live_shop adds the couriers
FAST_NAVIGATION_CHECKS = []


def fast_navigation():
    """The vendors and the couriers known on this browser go from page to page without
    reloading them (navigation.js): their space, their parcels and the menu work like an app.
    The other visitors keep the normal pages."""
    return bool(current_vendor()) or any(check() for check in FAST_NAVIGATION_CHECKS)


def space_prefix(vendor, token=None):
    """Return the base url of the space of `vendor`."""
    return "/ocd/espace/moi"


def voice_languages():
    return request.env["ocd.voice.language"].sudo().search([])


def page_languages(url=None):
    """Languages of the pages of the site (French, English…), each with the address of this page
    (or of `url`) in that language: the language button of the pages of OCD Live switches the
    page with them. Empty when the site has only one language."""
    website = request.env.website
    if not website or len(website.language_ids) < 2:
        return []
    current = request.lang.code if request.lang else website.default_lang_id.code
    IrHttp = request.env["ir.http"]
    rows = []
    for lang in website.language_ids.sorted(lambda lang: (lang != website.default_lang_id, lang.name)):
        rows.append({
            "code": lang.code,
            "short": (lang.iso_code or lang.code).split("_")[0].lower(),
            "name": lang.name.split(" / ")[-1],
            # Always with the code of the language (/fr/…, /en/…): Odoo then remembers the choice,
            # even for the language of the site (it shows the page without the code after)
            "url": IrHttp._url_localized(url=url, lang_code=lang.code, force_default_lang=True),
            "current": lang.code == current,
        })
    return rows


def page_values(voice_key, **values):
    """Values shared by all the pages: the voice of the page (key, languages and the sentence
    shown while it speaks) and the setting of the vendor login."""
    viewer_tz()  # the phone of the vendor gives its time zone (kept for the messages)
    prompt = request.env["ocd.voice.prompt"].sudo()
    if voice_key:
        prompt = prompt.search([("key", "=", voice_key)], limit=1)
    return {
        "voice_key": voice_key if prompt else False,
        "voice_languages": voice_languages(),
        "voice_caption": prompt.with_context(lang=request.env.lang).text if prompt else "",
        "ocd_company": company(),
        "ocd_team_view": team_view_vendor(),
        "ocd_fast_nav": fast_navigation(),
        "page_languages": page_languages(),
        **values,
    }


def now():
    return fields.Datetime.now()

def directory_countries(first=None):
    """The countries offered by OCD Live, in the order of the lists (see
    res.country._ocd_ordered): `first` (the one of the person), then the others."""
    Country = request.env["res.country"].sudo()
    return Country.browse([country.id for country, _group in Country._ocd_ordered(first)])


def group_label(group):
    env = request.env
    return {
        "first": env._("Suggested"),
        "africa": env._("Africa"),
        "europe": env._("Europe"),
        "americas": env._("Americas"),
        "asia": env._("Asia"),
        "oceania": env._("Oceania"),
    }.get(group, "")


def dial_rows(selected=None):
    """The countries of the phone fields: flag, dialing code, example of number and group of
    the list (the suggested countries, then each continent)."""
    rows = []
    for country, group in request.env["res.country"].sudo()._ocd_ordered(selected or None):
        rows.append({
            "country": country,
            "flag": (country.code or "").lower(),
            "dial": countries.dial_code(country),
            "size": countries.size(country),
            "example": countries.example(country),
            "group": group,
            "group_label": group_label(group),
            "selected": selected == country,
        })
    if rows and not any(row["selected"] for row in rows):
        rows[0]["selected"] = True
    return rows


def country_of_tz(tz_name):
    """The country of a time zone given by the phone (Africa/Douala: Cameroon), or None."""
    return tools.country_of_tz(tz_name)


def default_country():
    """Return the country to propose first: the one of the visitor (address of the
    connection, else time zone of the phone), else the one of the studio when OCD Live started
    there, else Togo."""
    offered = request.env["res.country"].sudo()._ocd_offered()
    studio = company().country_id.code
    codes = [
        request.geoip.country_code,
        country_of_tz(request.httprequest.cookies.get("tz")),
        studio if studio in countries.MAIN_COUNTRIES else None,
        countries.MAIN_COUNTRIES[0],
    ]
    for code in codes:
        found = offered.filtered(lambda c, code=code: code and c.code == code)
        if found:
            return found[:1]
    return offered[:1]


def normalize_phone(country, phone):
    """Return the number with its dialing code ("+228 90000007"), or False when it is not a
    number of `country`."""
    return countries.normalize(country, phone)


def local_digits(country, phone):
    """Return the number without its dialing code, as the vendor types it."""
    return countries.local_digits(country, phone)


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
    example = countries.example(country)
    if example:
        return request.env._("This number is not a number of %(country)s. Example: %(example)s.",
                             country=country.name, example=example)
    return request.env._("Your number has %s digits.", countries.size(country))


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
        remember_vendor(vendor)
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
        "end": to_viewer(found[2]).strftime("%H:%M") if found else False,
        "next": to_viewer(found[1]).strftime("%H:%M") if found else False,
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
    """An hour of the studio given as a float (18.5), in the time zone of the visitor."""
    current = company()
    today = current._ocd_local_today()
    minutes = round(value * 60)
    moment = current._ocd_to_utc(current._ocd_tz().localize(datetime.combine(today, time()) + timedelta(minutes=minutes)))
    return to_viewer(moment).strftime("%H:%M")


def initials(name):
    return "".join(word[:1] for word in (name or "").split()[:2]).upper()
