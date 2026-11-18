"""The clip of a product of a live (chantier 8, design ClipsAutomatiques): a vertical video of 30
seconds at most, cut with ffmpeg from the video of the live, with its texts drawn with Pillow.

- Vertical (720 x 1280, or 1080 x 1920): a video of a live already vertical (TikTok) fills the
  image; a horizontal one is laid on a blurred copy of itself, nothing is cut.
- The texts stay out of the zones that TikTok, Reels and the statuses cover with their buttons:
  the bottom (caption, « Reply »), the right column and the very top. The logo « Seen in live »
  at the top left; the name of the product, the vendor and the short link in a white band above
  the bottom zone.
- The last 2 seconds: the name, the QR code and the link, on the colours of OCD Live.
- The sound of the live, faded out at the end; no music added (the rights).

ffmpeg is the one of the server (ocd_live/media.py): started without the limits of the worker,
with 2 threads and a low priority, so that the site does not slow down while clips are made."""
import functools
import io
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from odoo.tools.misc import file_path

from odoo.addons.ocd_live import announce_image, media, tools

_logger = logging.getLogger(__name__)

# The sizes of a clip (setting « Quality »)
SIZES = {"720": (720, 1280), "1080": (1080, 1920)}
# The end of the clip: its name, its QR code and its link
END_SECONDS = 2
# The zones covered by the apps, in parts of the image
TOP_COVERED = 0.08
BOTTOM_COVERED = 0.22
RIGHT_COVERED = 0.13
# A video at least this tall (height / width) fills the clip; flatter, it is laid on a blur
TALL_RATIO = 1.5
# ffmpeg: the time of one clip, its threads, its priority
TIMEOUT = 180
THREADS = "2"
NICE = 15
# The weight of a clip: under 16 MB (a video of WhatsApp) also in 1080
MAX_RATE = {"720": "1800k", "1080": "3500k"}

INK = (21, 19, 15)
WHITE = (255, 255, 255)
ORANGE = (244, 106, 0)
ORANGE_DARK = (184, 79, 0)
ORANGE_SOFT = (255, 201, 153)
MUTED = (102, 95, 88)
FADED = (201, 195, 188)
RED_LIVE = (255, 77, 90)

DISPLAY = "BricolageGrotesque-ExtraBold"
BOLD = "Figtree-Bold"
SEMIBOLD = "Figtree-SemiBold"
EXTRABOLD = "Figtree-ExtraBold"


class ClipError(Exception):
    """A clip that cannot be made: `code` says why (for the team), `values` the details."""

    def __init__(self, code, **values):
        super().__init__(code)
        self.code = code
        self.values = values


@functools.lru_cache(maxsize=64)
def _font(name, size):
    return ImageFont.truetype(file_path(f"ocd_live/static/fonts/{name}.ttf"), max(int(size), 8))


def _fit(draw, text, name, sizes, width, max_lines):
    """The largest of `sizes` where `text` holds in `max_lines` lines of `width`; the smallest,
    shortened, otherwise. Return (font, size, lines)."""
    for size in sizes:
        font = _font(name, size)
        lines = announce_image._wrap(draw, text, font, width)
        if len(lines) <= max_lines and all(draw.textlength(line, font=font) <= width for line in lines):
            return font, size, lines
    font = _font(name, sizes[-1])
    lines = announce_image._wrap(draw, text, font, width)[:max_lines]
    if lines:
        lines[-1] = announce_image._shorten(draw, lines[-1], font, width)
    return font, sizes[-1], lines


def _logo(size):
    with Image.open(file_path("ocd_live/static/img/ocd_logo_round.png")) as logo:
        return logo.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def _brand_width(draw, k, label):
    name_width = draw.textlength("OCD", font=_font(EXTRABOLD, 24 * k))
    live_width = draw.textlength("LIVE", font=_font(EXTRABOLD, 15 * k)) + round(26 * k)
    label_width = draw.textlength(label, font=_font(BOLD, 21 * k)) if label else 0
    return round(8 * k) + round(40 * k) + round(8 * k) + name_width + round(8 * k) + live_width + (
        round(10 * k) + label_width if label else 0) + round(14 * k)


