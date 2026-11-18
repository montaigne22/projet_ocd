"""The video of a live, sent by the team after the live (chantier 8, design ClipsAutomatiques): the
recording of the studio, or the video downloaded from the account of OCD Live (TikTok, Facebook
and YouTube give it to their owner). Sent in pieces (it starts again where it stopped when the
network cuts), checked when it arrives (readable, image and sound, its length), kept a few days
(setting) to make the clips, then deleted: the clips stay.

A live may come in several parts (the studio that starts again, TikTok that cuts every hour):
each part says where it starts in the live (`offset_seconds`, from the real start of the live).

The files are kept out of the database and of its files (they are not saved in the backups):
in the folder `ocd_recordings_path` of the configuration of the server, else in
<data_dir>/ocd_recordings/<database>. A folder on an object storage (S3, R2) mounted on the
server works the same."""
import logging
import os
import secrets
import shutil
from datetime import timedelta

from odoo import api, fields, models, tools as odoo_tools
from odoo.exceptions import UserError

from .. import clip_video

_logger = logging.getLogger(__name__)

# A video of a live at most (4 GB)
MAX_BYTES = 4 * 1024 ** 3
# The pieces of a video sent (the browser cuts the file)
CHUNK_BYTES = 8 * 1024 ** 2
# Kept free on the disk besides a video sent
SPARE_BYTES = 1024 ** 3
# A video not sent to its end is forgotten after this
ABANDONED_HOURS = 24
STATES = [
    ("uploading", "Being Sent"),
    ("checking", "Being Checked"),
    ("ready", "Ready"),
    ("refused", "Refused"),
    ("deleted", "Deleted"),
]


