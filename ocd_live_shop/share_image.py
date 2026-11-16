"""Images a vendor shares on their WhatsApp status (JPEG, 1080 x 1350, the size of a status):
one product (its photo, name and price, the QR code of its page), or a page of the catalogue of
their boutique (4 products, the QR code of the boutique).

Drawn like the announcement of a live (`ocd_live.announce_image`, same fonts, colours and
helpers): twice as large, then reduced. The texts come translated from the caller."""

import io

from PIL import Image, ImageDraw, ImageOps

from odoo.addons.ocd_live.announce_image import (
    BOLD,
    DISPLAY,
    FADED,
    HEIGHT,
    INK,
    MARGIN,
    MUTED,
    ORANGE,
    ORANGE_TEXT,
    SEMIBOLD,
    WHITE,
    WIDTH,
    _fit,
    _font,
    _logo,
    _qr,
    _s,
    _shorten,
    _text,
    clean,
)

SAND = (244, 241, 236)
CONTENT = WIDTH - 2 * MARGIN
# Items on a page of the catalogue (2 x 2)
CATALOGUE_ITEMS = 4


def _photo(data, width, height, radius):
    """The photo (bytes) cropped to fill `width` x `height` (pixels of the drawing), with round
    corners: (image, mask). A sand box when there is no photo or it cannot be read."""
    box = Image.new("RGB", (width, height), SAND)
    if data:
        try:
            with Image.open(io.BytesIO(data)) as photo:
                photo = ImageOps.exif_transpose(photo).convert("RGB")
                box = ImageOps.fit(photo, (width, height), Image.Resampling.LANCZOS)
        except (OSError, ValueError, Image.DecompressionBombError):
            pass
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    return box, mask


def _page():
    """A dark page with the orange sun of OCD Live and its name."""
    image = Image.new("RGB", (_s(WIDTH), _s(HEIGHT)), INK)
    draw = ImageDraw.Draw(image)
    draw.ellipse((_s(WIDTH - 330), _s(-420), _s(WIDTH + 420), _s(330)), fill=ORANGE)
    logo = _logo()
    image.paste(logo, (_s(MARGIN), _s(MARGIN)), logo)
    _text(draw, (MARGIN + 128, MARGIN + 52), "OCD Live", _font(DISPLAY, 46), WHITE, anchor="lm")
    return image, draw


def _card(image, draw, top, values, lines):
    """The white card at the bottom: `lines` [(text, font name, size, colour)] at the left, the
    QR code of `values["url"]` at the right, the link under the lines."""
    bottom = HEIGHT - MARGIN
    draw.rounded_rectangle((_s(MARGIN), _s(top), _s(WIDTH - MARGIN), _s(bottom)), radius=_s(44), fill=WHITE)
    qr_size = bottom - top - 64
    qr_left = WIDTH - MARGIN - 32 - qr_size
    image.paste(_qr(values["url"], _s(qr_size)), (_s(qr_left), _s(top + 32)))
    width = qr_left - MARGIN - 48 - 24
    y = top + 30
    for text, name, sizes, colour in lines:
        font, size, fitted = _fit(draw, clean(text), name, sizes, width, 1)
        if fitted:
            _text(draw, (MARGIN + 44, y), fitted[0], font, colour)
        y += size * 1.25
    link = _shorten(draw, values["link"], _font(SEMIBOLD, 28), _s(width))
    _text(draw, (MARGIN + 44, bottom - 60), link, _font(SEMIBOLD, 28), ORANGE)


def _save(image):
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=86, optimize=True, progressive=True)
    return output.getvalue()


def product(values):
    """JPEG of a product. `values`: photo (bytes or None), name, price, vendor, cta and link
    (texts), url (the page of the product, in the QR code)."""
    image, draw = _page()
    top, height = 196, 580
    photo, mask = _photo(values.get("photo"), _s(CONTENT), _s(height), _s(44))
    image.paste(photo, (_s(MARGIN), _s(top)), mask)
    font, size, lines = _fit(draw, clean(values["name"]), DISPLAY, (72, 64, 56, 50), CONTENT, 2)
    y = top + height + 30
    for line in lines:
        _text(draw, (MARGIN, y), line, font, WHITE)
        y += size * 1.08
    _card(image, draw, 1000, values, [
        (values["price"], DISPLAY, (60, 52, 46), ORANGE),
        (values["vendor"], BOLD, (32, 28), INK),
        (values["cta"], SEMIBOLD, (28, 24), MUTED),
    ])
    return _save(image)


def catalogue(values):
    """JPEG of a page of the catalogue of a boutique. `values`: title (the boutique), subtitle
    ("12 products · 1/3"), items [{photo, name, price}] (4 at most), cta and link (texts), url
    (the boutique, in the QR code)."""
    image, draw = _page()
    font, _size, lines = _fit(draw, clean(values["title"]), DISPLAY, (64, 56, 48), CONTENT, 1)
    _text(draw, (MARGIN, 200), lines[0] if lines else "", font, WHITE)
    subtitle = _shorten(draw, clean(values.get("subtitle")), _font(SEMIBOLD, 32), _s(CONTENT))
    _text(draw, (MARGIN, 282), subtitle, _font(SEMIBOLD, 32), FADED)
    gap = 24
    cell_width = (CONTENT - gap) // 2
    photo_height, cell_height = 250, 330
    for index, item in enumerate(values["items"][:CATALOGUE_ITEMS]):
        left = MARGIN + (index % 2) * (cell_width + gap)
        top = 344 + (index // 2) * (cell_height + gap)
        photo, mask = _photo(item.get("photo"), _s(cell_width), _s(photo_height), _s(28))
        image.paste(photo, (_s(left), _s(top)), mask)
        name = _shorten(draw, clean(item["name"]), _font(BOLD, 30), _s(cell_width))
        _text(draw, (left, top + photo_height + 14), name, _font(BOLD, 30), WHITE)
        price = _shorten(draw, clean(item["price"]), _font(BOLD, 30), _s(cell_width))
        _text(draw, (left, top + photo_height + 52), price, _font(BOLD, 30), ORANGE_TEXT)
    _card(image, draw, 1062, values, [
        (values["cta"], DISPLAY, (40, 34, 30), INK),
    ])
    return _save(image)