def _brand(image, draw, left, top, k, label):
    """« (logo) OCD ● LIVE Seen in live » at (left, top); return its width."""
    height = round(52 * k)
    logo = _logo(round(40 * k))
    pad = round(8 * k)
    name_font = _font(EXTRABOLD, 24 * k)
    live_font = _font(EXTRABOLD, 15 * k)
    label_font = _font(BOLD, 21 * k)
    name_width = draw.textlength("OCD", font=name_font)
    live_width = draw.textlength("LIVE", font=live_font) + round(26 * k)
    width = _brand_width(draw, k, label)
    draw.rounded_rectangle((left, top, left + width, top + height), radius=height // 2, fill=(*INK, 200))
    image.alpha_composite(logo, (left + pad, top + (height - logo.height) // 2))
    x = left + pad + logo.width + round(8 * k)
    middle = top + height / 2
    draw.text((x, middle), "OCD", font=name_font, fill=WHITE, anchor="lm")
    x += name_width + round(8 * k)
    pill_top, pill_bottom = middle - round(12 * k), middle + round(12 * k)
    draw.rounded_rectangle((x, pill_top, x + live_width, pill_bottom), radius=round(6 * k), fill=ORANGE)
    dot = round(4 * k)
    draw.ellipse((x + round(7 * k), middle - dot, x + round(7 * k) + 2 * dot, middle + dot), fill=WHITE)
    draw.text((x + round(18 * k), middle), "LIVE", font=live_font, fill=WHITE, anchor="lm")
    x += live_width + round(10 * k)
    if label:
        draw.text((x, middle), label, font=label_font, fill=WHITE, anchor="lm")
    return width


def overlay(values, quality="720"):
    """The texts over the video (PNG with transparency). `values`: name, by (the vendor and
    their city), link (the short link written), seen (« Seen in live »)."""
    width, height = SIZES[quality]
    k = width / 720
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = round(24 * k)
    _brand(image, draw, margin, round(height * TOP_COVERED), k, announce_image.clean(values.get("seen")))
    # The band: above the bottom zone, out of the right column
    right = round(width * (1 - RIGHT_COVERED))
    inner = right - margin - 2 * round(20 * k)
    name_font, name_size, name_lines = _fit(
        draw, announce_image.clean(values["name"]), DISPLAY, [s * k for s in (44, 40, 36, 32, 28)], inner, 2
    )
    by_font = _font(SEMIBOLD, 23 * k)
    by = announce_image._shorten(draw, announce_image.clean(values.get("by")), by_font, inner)
    link_font, link_size, link_lines = _fit(draw, values["link"], DISPLAY, [s * k for s in (32, 28, 24, 20)], inner, 1)
    pad = round(20 * k)
    band_height = pad + name_size * 1.08 * len(name_lines) + (by_font.size * 1.35 if by else 0) + link_size * 1.3 + pad
    bottom = round(height * (1 - BOTTOM_COVERED)) - round(12 * k)
    top = bottom - round(band_height)
    draw.rounded_rectangle((margin, top, right, bottom), radius=round(24 * k), fill=(*WHITE, 246))
    y = top + pad
    for line in name_lines:
        draw.text((margin + pad, y), line, font=name_font, fill=INK)
        y += name_size * 1.08
    if by:
        draw.text((margin + pad, y + round(2 * k)), by, font=by_font, fill=MUTED)
        y += by_font.size * 1.35
    draw.text((margin + pad, y + round(2 * k)), link_lines[0] if link_lines else "", font=link_font, fill=ORANGE_DARK)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def end_card(values, quality="720"):
    """The last 2 seconds (PNG): the brand, the name, the QR code of the link and the link.
    `values`: name, link (written), url (in the QR code), line (« Delivery with a code... »)."""
    width, height = SIZES[quality]
    k = width / 720
    image = Image.new("RGBA", (width, height), (*INK, 255))
    draw = ImageDraw.Draw(image)
    # A soft orange sun at the top right, as on the image that announces a live
    draw.ellipse((width - round(260 * k), -round(330 * k), width + round(330 * k), round(260 * k)), fill=(*ORANGE, 255))
    content = width - 2 * round(64 * k)
    brand_width = _brand_width(draw, k, "")
    top = round(height * 0.16)
    _brand(image, draw, (width - brand_width) // 2, top, k, "")
    name_font, name_size, name_lines = _fit(
        draw, announce_image.clean(values["name"]), DISPLAY, [s * k for s in (56, 50, 44, 38, 32)], content, 3
    )
    y = top + round(96 * k)
    for line in name_lines:
        draw.text((width / 2, y), line, font=name_font, fill=WHITE, anchor="ma")
        y += name_size * 1.08
    qr_size = round(300 * k)
    border = round(18 * k)
    qr_top = max(round(y + 36 * k), round(height * 0.42))
    left = (width - qr_size) // 2
    draw.rounded_rectangle(
        (left - border, qr_top - border, left + qr_size + border, qr_top + qr_size + border), radius=round(24 * k), fill=WHITE
    )
    qr = tools.qr_image(values["url"], box_size=20).resize((qr_size, qr_size), Image.Resampling.NEAREST).convert("RGBA")
    image.alpha_composite(qr, (left, qr_top))
    y = qr_top + qr_size + border + round(40 * k)
    link_font, link_size, link_lines = _fit(draw, values["link"], DISPLAY, [s * k for s in (40, 36, 32, 28, 24)], content, 1)
    draw.text((width / 2, y), link_lines[0] if link_lines else "", font=link_font, fill=ORANGE_SOFT, anchor="ma")
    y += link_size * 1.4
    line = announce_image.clean(values.get("line"))
    if line:
        line_font, _size, line_lines = _fit(draw, line, SEMIBOLD, [s * k for s in (26, 24, 22)], content, 2)
        for text in line_lines:
            draw.text((width / 2, y), text, font=line_font, fill=FADED, anchor="ma")
            y += line_font.size * 1.3
    output = io.BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


# === THE VIDEO OF THE LIVE === #

def probe(path):
    """{duration, width, height, sound} of the video at `path` (its rotation taken into account);
    raise ClipError("unreadable") when it has no image."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            code, stdout, _stderr = media.run(
                [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise ClipError("unreadable") from None
        if code:
            raise ClipError("unreadable")
        info = json.loads(stdout or b"{}")
        streams = info.get("streams") or []
        images = [
            stream for stream in streams
            if stream.get("codec_type") == "video" and not (stream.get("disposition") or {}).get("attached_pic")
        ]
        if not images:
            raise ClipError("unreadable")
        stream = images[0]
        width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
        rotation = 0
        for side in stream.get("side_data_list") or []:
            if "rotation" in side:
                rotation = abs(int(float(side["rotation"])))
        rotation = rotation or abs(int(float((stream.get("tags") or {}).get("rotate") or 0)))
        if rotation in (90, 270):
            width, height = height, width
        duration = float((info.get("format") or {}).get("duration") or stream.get("duration") or 0)
        sound = any(item.get("codec_type") == "audio" for item in streams)
    else:
        try:
            _code, _stdout, stderr = media.run([media.ffmpeg(), "-hide_banner", "-i", str(path)], timeout=120)
        except subprocess.TimeoutExpired:
            raise ClipError("unreadable") from None
        text = stderr.decode("utf-8", "replace")
        video = re.search(r"Stream #\d+:\d+.*: Video: [^\n]*?(\d{2,5})x(\d{2,5})", text)
        if not video:
            raise ClipError("unreadable")
        width, height = int(video[1]), int(video[2])
        match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", text)
        duration = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else 0
        sound = ": Audio:" in text
    if not width or not height or duration <= 0:
        raise ClipError("unreadable")
    return {"duration": duration, "width": width, "height": height, "sound": sound}


def _geometry(width, height, size):
    """The filter that makes a vertical image of `size` from a video of `width` x `height`."""
    target_width, target_height = size
    fill = f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height}"
    if height / max(width, 1) >= TALL_RATIO:
        return f"[0:v]{fill},setsar=1,fps=30[base]"
    return (
        f"[0:v]split=2[back][front];[back]{fill},boxblur=20:2,eq=brightness=-0.08[blur];"
        f"[front]scale={target_width}:-2[sharp];[blur][sharp]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30[base]"
    )


def _command(*args):
    """ffmpeg with a low priority when the server allows it."""
    nice = shutil.which("nice")
    return [*([nice, "-n", str(NICE)] if nice else []), media.ffmpeg(), "-y", "-v", "error", *args]


def make(source, start, duration, info, overlay_png, end_png, quality="720"):
    """The clip: (video MP4, poster JPEG). `source` the path of the video of the live, `start`
    and `duration` in seconds, `info` its probe(). Raise ClipError."""
    if not media.can_convert():
        raise ClipError("no_ffmpeg")
    size = SIZES[quality]
    duration = round(max(duration, 1.0), 2)
    end_from = max(duration - END_SECONDS, 0)
    with tempfile.TemporaryDirectory(prefix="ocd_clip_") as folder:
        folder = Path(folder)
        (folder / "overlay.png").write_bytes(overlay_png)
        (folder / "end.png").write_bytes(end_png)
        target = folder / "clip.mp4"
        graph = (
            f"{_geometry(info['width'], info['height'], size)};"
            f"[base][1:v]overlay=0:0[texts];[texts][2:v]overlay=0:0:enable='gte(t,{end_from})'[video]"
        )
        command = _command(
            "-threads", THREADS, "-ss", f"{max(start, 0):.2f}", "-t", f"{duration:.2f}", "-i", str(source),
            "-i", str(folder / "overlay.png"), "-i", str(folder / "end.png"),
            "-filter_complex", graph, "-map", "[video]",
        )
        if info.get("sound"):
            command += ["-map", "0:a:0", "-af", f"afade=t=out:st={max(duration - 1, 0):.2f}:d=1",
                        "-c:a", "aac", "-b:a", "96k", "-ac", "2"]
        else:
            command += ["-an"]
        command += [
            "-t", f"{duration:.2f}", "-threads", THREADS,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-maxrate", MAX_RATE[quality],
            "-bufsize", f"{int(MAX_RATE[quality][:-1]) * 2}k", "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(target),
        ]
        try:
            code, _stdout, stderr = media.run(command, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise ClipError("too_slow") from None
        if code or not target.exists() or not target.stat().st_size:
            _logger.info("OCD Live: clip not made (%s): %s", code, stderr[-800:])
            raise ClipError("ffmpeg", detail=stderr.decode("utf-8", "replace")[-300:])
        poster = folder / "poster.jpg"
        try:
            media.run(_command("-ss", f"{min(1.5, duration / 2):.2f}", "-i", str(target), "-frames:v", "1",
                               "-vf", "scale=360:-2", "-q:v", "4", str(poster)), timeout=60)
        except subprocess.TimeoutExpired:
            pass
        return target.read_bytes(), (poster.read_bytes() if poster.exists() else None)


def preview(source, start, info, seconds=8):
    """A small video (360 x 640, without the texts) from `start`: to check the shift of the
    video of the live with its first moment. Raise ClipError."""
    if not media.can_convert():
        raise ClipError("no_ffmpeg")
    with tempfile.TemporaryDirectory(prefix="ocd_preview_") as folder:
        target = Path(folder) / "preview.mp4"
        graph = _geometry(info["width"], info["height"], (360, 640))
        command = _command(
            "-threads", THREADS, "-ss", f"{max(start, 0):.2f}", "-t", str(seconds), "-i", str(source),
            "-filter_complex", graph, "-map", "[base]",
            *(["-map", "0:a:0", "-c:a", "aac", "-b:a", "64k", "-ac", "1"] if info.get("sound") else ["-an"]),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "32", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(target),
        )
        try:
            code, _stdout, _stderr = media.run(command, timeout=60)
        except subprocess.TimeoutExpired:
            raise ClipError("too_slow") from None
        if code or not target.exists():
            raise ClipError("ffmpeg")
        return target.read_bytes()
