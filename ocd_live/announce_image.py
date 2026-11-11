"""Image that announces a live, to share with friends (PNG made with Pillow, 1080 x 1350).

Nothing personal on it: the public name of the vendor, what they sell, the day and the hour of
the live, the page where to find it (link and QR code). It is drawn twice as large, then reduced:
the round corners and the texts stay smooth."""

import functools
import io
import re
import unicodedata

from PIL import Image, ImageDraw, ImageFont

from odoo.tools.misc import file_path

from . import tools

WIDTH, HEIGHT = 1080, 1350
SCALE = 2
MARGIN = 72

ORANGE = (244, 106, 0)
ORANGE_TEXT = (255, 154, 77)
INK = (21, 19, 15)
INK_SOFT = (43, 39, 34)
MUTED = (102, 95, 88)
FADED = (201, 195, 188)
WHITE = (255, 255, 255)
RED_LIVE = (255, 77, 90)

DISPLAY = "BricolageGrotesque-ExtraBold"
BOLD = "Figtree-Bold"
SEMIBOLD = "Figtree-SemiBold"
EXTRABOLD = "Figtree-ExtraBold"


def _s(value):
    return round(value * SCALE)


@functools.lru_cache(maxsize=64)
def _font(name, size):
    return ImageFont.truetype(file_path(f"ocd_live/static/fonts/{name}.ttf"), _s(size))


def clean(text):
    """Text that the fonts can draw: no emoji nor symbol, one space between the words."""
    kept = "".join(
        char for char in (text or "")
        if unicodedata.category(char) not in ("So", "Sk", "Cs", "Co", "Cn", "Cc", "Cf")
    )
    return re.sub(r"\s+", " ", kept).strip()


def _width(draw, text, font):
    return draw.textlength(text, font=font)


def _shorten(draw, text, font, width):
    if _width(draw, text, font) <= width:
        return text
    while text and _width(draw, text + "…", font) > width:
        text = text[:-1]
    return text.rstrip(" ,·-") + "…"


