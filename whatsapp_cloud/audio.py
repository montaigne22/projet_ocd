"""The sounds between Odoo and WhatsApp, converted with ffmpeg.

- Sent: a voice message recorded in Odoo (MP3) reaches the customer as a voice note only in OGG
  Opus (mono), with ``"voice": true``; a sound WhatsApp does not take (WAV, WebM, FLAC, an OGG
  that is not Opus) is converted to OGG Opus too.
- Received: the voice notes of the customers (OGG Opus, AMR) do not play in the browsers of old
  iPhones (Safari): kept as MP3, which every browser plays.

ffmpeg is the one of the server (``apt-get install ffmpeg``), else the one of imageio-ffmpeg (pip,
requirements.txt). Without it, the files go and stay as they are.
"""
import logging
import os
import shutil
import subprocess
import tempfile

_logger = logging.getLogger(__name__)

# A voice message lasts a few minutes: converted within this time, or left as it is
TIMEOUT = 60
# The result of each conversion: extension, mimetype, ffmpeg arguments of the output
FORMATS = {
    # voice note of WhatsApp: Opus in OGG, mono, 48 kHz, voice tuning
    "voice": (".ogg", "audio/ogg", ["-ar", "48000", "-c:a", "libopus", "-b:a", "32k", "-application", "voip",
                                    "-f", "ogg"]),
    # played by every browser
    "mp3": (".mp3", "audio/mpeg", ["-ar", "44100", "-c:a", "libmp3lame", "-q:a", "5", "-f", "mp3"]),
}


def ffmpeg():
    """The ffmpeg of the server, else the one of imageio-ffmpeg (pip), else None."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg  # noqa: PLC0415 (optional)

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 (not installed, or no ffmpeg for this system)
        return None


def convert(raw, target):
    """The sound `raw` (any format ffmpeg reads) in the format `target` of FORMATS, mono: the
    bytes, or None when it cannot be converted (no ffmpeg, not a sound, too long)."""
    binary = ffmpeg()
    raw = bytes(raw or b"")  # the content of an attachment (BinaryValue) or bytes
    if not binary or not raw:
        return None
    extension, _mimetype, arguments = FORMATS[target]
    with tempfile.TemporaryDirectory(prefix="whatsapp_audio_") as folder:
        source = os.path.join(folder, "source")
        output = os.path.join(folder, f"sound{extension}")
        with open(source, "wb") as file:
            file.write(raw)
        command = [binary, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", source,
                   "-vn", "-ac", "1", *arguments, output]
        try:
            subprocess.run(command, capture_output=True, timeout=TIMEOUT, check=True)
        except subprocess.CalledProcessError as error:
            _logger.warning("WhatsApp: sound not converted to %s: %s", target,
                            (error.stderr or b"").decode(errors="replace").strip()[-300:])
            return None
        except (OSError, subprocess.SubprocessError) as error:
            _logger.warning("WhatsApp: sound not converted to %s: %s", target, error)
            return None
        with open(output, "rb") as file:
            data = file.read()
    return data or None


def mimetype_of(target):
    return FORMATS[target][1]


def extension_of(target):
    return FORMATS[target][0]
