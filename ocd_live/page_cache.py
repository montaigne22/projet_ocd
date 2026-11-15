"""Public pages kept in memory a few seconds, for the crowds of the lives.

A live on TikTok or on Facebook sends thousands of people to the same pages within minutes: the
feed of the lives, the page of a live, a boutique, a product. For a visitor who has nothing of
their own on the site yet (not logged in, no vendor or courier on this browser, no cart, no
order), these pages are the same for everyone with the same language, country and time zone:
each worker of Odoo keeps the page it built for a few seconds and gives it to the next visitors
instead of building it again (ir.http._dispatch).

A route asks for it with options of @http.route:

- ``ocd_cache``: how many seconds its pages are kept;
- ``ocd_cache_params``: the parameters of the address (of the call, for a jsonrpc route) that
  make another page (?pays=cm). An address with any other parameter is built for its visitor
  (?noted=1 after a form). The parameters added by the networks and the ads (fbclid, utm_…) never
  change the page: they are left aside;
- ``ocd_cache_hit``: the name of a method of the controller, called with the parameters of the
  request when the page comes from memory, for what must happen at each visit (count the visit of
  a live).

What belongs to one visitor is never given to another: the token of the forms (CSRF) is put
back for each visitor; a visitor with something of their own always gets a page built for them;
a page during which the visitor got something of their own (a cookie, a key of the session) is
not kept. The memory is off during the tests of the modules (a test would see the pages of the
test before), except for the tests of this memory (IN_TESTS)."""

import json
import re
import threading
import time
import zlib
from collections import OrderedDict
from urllib.parse import quote, quote_plus

from odoo.http import Response, request
from odoo.http.session import get_default_session
from odoo.modules import module as odoo_module

from . import tools

MAX_PAGES = 500  # pages kept by each worker; the oldest used go first
MAX_BYTES = 2 * 1024 * 1024  # a bigger page is not kept
HEADER = "X-OCD-Cache"  # hit: from memory, miss: built and kept, pass: built for its visitor
IN_TESTS = False

# Parameters added to the links by the networks and the ads: the page is the same without them
TRACKING_PARAMS = frozenset({
    "fbclid", "gclid", "gbraid", "wbraid", "dclid", "msclkid", "ttclid", "twclid", "igshid", "igsh",
    "li_fat_id", "mc_cid", "mc_eid", "_ga", "_gl", "si",
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id", "utm_name",
})

# What the session of a visitor holds before they have anything of their own: the keys of Odoo,
# the pricelist and the taxes Odoo found for their country (the country is in the key of the
# page) and the hour it looked at them, the pricelist they chose in the shop (SESSION_KEY_PARTS,
# in the key of the page), the lives whose boutique they visited (counted once). Any other key
# (a cart, an order, a vendor, a courier, a message of a form...) makes their pages their own.
SESSION_KEY_PARTS = ("website_sale_selected_pl_id",)
SESSION_KEYS = frozenset(get_default_session()) | frozenset(SESSION_KEY_PARTS) | {
    "website_sale_current_pl", "fiscal_position_id", "website_sale_pricelist_time", "ocd_live_visits",
    "_trace_disable",  # sessions of the tests of Odoo
}
# Cookies of a person known on this browser: the vendor (controllers/common.py), the courier
# (ocd_live_shop)
PERSONAL_COOKIES = set()

# The token of the forms of the visitor (request.csrf_token): 40 hexadecimal digits, "o", the
# second it ends; put back for each visitor
CSRF_RE = re.compile(rb"(?<![0-9a-f])[0-9a-f]{40}o[0-9]{10}(?![0-9])")
CSRF_MARK = b"__ocd_csrf_token__"

_pages = OrderedDict()
_lock = threading.Lock()


def active():
    """Whether the pages are kept now: the setting of the website (on by default)."""
    if odoo_module.current_test and not IN_TESTS:
        return False
    website = request.env.website
    return bool(website) and website.ocd_page_cache


def clear():
    """Forget the pages kept by this worker."""
    with _lock:
        _pages.clear()


