"""Small helpers shared by the models and the pages of OCD Live."""

import re

from odoo.tools import format_date


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
