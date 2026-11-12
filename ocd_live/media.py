"""The short video of a vendor for its card in the feed of the lives.

A video sent from a phone is checked (kind, size); when ffmpeg is installed on the server, it is
made readable by every phone and every browser: MP4 (H.264, AAC), at most 720 pixels wide and
30 seconds, with « fast start » so that it starts at once, and its first image becomes the
poster of the card. Without ffmpeg, only MP4 and WebM videos are kept (most phones record MP4),
with a smaller size limit since they are kept as they are."""

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

MAX_SECONDS = 30
MAX_UPLOAD_MB = 60  # a phone video of 30 to 60 seconds, before it is made smaller
MAX_KEPT_MB = 15  # kept as it is, without ffmpeg
READABLE = ("video/mp4", "video/webm")
ACCEPTED = (*READABLE, "video/quicktime", "video/3gpp", "video/x-matroska", "video/x-msvideo")
TIMEOUT = 180


class VideoError(ValueError):
    """A video that cannot be the video of a card: its message says why, for the vendor."""

    def __init__(self, code, **values):
        super().__init__(code)
        self.code = code
        self.values = values


def can_convert():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def kind(data):
    """The kind of a video from its first bytes, also when the server cannot guess it (no
    libmagic): MP4, QuickTime and 3GP (« ftyp »), WebM and Matroska, AVI."""
    mimetype = guess_mimetype(data, default="application/octet-stream")
    if mimetype.startswith("video/"):
        return mimetype
    head = data[:16]
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand.startswith(b"qt"):
            return "video/quicktime"
        return "video/3gpp" if brand.startswith(b"3g") else "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm" if b"webm" in data[:4096] else "video/x-matroska"
    if head[:4] == b"RIFF" and head[8:12] == b"AVI ":
        return "video/x-msvideo"
    return mimetype


def _probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, timeout=60, check=False,
    )
    if result.returncode:
        raise VideoError("unreadable")
    info = json.loads(result.stdout or b"{}")
    streams = info.get("streams") or []
    if not any(stream.get("codec_type") == "video" for stream in streams):
        raise VideoError("unreadable")
    duration = float((info.get("format") or {}).get("duration") or 0)
    has_sound = any(stream.get("codec_type") == "audio" for stream in streams)
    return duration, has_sound


def prepare(data):
    """Return (video, poster, mimetype, sound) for the card, from the bytes sent (sound: whether
    the video has sound, None when unknown); raise VideoError."""
    if not data:
        raise VideoError("empty")
    mimetype = kind(data)
    if mimetype not in ACCEPTED and not mimetype.startswith("video/"):
        raise VideoError("not_video")
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        raise VideoError("too_big", size=MAX_UPLOAD_MB)
    if not can_convert():
        if mimetype not in READABLE:
            raise VideoError("format")
        if size_mb > MAX_KEPT_MB:
            raise VideoError("too_big", size=MAX_KEPT_MB)
        return data, None, mimetype, None
    with tempfile.TemporaryDirectory(prefix="ocd_video_") as folder:
        source = Path(folder) / "source"
        source.write_bytes(data)
        duration, has_sound = _probe(source)
        if duration > MAX_SECONDS * 4:
            raise VideoError("too_long", seconds=MAX_SECONDS)
        target = Path(folder) / "card.mp4"
        command = [
            "ffmpeg", "-y", "-v", "error", "-i", str(source), "-t", str(MAX_SECONDS),
            "-vf", "scale='min(720,iw)':-2,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]
        command += ["-c:a", "aac", "-b:a", "96k", "-ac", "2"] if has_sound else ["-an"]
        try:
            result = subprocess.run([*command, str(target)], capture_output=True, timeout=TIMEOUT, check=False)
        except subprocess.TimeoutExpired:
            raise VideoError("too_long", seconds=MAX_SECONDS) from None
        if result.returncode or not target.exists():
            _logger.info("OCD Live: video not converted: %s", result.stderr[-500:])
            raise VideoError("unreadable")
        poster = Path(folder) / "poster.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", "0.3", "-i", str(target), "-frames:v", "1", "-q:v", "3", str(poster)],
            capture_output=True, timeout=60, check=False,
        )
        return target.read_bytes(), (poster.read_bytes() if poster.exists() else None), "video/mp4", has_sound
