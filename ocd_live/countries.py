"""Countries of OCD Live: the ones offered by default, their continent, and their phone numbers.

The numbers are checked with `phonenumbers` (the rules of Google for every country) when it is
installed; without it, a simple rule keeps the forms working: the dialing code of Odoo and a
national number of 6 to 14 digits (the exact size for the first countries of OCD)."""

import re

import pytz

try:
    import phonenumbers
except ImportError:  # the simple rule below
    phonenumbers = None

# The countries where OCD Live started: first in the lists, after the one of the person
MAIN_COUNTRIES = ("TG", "CM", "BJ", "CI", "SN")

# Offered at the installation: every country of Africa, then the best known of Europe, the
# Americas and Asia (the team adds or removes countries in OCD Live > Configuration > Countries)
AFRICA = (
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CG", "CD", "CI", "DJ", "EG",
    "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG", "MW", "ML",
    "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL", "SO", "ZA", "SS", "SD",
    "TZ", "TG", "TN", "UG", "ZM", "ZW",
)
EUROPE = (
    "FR", "BE", "CH", "LU", "DE", "GB", "IE", "IT", "ES", "PT", "NL", "AT", "SE", "NO", "DK", "FI",
    "PL", "CZ", "RO", "GR", "RU", "UA", "MC",
)
AMERICAS = ("US", "CA", "BR", "MX", "AR", "CO", "CL", "PE", "HT", "DO", "CU", "GP", "MQ", "GF")
ASIA = (
    "CN", "IN", "JP", "KR", "AE", "SA", "QA", "KW", "BH", "OM", "LB", "TR", "IL", "JO", "PK", "ID",
    "MY", "SG", "TH", "VN", "PH",
)
DEFAULT_OFFERED = AFRICA + EUROPE + AMERICAS + ASIA

CONTINENTS = ("africa", "europe", "americas", "asia", "oceania")
# Countries whose first time zone does not tell the continent (islands of the oceans)
CONTINENT_OF = {
    "CV": "africa", "MU": "africa", "SC": "africa", "KM": "africa", "MG": "africa", "RE": "africa",
    "YT": "africa", "SH": "africa", "IS": "europe", "FO": "europe", "PT": "europe", "ES": "europe",
    "BM": "americas", "FK": "americas", "GS": "americas", "MV": "asia", "IO": "asia", "CY": "europe",
    "TR": "asia", "RU": "europe", "GE": "asia", "AM": "asia", "AZ": "asia",
}
ZONE_CONTINENTS = {
    "Africa": "africa", "Europe": "europe", "America": "americas", "Asia": "asia",
    "Australia": "oceania", "Pacific": "oceania", "Antarctica": "oceania",
}

# Size of the national number in the first countries, for the simple rule
KNOWN_SIZES = {"TG": 8, "CM": 9, "BJ": 10, "CI": 10, "SN": 9}


def continent(code):
    """Continent of the country `code` (ISO): africa, europe, americas, asia or oceania."""
    code = (code or "").upper()
    if code in CONTINENT_OF:
        return CONTINENT_OF[code]
    zones = pytz.country_timezones.get(code) if code in pytz.country_timezones else None
    if zones:
        return ZONE_CONTINENTS.get(zones[0].split("/", 1)[0], "oceania")
    return "oceania"


def dial_code(country):
    return f"+{country.phone_code}" if country and country.phone_code else ""


def _digits(value):
    return re.sub(r"\D", "", value or "")


def normalize(country, phone):
    """The number written "+228 90000007" (dialing code, a space, the national number), or
    False when it is not a number of `country`."""
    if not country or not phone:
        return False
    if phonenumbers:
        text = phone.strip()
        if not text.startswith("+") and _digits(text).startswith("00"):
            text = "+" + _digits(text)[2:]
        try:
            number = phonenumbers.parse(text, (country.code or "").upper())
        except phonenumbers.NumberParseException:
            return False
        if country.phone_code and number.country_code != country.phone_code:
            return False
        if not phonenumbers.is_possible_number(number):
            return False
        return f"+{number.country_code} {phonenumbers.national_significant_number(number)}"
    digits = _digits(phone)
    dial = str(country.phone_code or "")
    if digits.startswith("00"):
        digits = digits[2:]
    sizes = (KNOWN_SIZES[country.code],) if country.code in KNOWN_SIZES else tuple(range(6, 15))
    if dial and digits.startswith(dial) and len(digits) - len(dial) in sizes:
        digits = digits[len(dial):]
    if country.code not in KNOWN_SIZES and len(digits) > 6 and digits.startswith("0"):
        digits = digits[1:]  # trunk prefix: 06 12 34 56 78 in France
    if len(digits) not in sizes or not dial:
        return False
    return f"+{dial} {digits}"


def local_digits(country, phone):
    """The number without its dialing code, as the person types it."""
    digits = _digits(phone)
    dial = str(country.phone_code or "") if country else ""
    if dial and (phone or "").strip().startswith("+") and digits.startswith(dial):
        digits = digits[len(dial):]
    return digits


def example(country):
    """An example of mobile number of the country, as written there ("90 11 23 45")."""
    code = (country.code or "").upper() if country else ""
    if phonenumbers and code:
        number = phonenumbers.example_number_for_type(code, phonenumbers.PhoneNumberType.MOBILE)
        if number:
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
    return "90 00 00 00" if code == "TG" else ""


def size(country):
    """Usual size of a mobile number of the country (digits), for the field."""
    code = (country.code or "").upper() if country else ""
    if phonenumbers and code:
        number = phonenumbers.example_number_for_type(code, phonenumbers.PhoneNumberType.MOBILE)
        if number:
            return len(phonenumbers.national_significant_number(number))
    return KNOWN_SIZES.get(code, 9)
