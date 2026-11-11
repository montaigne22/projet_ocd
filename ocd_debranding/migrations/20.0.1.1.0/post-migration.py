import io
import os

from PIL import Image

from odoo import SUPERUSER_ID, api
from odoo.tools import BinaryBytes, file_open

HERE = os.path.dirname(__file__)


def _thumbnail(data):
    return Image.open(io.BytesIO(data)).convert("RGBA").resize((32, 32))


def _same_picture(data, reference):
    """Odoo stores the favicon converted (ICO, 256 px): compare the pictures, not the bytes."""
    try:
        a, b = _thumbnail(data), _thumbnail(reference)
    except OSError:
        return False
    total = sum(abs(x - y) for pa, pb in zip(a.getdata(), b.getdata()) for x, y in zip(pa, pb))
    return total / (32 * 32 * 4) < 8


def migrate(cr, version):
    """The tab icon of the website becomes the round one of OCD Live, when it is still the
    first icon of OCD Live (square, black corners) or the one of Odoo; an icon chosen by the
    team is kept."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    with open(os.path.join(HERE, "favicon_v1.png"), "rb") as icon:
        references = [icon.read()]
    with file_open("web/static/img/favicon.ico", "rb") as icon:
        references.append(icon.read())
    with file_open("ocd_debranding/static/img/favicon.png", "rb") as icon:
        new_icon = icon.read()
    for website in env["website"].search([]):
        current = bytes(website.favicon) if website.favicon else b""
        if not current or any(_same_picture(current, reference) for reference in references):
            website.favicon = BinaryBytes(new_icon, filename="favicon.png")