class OcdLiveRecording(models.Model):
    _name = "ocd.live.recording"
    _description = "Video Of A Live"
    _order = "booking_id, sequence, id"

    booking_id = fields.Many2one(comodel_name="ocd.live.booking", string="Live", required=True, index=True,
                                 ondelete="cascade")
    company_id = fields.Many2one(related="booking_id.company_id", store=True)
    sequence = fields.Integer(string="Part", default=1)
    name = fields.Char(string="File", required=True)
    state = fields.Selection(selection=STATES, required=True, default="uploading", index=True)
    size = fields.Float(string="Size (Bytes)", digits=(16, 0), required=True)
    received = fields.Float(string="Received (Bytes)", digits=(16, 0), default=0)
    token = fields.Char(copy=False, groups="ocd_live.group_ocd_live_user")
    offset_seconds = fields.Float(
        string="Starts At (Seconds Of The Live)", digits=(16, 1), default=0,
        help="Where this part starts in the live, from its real start. Negative: the recording "
        "started before the live.",
    )
    duration = fields.Float(string="Length (Seconds)", digits=(16, 1), readonly=True)
    width = fields.Integer(readonly=True)
    height = fields.Integer(readonly=True)
    has_sound = fields.Boolean(string="Sound", readonly=True)
    warning = fields.Char(readonly=True, help="Something to check, the clips are made all the same.")
    error = fields.Char(readonly=True)
    user_id = fields.Many2one(comodel_name="res.users", string="Sent By", default=lambda self: self.env.user,
                              readonly=True)
    received_at = fields.Datetime(string="Received At", readonly=True)
    delete_after = fields.Datetime(string="Deleted After", readonly=True)

    # === FILES === #

    @api.model
    def _ocd_folder(self):
        folder = odoo_tools.config.get("ocd_recordings_path") or os.path.join(
            odoo_tools.config["data_dir"], "ocd_recordings", self.env.cr.dbname
        )
        os.makedirs(folder, exist_ok=True)
        return folder

    def _ocd_path(self):
        self.ensure_one()
        return os.path.join(self._ocd_folder(), f"{self.id}.video")

    def _ocd_has_file(self):
        self.ensure_one()
        return self.state in ("checking", "ready") and os.path.exists(self._ocd_path())

    @api.model
    def _ocd_free_bytes(self):
        return shutil.disk_usage(self._ocd_folder()).free

    def unlink(self):
        paths = [record._ocd_path() for record in self]
        result = super().unlink()
        for path in paths:
            self._ocd_remove(path)
        return result

    @api.model
    def _ocd_remove(self, path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError:
            _logger.warning("OCD Live: video of a live not removed: %s", path, exc_info=True)

    # === SENDING === #

    @api.model
    def _ocd_start(self, booking, name, size):
        """A new part of the video of `booking`, or the same one again when it was not sent to
        its end (the same file chosen again after closing the page): it goes on from there."""
        booking.ensure_one()
        size = int(size or 0)
        name = os.path.basename(str(name or "video"))[:120] or "video"
        if booking.state not in ("confirmed", "done"):
            raise UserError(self.env._("The live is not confirmed."))
        if size <= 0:
            raise UserError(self.env._("This file is empty."))
        if size > MAX_BYTES:
            raise UserError(self.env._("The video is too heavy: %s GB at most.", MAX_BYTES // 1024 ** 3))
        same = booking.ocd_recording_ids.filtered(
            lambda part: part.state == "uploading" and part.name == name and int(part.size) == size
        )[:1]
        if same:
            return same
        if self._ocd_free_bytes() < size + SPARE_BYTES:
            raise UserError(self.env._(
                "Not enough space on the server for this video: %(free)s GB free, %(size)s GB needed.",
                free=round(self._ocd_free_bytes() / 1024 ** 3, 1), size=round((size + SPARE_BYTES) / 1024 ** 3, 1),
            ))
        last = booking.ocd_recording_ids.filtered(lambda part: part.state != "deleted").sorted("sequence")[-1:]
        recording = self.create({
            "booking_id": booking.id,
            "sequence": (last.sequence + 1) if last else 1,
            "name": name,
            "size": size,
            "token": secrets.token_urlsafe(24),
        })
        with open(recording._ocd_path(), "wb"):
            pass
        return recording

    def _ocd_write_piece(self, offset, data):
        """Write a piece of the file at `offset`; return the bytes received so far. A piece
        already received (sent again after a cut) or not the next one changes nothing: the
        browser goes on from what is returned."""
        self.ensure_one()
        if self.state != "uploading":
            return int(self.received)
        path = self._ocd_path()
        current = os.path.getsize(path) if os.path.exists(path) else 0
        if int(offset) != current or not data or len(data) > CHUNK_BYTES or current + len(data) > self.size:
            if current != int(self.received):
                self.received = current
            return current
        with open(path, "ab") as handle:
            handle.write(data)
        received = current + len(data)
        values = {"received": received}
        if received >= self.size:
            values.update({"state": "checking", "received_at": fields.Datetime.now()})
        self.write(values)
        if received >= self.size:
            self._ocd_trigger()
        return received

    @api.model
    def _ocd_trigger(self):
        cron = self.env.ref("ocd_clips.ir_cron_clips", raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()

    # === CHECK === #

    def _ocd_check(self):
        """Check a video received: readable, with an image; its length and its sound. Then the
        clips of the live are planned."""
        for recording in self.filtered(lambda part: part.state == "checking"):
            company = recording.company_id or self.env.company
            try:
                info = clip_video.probe(recording._ocd_path())
            except clip_video.ClipError:
                recording.write({"state": "refused", "error": self.env._(
                    "This file cannot be read as a video: send the video of the live in MP4 or MOV."
                )})
                recording._ocd_remove(recording._ocd_path())
                continue
            values = {
                "state": "ready",
                "duration": info["duration"],
                "width": info["width"],
                "height": info["height"],
                "has_sound": info["sound"],
                "error": False,
                "delete_after": fields.Datetime.now() + timedelta(days=company.ocd_clip_keep_days),
            }
            before = recording.booking_id.ocd_recording_ids.filtered(
                lambda part: part.sequence < recording.sequence and part.state in ("ready", "deleted") and part.duration
            ).sorted("sequence")[-1:]
            if before and not recording.offset_seconds:
                values["offset_seconds"] = before.offset_seconds + before.duration
            recording.write(values)
            recording.warning = recording._ocd_warning()
            recording.booking_id._ocd_plan_clips()

    def _ocd_warning(self):
        """What the team should look at, in a sentence: no sound, a video shorter than the moments."""
        self.ensure_one()
        env = self.env
        Moment = env["ocd.live.moment"]
        if not self.has_sound:
            return env._("The video has no sound: the clips will be silent.")
        booking = self.booking_id
        parts = booking.ocd_recording_ids.filtered(lambda part: part.state in ("ready", "deleted") and part.duration)
        end = max((part.offset_seconds + part.duration for part in parts), default=0)
        last = max(booking.moment_ids.mapped("offset_seconds") or [0])
        if last > end:
            return env._(
                "The video lasts %(video)s, the last moment is at %(moment)s: check the shift, or send the next part.",
                video=Moment._ocd_time_label(end), moment=Moment._ocd_time_label(last),
            )
        return False

    def _ocd_contains(self, start, duration=0):
        """Whether this part holds the seconds of the live from `start` (for `duration`)."""
        self.ensure_one()
        return self.state == "ready" and self.offset_seconds <= start and start + duration <= self.offset_seconds + self.duration

    def _ocd_shift(self, seconds):
        """Move this part by `seconds` in the live (« − 5 s », « + 5 s »): its clips are made again."""
        for recording in self:
            recording.offset_seconds = round(recording.offset_seconds + seconds, 1)
            recording.warning = recording._ocd_warning() if recording.state == "ready" else recording.warning
            recording.booking_id._ocd_plan_clips()

    # === CLEANING === #

    @api.model
    def _ocd_clean(self):
        """The videos past their days are deleted (the clips stay); a video not sent to its end
        is forgotten after a day."""
        now = fields.Datetime.now()
        for recording in self.sudo().search([("state", "in", ("ready", "refused")), ("delete_after", "<=", now)]):
            recording._ocd_remove(recording._ocd_path())
            recording.state = "deleted"
        for recording in self.sudo().search([("state", "=", "refused"), ("delete_after", "=", False)]):
            recording.delete_after = now + timedelta(days=1)
        self.sudo().search([
            ("state", "=", "uploading"), ("write_date", "<", now - timedelta(hours=ABANDONED_HOURS)),
        ]).unlink()
