"""Small helpers shared by the models and the pages of OCD Live."""

import base64
import functools
import io
import re

import logging
from urllib.parse import urljoin, urlsplit, urlunsplit

import pytz
import qrcode
import requests
from babel.dates import get_timezone_location

from odoo.tools import format_date
from odoo.tools.misc import babel_locale_parse

_logger = logging.getLogger(__name__)

# Short links of the platforms (Share › Copy the link on a phone): the page of a replay plays a
# video from its full address only, which holds the number of the video
SHORT_VIDEO_HOSTS = ("vt.tiktok.com", "vm.tiktok.com", "fb.watch")
REDIRECTS = (301, 302, 303, 307, 308)
_expanded = {}


def day_text(env, day, pattern="EEEE d MMMM", capital=False):
    """Return `day` written in the language of `env`, e.g. "Mardi 1er décembre" or
    "mar. 1er déc." (French writes the first day of the month "1er")."""
    text = format_date(env, day, date_format=pattern)
    if day.day == 1 and (env.lang or "").startswith("fr"):
        text = re.sub(r"(?<!\d)1(?!\d)", "1er", text, count=1)
    return text[:1].upper() + text[1:] if capital else text


def hour_text(value):
    """Return an hour given as a float, e.g. 18.5 → "18:30"."""
    minutes = round(value * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def qr_image(data, box_size=12):
    """QR code of `data` (PIL image), black on white and without margin; it still reads with a
    scratch or a fold (level M). Made with `qrcode`, needed by Odoo: no drawing engine of
    reportlab to install."""
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=0)
    code.add_data(data)
    code.make(fit=True)
    return code.make_image(fill_color="black", back_color="white").get_image().convert("L")


def qr_data_uri(data, box_size=12):
    """QR code of `data` for a page or a PDF (PNG in the address of the image)."""
    output = io.BytesIO()
    qr_image(data, box_size).save(output, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


# Names without a place: a default of Odoo or a browser that hides its zone, never the one of a
# person (Lomé, Dakar or Abidjan have their own name)
NO_PLACE_ZONES = {"UTC", "Etc/UTC", "Etc/GMT", "GMT", "Etc/Universal", "Universal", "Etc/Zulu", "Zulu", "Etc/Greenwich"}


def valid_tz(name):
    """The time zone `name` when it is the one of a place (browsers give their own names),
    else None."""
    if not name or name in NO_PLACE_ZONES:
        return None
    try:
        zone = pytz.timezone(name).zone
    except (pytz.UnknownTimeZoneError, ValueError):
        return None
    return None if zone in NO_PLACE_ZONES else zone


def to_tz(value, tz_name):
    """A naive UTC datetime (as stored by the ORM), as an aware datetime of `tz_name`."""
    return pytz.utc.localize(value).astimezone(pytz.timezone(tz_name))


def zone_text(env, tz_name):
    """Name of a time zone for the person reading, in their language: "Heure : Cameroun",
    "Togo Time", "Heure : Canada (Toronto)"."""
    text = get_timezone_location(pytz.timezone(tz_name), locale=babel_locale_parse(env.lang or "en_US"))
    return text[:1].upper() + text[1:]


def same_offset(tz_a, tz_b, moment):
    """Whether two time zones show the same hour at `moment` (naive UTC)."""
    return to_tz(moment, tz_a).utcoffset() == to_tz(moment, tz_b).utcoffset()


@functools.cache
def _zone_countries():
    return {zone: code for code in pytz.country_timezones for zone in pytz.country_timezones[code]}


def country_of_tz(tz_name):
    """ISO code of the country of a time zone (Africa/Douala: CM), or None."""
    zone = valid_tz(tz_name)
    return _zone_countries().get(zone) if zone else None


def whatsapp_url(phone, text):
    """Link that opens WhatsApp with `phone` and a message ready to send, or False."""
    from urllib.parse import quote

    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 8:
        return False
    return f"https://wa.me/{digits}?text={quote(text)}"


def is_short_video_link(url):
    """Whether `url` is a short link of a video (vt.tiktok.com/ZS…, tiktok.com/t/…, fb.watch/…)."""
    parts = urlsplit((url or "").strip())
    host = (parts.hostname or "").lower()
    return host in SHORT_VIDEO_HOSTS or (host.endswith("tiktok.com") and parts.path.startswith("/t/"))


def expand_video_link(url, timeout=8):
    """The full address behind a short link of a video, as the platform gives it (its
    redirections are followed, the page itself is not loaded); the link as it is when it is
    not a short link, or when the platform does not answer. TikTok: without the tracking
    parameters (« ?_r=1&_t=… »)."""
    url = (url or "").strip()
    if not is_short_video_link(url):
        return url
    if url in _expanded:
        return _expanded[url]
    current = url
    for _hop in range(5):
        try:
            response = requests.head(current, allow_redirects=False, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code == 405:  # HEAD refused: the same with GET, without the page
                response = requests.get(current, allow_redirects=False, timeout=timeout, stream=True,
                                        headers={"User-Agent": "Mozilla/5.0"})
                response.close()
        except requests.RequestException as error:
            _logger.info("OCD Live: short link %s not opened: %s", url, error)
            return url
        location = response.headers.get("Location")
        if response.status_code not in REDIRECTS or not location:
            break
        current = urljoin(current, location)
        if not is_short_video_link(current):
            break
    if current == url or is_short_video_link(current) or not current.startswith("https://"):
        return url
    parts = urlsplit(current)
    if (parts.hostname or "").endswith("tiktok.com"):
        current = urlunsplit(("https", parts.netloc, parts.path, "", ""))
    _expanded[url] = current
    return current
