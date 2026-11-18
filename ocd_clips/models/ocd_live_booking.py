from datetime import timedelta

from odoo import api, fields, models


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    ocd_recording_ids = fields.One2many(comodel_name="ocd.live.recording", inverse_name="booking_id",
                                        string="Video Of The Live")
    ocd_clip_ids = fields.One2many(comodel_name="ocd.live.clip", inverse_name="booking_id", string="Clips")
    ocd_clip_count = fields.Integer(string="Clips Ready", compute="_compute_ocd_clip_count")
    ocd_clips_told_at = fields.Datetime(string="Clips Told At", readonly=True, copy=False,
                                        help="The vendor was told on WhatsApp that the clips of the live are ready.")

    def _compute_ocd_clip_count(self):
        groups = self.env["ocd.live.clip"]._read_group(
            [("booking_id", "in", self.ids), ("state", "=", "ready")], ["booking_id"], ["__count"],
        )
        counts = {booking.id: count for booking, count in groups}
        for booking in self:
            booking.ocd_clip_count = counts.get(booking.id, 0)

    # === THE CLIPS OF THE LIVE === #

    def _ocd_clip_plan(self):
        """The clips the live gives: [{moment, product, start, duration, reason}]. One clip per
        product: its moment with the most time before the next product; from a little before the
        moment (setting), 30 seconds at most, cut before the next product and at the end of the
        part of the video; « No clip » under the length at least (two products too close)."""
        self.ensure_one()
        company = self.company_id or self.env.company
        before, longest, shortest = (company.ocd_clip_before_seconds, company.ocd_clip_max_seconds,
                                     company.ocd_clip_min_seconds)
        moments = self.moment_ids.sorted(lambda moment: (moment.offset_seconds, moment.id))
        parts = self.ocd_recording_ids.filtered(lambda part: part.state == "ready")
        chosen = {}
        for index, moment in enumerate(moments):
            following = moments[index + 1] if index + 1 < len(moments) else None
            room = (following.offset_seconds - moment.offset_seconds) if following else longest + before
            best = chosen.get(moment.product_tmpl_id)
            if not best or room > best["room"]:
                chosen[moment.product_tmpl_id] = {"moment": moment, "room": room, "following": following}
        plan = []
        for product, item in chosen.items():
            moment, following = item["moment"], item["following"]
            start = max(moment.offset_seconds - before, 0)
            end = start + longest
            reason = False
            if following and following.offset_seconds - 1 < end:
                end = following.offset_seconds - 1
                reason = "too_close"
            part = parts.filtered(lambda part: part._ocd_contains(start))[:1]
            if not part:
                plan.append({"moment": moment, "product": product, "start": start, "duration": 0, "reason": "outside"})
                continue
            part_end = part.offset_seconds + part.duration
            if part_end < end:
                end = part_end
                reason = "outside"
            duration = round(end - start, 1)
            plan.append({
                "moment": moment, "product": product, "start": round(start, 1), "duration": duration,
                "reason": reason if duration < shortest else False,
            })
        return plan

    def _ocd_plan_clips(self):
        """Create or update the clips of the live from the video received and the moments: a clip
        keeps its short link (shared already), it is made again when its seconds change."""
        Clip = self.env["ocd.live.clip"].sudo()
        for booking in self:
            if booking.partner_id.ocd_clips_off or not booking.ocd_recording_ids.filtered(lambda part: part.state == "ready"):
                continue
            existing = {clip.product_tmpl_id: clip for clip in booking.ocd_clip_ids}
            for item in booking._ocd_clip_plan():
                values = {
                    "moment_id": item["moment"].id,
                    "product_id": item["moment"].product_id.id,
                    "start": item["start"],
                    "duration": item["duration"],
                }
                if item["reason"]:
                    values.update({"state": "skipped", "reason": item["reason"], "error_code": False})
                clip = existing.get(item["product"])
                if not clip:
                    Clip.create({
                        "booking_id": booking.id, "product_tmpl_id": item["product"].id,
                        "state": "queued", **values,
                    })
                    continue
                moved = abs(clip.start - item["start"]) > 0.4 or abs(clip.duration - item["duration"]) > 0.4
                if item["reason"]:
                    if clip.state != "skipped" or moved:
                        clip.write(values)
                elif moved or clip.state in ("skipped", "failed"):
                    clip.write({**values, "state": "queued", "tries": 0, "error_code": False, "reason": False})
            booking._ocd_clips_done()
        self.env["ocd.live.recording"]._ocd_trigger()

    def _ocd_clips_done(self):
        """When the clips of a live are all made (or not possible), the vendor is told once."""
        for booking in self:
            clips = booking.ocd_clip_ids
            if booking.ocd_clips_told_at or not clips or clips.filtered(lambda clip: clip.state in ("queued", "processing")):
                continue
            ready = clips.filtered(lambda clip: clip.state == "ready")
            if not ready:
                continue
            booking.ocd_clips_told_at = fields.Datetime.now()
            if self.env["ocd.automation"]._ocd_enabled("clips_ready"):
                booking._ocd_tell_clips_ready(ready)

    def _ocd_tell_clips_ready(self, clips):
        """Hook (ocd_clips_whatsapp): tell the vendor that the clips of the live are ready."""

    def action_ocd_open_clips(self):
        """The screen « Video of the live and clips » of the back office."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "ocd_clips.screen",
            "name": self.env._("Clips of %s", self.partner_id.name),
            "params": {"booking_id": self.id},
        }

    @api.model
    def _ocd_lives_without_video(self, days=3):
        """The lives of the last days with products shown and no video sent: « To do » of the team
        (from the day after the live)."""
        now = fields.Datetime.now()
        bookings = self.search([
            ("state", "in", ("confirmed", "done")), ("moment_ids", "!=", False),
            ("end_datetime", "<", now - timedelta(hours=12)), ("end_datetime", ">", now - timedelta(days=days)),
            ("partner_id.ocd_clips_off", "=", False),
        ], order="end_datetime")
        return bookings.filtered(lambda booking: not booking.ocd_recording_ids.filtered(
            lambda part: part.state in ("uploading", "checking", "ready", "deleted")
        ))
