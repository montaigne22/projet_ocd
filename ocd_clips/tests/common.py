import shutil
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from odoo import fields

from odoo.addons.ocd_live import media
from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon

from ..models.ocd_live_recording import OcdLiveRecording


def make_video(seconds=40, size="320x180", sound=True, rate=10):
    """A video of a live made by ffmpeg (lavfi): horizontal by default, with sound."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "live.mp4"
        command = [media.ffmpeg(), "-y", "-v", "error", "-f", "lavfi", "-i",
                   f"testsrc=size={size}:rate={rate}:duration={seconds}"]
        if sound:
            command += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
        command += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
        if sound:
            command += ["-c:a", "aac", "-shortest"]
        command.append(str(path))
        subprocess.run(command, check=True, capture_output=True, timeout=120)
        return path.read_bytes()


def probe(data):
    """The probe of a video given as bytes."""
    from .. import clip_video  # noqa: PLC0415

    with tempfile.NamedTemporaryFile(suffix=".mp4") as handle:
        handle.write(data)
        handle.flush()
        return clip_video.probe(handle.name)


class OcdClipsCommon(OcdShopCommon):
    """A live of Brenda with products shown, its videos kept in a folder of the test."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = tempfile.mkdtemp(prefix="ocd_recordings_")
        cls.addClassCleanup(shutil.rmtree, cls.folder, ignore_errors=True)
        cls.startClassPatcher(patch.object(OcdLiveRecording, "_ocd_folder", lambda self: cls.folder))
        cls.company.write({
            "ocd_clip_max_seconds": 12, "ocd_clip_min_seconds": 6, "ocd_clip_before_seconds": 3,
            "ocd_clip_keep_days": 7, "ocd_clip_quality": "720", "ocd_clip_link_base": "https://ocdlive.com",
        })
        cls.brenda.write({"city": "Douala", "country_id": cls.env.ref("base.cm").id, "lang": "en_US"})
        cls.scarf = cls._product("Foulard", 3000, cls.brenda)
        cls.belt = cls._product("Ceinture", 4000, cls.brenda)
        for product in (cls.dress, cls.scarf, cls.belt):
            product.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        cls.Clip = cls.env["ocd.live.clip"]
        cls.Recording = cls.env["ocd.live.recording"]

    def _live(self, vendor=None, start=None, minutes=60):
        """A live of `vendor` that started an hour ago (written directly: no slot needed)."""
        vendor = vendor or self.brenda
        start = start or fields.Datetime.now() - timedelta(hours=2)
        self._slot = getattr(self, "_slot", 0) + 1
        later = self.company._ocd_local_today() + timedelta(days=40 + self._slot)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": vendor.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "studio",
        })
        booking.state = "confirmed"
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [start, start + timedelta(minutes=minutes), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        return booking

    def _moment(self, booking, product, seconds):
        return self.env["ocd.live.moment"].create({
            "booking_id": booking.id, "product_tmpl_id": product.product_tmpl_id.id, "product_id": product.id,
            "offset_seconds": seconds,
        })

    def _send(self, booking, data, name="live.mp4", piece=None):
        """Send the video `data` of `booking` in pieces, as the screen does."""
        part = self.Recording._ocd_start(booking, name, len(data))
        piece = piece or len(data)
        received = int(part.received)
        while received < len(data):
            received = part._ocd_write_piece(received, data[received:received + piece])
        return part

    def _run_cron(self):
        """The scheduled task, without its commits (forbidden in a test)."""
        with patch.object(self.env.registry["ir.cron"], "_commit_progress", return_value=float("inf")):
            self.Clip._cron_ocd_clips()