def dispatch(endpoint, build):
    """The answer of `endpoint`: from memory when its route keeps its pages and the visitor has
    nothing of their own, else built by `build()`, and kept for the next visitors."""
    ttl = endpoint.routing.get("ocd_cache")
    if not ttl or not active():
        return build()
    jsonrpc = endpoint.routing.get("type") == "jsonrpc"
    params = _params(endpoint, jsonrpc)
    if params is None or not anonymous() or (not jsonrpc and request.httprequest.method not in ("GET", "HEAD")):
        request.future_response.headers[HEADER] = "pass"
        return build()
    key = _key(params, jsonrpc)
    entry = _get(key)
    if entry:
        if hook := endpoint.routing.get("ocd_cache_hit"):
            getattr(endpoint.func.__self__, hook)(**request.params)
        request.future_response.headers[HEADER] = "hit"
        return _answer(entry, jsonrpc)
    result = build()
    request.future_response.headers[HEADER] = "miss"
    entry = _entry(result, ttl, jsonrpc)
    if entry:
        _put(key, entry)
    return result


def anonymous():
    """Whether the visitor has nothing of their own on the site (see SESSION_KEYS)."""
    if not request.env.user._is_public():
        return False
    session = request.session
    if session.debug or not SESSION_KEYS.issuperset(session):
        return False
    cookies = request.httprequest.cookies
    return not any(cookies.get(name) for name in PERSONAL_COOKIES)


def _params(endpoint, jsonrpc):
    """The parameters of the request that make another page, as a part of the key; None when it
    has another parameter (the page is then built for its visitor)."""
    allowed = endpoint.routing.get("ocd_cache_params") or ()
    if jsonrpc:
        given = request.dispatcher.jsonrequest.get("params") or {}
        if not set(given) <= set(allowed):
            return None
        return tuple(sorted((name, json.dumps(value, sort_keys=True)) for name, value in given.items()))
    args = request.httprequest.args
    params = []
    for name in sorted(args):
        if name in TRACKING_PARAMS:
            continue
        if name not in allowed:
            return None
        params.append((name, tuple(args.getlist(name))))
    return tuple(params)


def _key(params, jsonrpc):
    """What makes another page: the address, the language, the country (the currency, the
    taxes, the countries first), the time zone (the hours), the pricelist chosen in the shop."""
    httprequest = request.httprequest
    session = request.session
    return (
        request.db,
        request.env.website.id,
        httprequest.url_root,
        httprequest.path,
        jsonrpc,
        params,
        request.lang.code if request.lang else "",
        request.geoip.country_code or "",
        tools.valid_tz(httprequest.cookies.get("tz")) or "",
        tuple(session.get(name) for name in SESSION_KEY_PARTS),
    )


def _get(key):
    with _lock:
        entry = _pages.get(key)
        if entry is None:
            return None
        if entry[0] <= time.monotonic():
            del _pages[key]
            return None
        _pages.move_to_end(key)
        return entry


def _put(key, entry):
    with _lock:
        _pages[key] = entry
        _pages.move_to_end(key)
        while len(_pages) > MAX_PAGES:
            _pages.popitem(last=False)


def _entry(result, ttl, jsonrpc):
    """What is kept of `result` for the next visitors (until when, the page without the token of
    the forms, compressed, its headers), or None: an error, a redirection, a too big page, or a
    page during which the visitor got something of their own."""
    if not anonymous():
        return None
    cookies = request.future_response.headers.getlist("Set-Cookie")
    if any(not cookie.startswith("frontend_lang=") for cookie in cookies):
        return None
    if jsonrpc:
        try:
            body = json.dumps(result).encode()
        except (TypeError, ValueError):
            return None
        headers = ()
    else:
        if (
            not isinstance(result, Response)
            or result.status_code != 200
            or result.direct_passthrough
            or result.headers.getlist("Set-Cookie")
        ):
            return None
        body = result.get_data()
        headers = tuple(
            (name, value) for name, value in result.headers.items() if name.lower() in ("content-type", "content-language")
        )
    if len(body) > MAX_BYTES or _shows_tracking(body):
        return None
    return (time.monotonic() + ttl, zlib.compress(CSRF_RE.sub(CSRF_MARK, body), 1), headers)


def _shows_tracking(body):
    """Whether the page shows a parameter of the networks given in its address (the links of
    the languages keep the parameters): it is then not kept for the others."""
    args = request.httprequest.args
    for name in TRACKING_PARAMS.intersection(args):
        for value in args.getlist(name):
            if value and any(form.encode() in body for form in {value, quote(value), quote_plus(value)}):
                return True
    return False


def _answer(entry, jsonrpc):
    """The page kept, with the token of the forms of this visitor."""
    _until, packed, headers = entry
    body = zlib.decompress(packed)
    if CSRF_MARK in body:
        body = body.replace(CSRF_MARK, request.csrf_token().encode())
    if jsonrpc:
        return json.loads(body)
    return request.make_response(body, headers=list(headers))