def _wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split(" "):
        candidate = f"{line} {word}".strip()
        if line and _width(draw, candidate, font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def _fit(draw, text, name, sizes, width, max_lines):
    """The largest of `sizes` where `text` holds in `max_lines` lines of `width` (at most);
    the smallest size, shortened, when no size is enough."""
    for size in sizes:
        font = _font(name, size)
        lines = _wrap(draw, text, font, _s(width))
        if len(lines) <= max_lines and all(_width(draw, line, font) <= _s(width) for line in lines):
            return font, size, lines
    size = sizes[-1]
    font = _font(name, size)
    lines = _wrap(draw, text, font, _s(width))
    lines = lines[:max_lines]
    if lines:
        lines[-1] = _shorten(draw, lines[-1], font, _s(width))
    return font, size, lines


def _text(draw, xy, text, font, fill, anchor="la"):
    draw.text((_s(xy[0]), _s(xy[1])), text, font=font, fill=fill, anchor=anchor)


def _logo():
    path = file_path("ocd_live/static/img/ocd_logo_round.png")
    with Image.open(path) as logo:
        return logo.convert("RGBA").resize((_s(104), _s(104)), Image.Resampling.LANCZOS)


def _qr(link, size):
    """The QR code of the page, its squares kept sharp."""
    return tools.qr_image(link, box_size=20).resize((size, size), Image.Resampling.NEAREST)


def render(values):
    """PNG of the announcement. `values`: headline, name, category, day, hour, time_zone,
    cta and link (texts), url (the page, in the QR code)."""
    image = Image.new("RGB", (_s(WIDTH), _s(HEIGHT)), INK)
    draw = ImageDraw.Draw(image)
    content = WIDTH - 2 * MARGIN

    # Shapes of the background: an orange sun at the top, a soft ring in the corner below
    draw.ellipse((_s(WIDTH - 330), _s(-420), _s(WIDTH + 420), _s(330)), fill=ORANGE)
    draw.ellipse((_s(WIDTH - 210), _s(HEIGHT - 190), _s(WIDTH + 190), _s(HEIGHT + 210)), outline=INK_SOFT, width=_s(40))

    # Brand and "LIVE"
    image.paste(_logo(), (_s(MARGIN), _s(MARGIN)), _logo())
    _text(draw, (MARGIN + 128, MARGIN + 52), "OCD Live", _font(DISPLAY, 46), WHITE, anchor="lm")
    pill = _font(EXTRABOLD, 30)
    label = "LIVE"
    pill_width = _width(draw, label, pill) / SCALE + 86
    left = WIDTH - MARGIN - pill_width
    draw.rounded_rectangle(
        (_s(left), _s(MARGIN + 22), _s(WIDTH - MARGIN), _s(MARGIN + 82)), radius=_s(30), fill=WHITE
    )
    draw.ellipse((_s(left + 26), _s(MARGIN + 42), _s(left + 46), _s(MARGIN + 62)), fill=RED_LIVE)
    _text(draw, (left + 60, MARGIN + 52), label, pill, INK, anchor="lm")

    # What is announced, then who: in the middle of the space above the card
    head_font, head_size, head_lines = _fit(
        draw, clean(values["headline"]).upper(), EXTRABOLD, (40, 36, 32), content, 1
    )
    name_font, name_size, name_lines = _fit(
        draw, clean(values["name"]), DISPLAY, (132, 120, 108, 96, 84, 76), content, 2
    )
    category = clean(values.get("category"))
    height = head_size * 1.2 + 24 + name_size * 1.04 * len(name_lines) + (22 + 42 * 1.2 if category else 0)
    top = 230 + (500 - height) / 2
    _text(draw, (MARGIN, top), head_lines[0] if head_lines else "", head_font, ORANGE_TEXT)
    top += head_size * 1.2 + 24
    for line in name_lines:
        _text(draw, (MARGIN, top), line, name_font, WHITE)
        top += name_size * 1.04
    if category:
        line = _shorten(draw, category, _font(SEMIBOLD, 42), _s(content))
        _text(draw, (MARGIN, top + 22), line, _font(SEMIBOLD, 42), FADED)

    # When: the day and the hour, and the QR code of the page
    card_top, card_bottom = 760, 1150
    draw.rounded_rectangle(
        (_s(MARGIN), _s(card_top), _s(WIDTH - MARGIN), _s(card_bottom)), radius=_s(44), fill=WHITE
    )
    qr_size = 250
    qr_left = WIDTH - MARGIN - 56 - qr_size
    text_width = qr_left - MARGIN - 56 - 40
    day_font, _size, day_lines = _fit(draw, clean(values["day"]), BOLD, (48, 44, 40, 36), text_width, 1)
    _text(draw, (MARGIN + 56, card_top + 58), day_lines[0] if day_lines else "", day_font, INK)
    hour_font, _size, hour_lines = _fit(draw, values["hour"], DISPLAY, (172, 156, 140), text_width, 1)
    _text(draw, (MARGIN + 50, card_top + 112), hour_lines[0] if hour_lines else "", hour_font, ORANGE)
    zone_font, _size, zone_lines = _fit(draw, clean(values["time_zone"]), SEMIBOLD, (34, 30), text_width, 1)
    _text(draw, (MARGIN + 56, card_top + 314), zone_lines[0] if zone_lines else "", zone_font, MUTED)
    qr = _qr(values["url"], _s(qr_size))
    image.paste(qr, (_s(qr_left), _s(card_top + 70)))

    # The invitation and the address of the page
    font, _size, lines = _fit(draw, clean(values["cta"]), DISPLAY, (56, 50, 44), content, 1)
    _text(draw, (MARGIN, 1196), lines[0] if lines else "", font, WHITE)
    link = _shorten(draw, values["link"], _font(SEMIBOLD, 34), _s(content))
    _text(draw, (MARGIN, 1272), link, _font(SEMIBOLD, 34), ORANGE_TEXT)

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
