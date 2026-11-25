"""The screen « Video of the live and clips » of the back office (client action ocd_clips.screen,
design ClipsAutomatiques): the video of the live sent in pieces, its parts and their shift, the
clips of the live with « See », « Make again » and « Hide »."""
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_datetime

from odoo.addons.ocd_live import media
from odoo.addons.ocd_live.tools import day_text

from .ocd_live_recording import CHUNK_BYTES, MAX_BYTES

# « − 5 s » and « + 5 s »
SHIFT_STEP = 5
TONES = {
    "queued": "wait", "processing": "wait", "ready": "ok", "failed": "bad", "skipped": "off", "deleted": "off",
    "uploading": "wait", "checking": "wait", "refused": "bad",
}


def size_text(env, size):
    """« 1,6 GB », « 700 MB »."""
    if size >= 1024 ** 3:
        return env._("%s GB", f"{size / 1024 ** 3:.1f}")
    return env._("%s MB", max(1, round(size / 1024 ** 2)))


def length_text(env, seconds):
    """« 1 h 02 », « 29 min », « 45 s »."""
    seconds = int(round(seconds or 0))
    if seconds >= 3600:
        return f"{seconds // 3600} h {seconds % 3600 // 60:02d}"
    if seconds >= 60:
        return env._("%s min", seconds // 60)
    return env._("%s s", seconds)


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    @api.model
    def _ocd_clips_check_team(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live sends the videos of the lives."))

    def _ocd_clips_line(self):
        """Where the video and the clips of the live stand, in a sentence (the control room)."""
        self.ensure_one()
        env = self.env
        parts = self.ocd_recording_ids.filtered(lambda part: part.state != "deleted")
        if not parts:
            if self.ocd_recording_ids:
                return env._("Video of the live deleted after its days; the clips stay.")
            return env._("No video yet: send it after the live, its clips are made from it.")
        sending = parts.filtered(lambda part: part.state == "uploading")
        if sending:
            percent = int(sum(sending.mapped("received")) * 100 / max(sum(sending.mapped("size")), 1))
            return env._("Video being sent: %s %%", percent)
        if parts.filtered(lambda part: part.state == "checking"):
            return env._("Video received, being checked.")
        clips = self.ocd_clip_ids
        ready = len(clips.filtered(lambda clip: clip.state == "ready"))
        waiting = len(clips.filtered(lambda clip: clip.state in ("queued", "processing")))
        if waiting:
            return env._("%(ready)s clips ready, %(waiting)s being made.", ready=ready, waiting=waiting)
        if parts.filtered(lambda part: part.state == "refused") and not ready:
            return env._("Video refused: send the video of the live in MP4 or MOV.")
        return env._("1 clip ready.") if ready == 1 else env._("%s clips ready.", ready)

    # === THE SCREEN === #

    def ocd_clips_screen_data(self):
        self._ocd_clips_check_team()
        self.ensure_one()
        booking = self.sudo()
        env = self.env
        company = booking.company_id or env.company
        start = company._ocd_to_local(booking.start_datetime)
        end = company._ocd_to_local(booking.end_datetime)
        vendor = booking.partner_id
        if booking.ocd_started_at:
            started = env._(
                "The live started at %s (« The live starts » touched in the control room): the moments count from there.",
                company._ocd_to_local(booking.ocd_started_at).strftime("%H:%M"),
            )
        else:
            started = env._(
                "« The live starts » was not touched in the control room: the moments count from the hour booked (%s).",
                start.strftime("%H:%M"),
            )
        first = booking.moment_ids.sorted(lambda moment: (moment.offset_seconds, moment.id))[:1]
        parts = booking.ocd_recording_ids.sorted("sequence")
        clips = booking.ocd_clip_ids.sorted(lambda clip: (clip.start, clip.id))
        return {
            "booking_id": booking.id,
            "title": " · ".join(part for part in (
                vendor.name, day_text(env, start.date(), "EEE d MMM"), f"{start:%H:%M} – {end:%H:%M}",
            ) if part),
            "off": vendor.ocd_clips_off,
            "can_send": booking.state in ("confirmed", "done") and not vendor.ocd_clips_off,
            "no_moment": not booking.moment_ids,
            "max_bytes": MAX_BYTES,
            "chunk_bytes": CHUNK_BYTES,
            "started": started,
            "parts": [booking._ocd_part_row(part) for part in parts],
            "preview": {
                "line": env._(
                    "The preview of the first moment (%(product)s, at %(time)s) plays again after each shift: "
                    "the product must be on screen at its first seconds.",
                    product=first.product_tmpl_id.name, time=first.offset_label,
                ),
            } if first and parts.filtered(lambda part: part.state == "ready") else False,
            "clips": [booking._ocd_clip_row(clip) for clip in clips],
            "busy": bool(parts.filtered(lambda part: part.state == "checking")
                         or clips.filtered(lambda clip: clip.state in ("queued", "processing"))),
            "note": env._(
                "The clips are made on the server, one live at a time (a few minutes for a live). The video of the "
                "live is deleted after %s days; the clips stay.", company.ocd_clip_keep_days,
            ),
            "updated_at": format_datetime(env, fields.Datetime.now(), tz=env.user.tz, dt_format="HH:mm"),
        }

    def _ocd_part_row(self, part):
        env = self.env
        states = dict(part._fields["state"]._description_selection(env))
        if part.state == "uploading":
            line = env._("%(received)s of %(size)s received: choose the same file to go on.",
                         received=size_text(env, part.received), size=size_text(env, part.size))
        elif part.state == "checking":
            line = env._("Received, being checked.") if media.can_convert() else env._(
                "Received: waits for ffmpeg, not installed on the server (pip install -r requirements.txt: imageio-ffmpeg)."
            )
        elif part.state == "refused":
            line = part.error or states["refused"]
        elif part.state == "deleted":
            line = env._("Deleted after its days: the clips stay.")
        else:
            checked = env._("image and sound checked") if part.has_sound else env._("image checked, no sound")
            line = " · ".join(filter(None, [checked, part.warning]))
        offset = part.offset_seconds
        if offset < 0:
            where = env._("The recording starts %s before the live", length_text(env, -offset))
        else:
            where = env._("Starts at %s of the live", self.env["ocd.live.moment"]._ocd_time_label(offset))
        return {
            "id": part.id,
            "sequence": part.sequence,
            "name": part.name,
            "state": part.state,
            "state_label": states.get(part.state, ""),
            "tone": TONES.get(part.state, "off"),
            "size": size_text(env, part.size),
            "length": length_text(env, part.duration) if part.duration else "",
            "line": line,
            "where": where,
            "offset": part.offset_seconds,
            "percent": int(part.received * 100 / part.size) if part.size else 0,
            "received": int(part.received),
            "total": int(part.size),
            "can_shift": part.state == "ready",
            "warning": bool(part.warning),
        }

    def _ocd_clip_row(self, clip):
        env = self.env
        states = dict(clip._fields["state"]._description_selection(env))
        reasons = dict(clip._fields["reason"]._description_selection(env))
        state = states.get(clip.state, "")
        if clip.hidden:
            state = env._("Hidden by the vendor") if clip.hidden_by == "vendor" else env._("Hidden by the team")
        why = ""
        if clip.state in ("failed", "skipped"):
            why = clip.error or reasons.get(clip.reason, "")
            if clip.state == "failed" and clip.tries > 1:
                why = env._("%(tries)s tries: %(why)s", tries=clip.tries, why=why)
        ready = clip.state == "ready"
        return {
            "id": clip.id,
            "product": clip.product_tmpl_id.name,
            "moment": clip._ocd_moment_text(),
            "length": clip._ocd_duration_text() if clip.duration and clip.state != "skipped" else "-",
            "state": clip.state,
            "state_label": state,
            "tone": "off" if clip.hidden else TONES.get(clip.state, "off"),
            "why": why,
            "plays": clip.play_count if ready else "-",
            "visits": clip.visit_count if ready else "-",
            "sales": clip.order_count if ready else "-",
            "video": clip._ocd_video_url() if ready else False,
            "poster": clip._ocd_poster_url() if ready else False,
            "link": clip._ocd_link_text(),
            "can_remake": clip.state in ("ready", "failed", "skipped", "deleted") and bool(
                clip._ocd_part() and clip._ocd_part()._ocd_has_file()
            ),
            "hidden": clip.hidden,
            "can_hide": ready,
        }

    # === WHAT THE SCREEN DOES === #

    def ocd_clips_start_upload(self, name, size):
        """A new part of the video (or the same one again, to go on): {id, token, received}."""
        self._ocd_clips_check_team()
        self.ensure_one()
        if self.partner_id.ocd_clips_off:
            raise UserError(self.env._("This vendor refuses the clips (« No clips » on their form)."))
        part = self.env["ocd.live.recording"].sudo()._ocd_start(self.sudo(), name, size)
        return {"id": part.id, "token": part.token, "received": int(part.received)}

    def ocd_clips_shift(self, part_id, seconds):
        """« − 5 s », « + 5 s » on a part: its clips are made again."""
        self._ocd_clips_check_team()
        self.ensure_one()
        part = self.sudo().ocd_recording_ids.filtered(lambda record: record.id == part_id and record.state == "ready")
        if not part:
            raise UserError(self.env._("This part of the video is no longer there."))
        step = SHIFT_STEP if seconds > 0 else -SHIFT_STEP
        part._ocd_shift(step)
        return self.ocd_clips_screen_data()

    def ocd_clips_remove_part(self, part_id):
        """Remove a part sent by mistake (or refused): its file is deleted, the clips planned again."""
        self._ocd_clips_check_team()
        self.ensure_one()
        part = self.sudo().ocd_recording_ids.filtered(lambda record: record.id == part_id)
        part.unlink()
        self.sudo()._ocd_plan_clips()
        return self.ocd_clips_screen_data()

    def ocd_clips_act(self, clip_id, what):
        """« Make again », « Hide », « Show » a clip of the live."""
        self._ocd_clips_check_team()
        self.ensure_one()
        clip = self.sudo().ocd_clip_ids.filtered(lambda record: record.id == clip_id)
        if not clip:
            raise UserError(self.env._("This clip is no longer there."))
        if what == "remake":
            clip.action_ocd_remake()
        elif what == "hide":
            clip.action_ocd_hide()
        elif what == "show":
            clip.action_ocd_show()
        return self.ocd_clips_screen_data()

    def ocd_clips_preview_info(self):
        """The seconds of the part shown by the preview: from a little before the first moment."""
        self.ensure_one()
        booking = self.sudo()
        first = booking.moment_ids.sorted(lambda moment: (moment.offset_seconds, moment.id))[:1]
        if not first:
            return False
        company = booking.company_id or self.env.company
        start = max(first.offset_seconds - company.ocd_clip_before_seconds, 0)
        part = booking.ocd_recording_ids.filtered(lambda record: record._ocd_contains(start))[:1] or \
            booking.ocd_recording_ids.filtered(lambda record: record.state == "ready")[:1]
        if not part or not part._ocd_has_file():
            return False
        return part, max(start - part.offset_seconds, 0)
