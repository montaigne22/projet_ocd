"""Small helpers shared by the models and the pages of OCD Live."""

import base64
import io
import re

import pytz
import qrcode
from babel.dates import get_timezone_location

from odoo.tools import format_date
from odoo.tools.misc import babel_locale_parse


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
