import os
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.ocd_live import media

from .. import clip_video
from ..models import ocd_live_clip
from .common import OcdClipsCommon, make_video, probe


def fake_make(source, start, duration, info, overlay_png, end_png, quality="720"):
    """A clip made at once (the real ffmpeg is tested apart)."""
    return b"\x00\x00\x00\x18ftypmp42" + b"clip" * 64, None


@tagged("post_install", "-at_install")
class TestOcdClips(OcdClipsCommon):
    """The automatic clips (chantier 8, design ClipsAutomatiques): the video of a live sent in
    pieces and checked, the clips planned from the moments of the control room, made one after
    the other, their link, their sales, the cleaning."""

    def test_the_plan_of_the_clips_of_a_live(self):
        live = self._live()
        self._moment(live, self.dress, 10)
        self._moment(live, self.scarf, 22)
        self._moment(live, self.belt, 24)   # 2 s after the scarf: no clip of the scarf
        self._moment(live, self.dress, 40)  # shown again: the moment with the most room
        with patch.object(clip_video, "make", fake_make):
            self._send(live, make_video(60))
            self._run_cron()
        clips = {clip.product_tmpl_id: clip for clip in live.ocd_clip_ids}
        self.assertEqual(len(clips), 3, "One clip per product and per live")
        dress = clips[self.dress.product_tmpl_id]
        self.assertEqual((dress.start, dress.duration), (37, 12), "3 s before, 12 s at most (setting)")
        scarf = clips[self.scarf.product_tmpl_id]
        self.assertEqual((scarf.state, scarf.reason), ("skipped", "too_close"))
        belt = clips[self.belt.product_tmpl_id]
        self.assertEqual((belt.start, belt.duration), (21, 12), "Cut before the next product only when it comes")
        self.assertEqual(belt.state, "ready")
        self.assertNotEqual(dress.code, belt.code)
        self.assertFalse(set(dress.code) & set("01OIL"), "No letters that look alike")
        self.assertEqual(dress._ocd_link(), f"https://ocdlive.com/p/{dress.code}")
        self.assertEqual(dress._ocd_link_text(), f"ocdlive.com/p/{dress.code}")

    def test_a_real_clip_made_with_ffmpeg(self):
        """Horizontal video on a blur, vertical 720 x 1280, the sound of the live, the image."""
        live = self._live()
        self._moment(live, self.dress, 5)
        part = self._send(live, make_video(30), piece=64 * 1024)
        self.assertEqual(part.state, "checking")
        self._run_cron()
        self.assertEqual(part.state, "ready")
        self.assertTrue(part.has_sound)
        self.assertAlmostEqual(part.duration, 30, delta=0.5)
        self.assertEqual((part.width, part.height), (320, 180))
        clip = live.ocd_clip_ids
        self.assertEqual(clip.state, "ready", clip.error)
        info = probe(clip.video.content)
        self.assertEqual((info["width"], info["height"]), (720, 1280))
        self.assertAlmostEqual(info["duration"], 12, delta=0.6)
        self.assertTrue(info["sound"], "The sound of the live")
        self.assertTrue(clip.poster, "An image for the lists")
        self.assertEqual(clip.version, 1)
        self.assertTrue(live.ocd_clips_told_at, "The vendor is told once all are made")
        # The texts of the video, out of the zones covered by the apps
        texts = clip._ocd_texts()
        self.assertEqual(texts["link"], clip._ocd_link_text())
        self.assertEqual(texts["by"], "Brenda Wax · Douala")

    def test_the_video_is_sent_in_pieces_and_goes_on_after_a_cut(self):
        live = self._live()
        data = b"x" * 1000
        part = self.Recording._ocd_start(live, "live.mp4", len(data))
        self.assertEqual(part._ocd_write_piece(0, data[:300]), 300)
        self.assertEqual(part._ocd_write_piece(0, data[:300]), 300, "A piece sent again changes nothing")
        self.assertEqual(part._ocd_write_piece(600, data[600:900]), 300, "Not the next piece: the browser goes on from 300")
        # The page closed: the same file chosen again goes on where it stopped
        again = self.Recording._ocd_start(live, "live.mp4", len(data))
        self.assertEqual(again, part)
        self.assertEqual(again.received, 300)
        self.assertEqual(part._ocd_write_piece(300, data[300:]), 1000)
        self.assertEqual(part.state, "checking")
        self.assertEqual(os.path.getsize(part._ocd_path()), 1000)
        # Not a video: refused, its file deleted
        self._run_cron()
        self.assertEqual(part.state, "refused")
        self.assertIn("MP4 or MOV", part.error)
        self.assertFalse(os.path.exists(part._ocd_path()))
        # Without ffmpeg, a video waits (the settings and the screen say why)
        other = self._send(live, b"y" * 100, name="other.mp4")
        with patch.object(media, "can_convert", return_value=False):
            self._run_cron()
            self.assertEqual(other.state, "checking")
            self.assertIn("waits for ffmpeg", live.ocd_clips_screen_data()["parts"][-1]["line"])
        with self.assertRaises(UserError):
            self.Recording._ocd_start(live, "empty.mp4", 0)
        with self.assertRaises(UserError):
            self.Recording._ocd_start(live, "huge.mp4", 5 * 1024 ** 3)

    def test_the_parts_the_shift_and_the_warnings(self):
        live = self._live()
        self._moment(live, self.dress, 8)
        self._moment(live, self.scarf, 50)
        with patch.object(clip_video, "make", fake_make):
            first = self._send(live, make_video(30, sound=False), name="part1.mp4")
            self._run_cron()
            self.assertIn("no sound", first.warning)
            scarf = live.ocd_clip_ids.filtered(lambda clip: clip.product_tmpl_id == self.scarf.product_tmpl_id)
            self.assertEqual((scarf.state, scarf.reason), ("skipped", "outside"), "Not in the video yet")
            second = self._send(live, make_video(30), name="part2.mp4")
            self._run_cron()
            self.assertAlmostEqual(second.offset_seconds, 30, delta=0.5, msg="The next part starts where the first ends")
            self.assertEqual(scarf.state, "ready", "Made from the second part")
            dress = live.ocd_clip_ids.filtered(lambda clip: clip.product_tmpl_id == self.dress.product_tmpl_id)
            self.assertEqual(dress.state, "ready")
            # « + 5 s »: the recording starts later in the live, its clips are made again
            first._ocd_shift(5)
            self.assertEqual(first.offset_seconds, 5)
            self.assertEqual(dress.state, "queued")
            self.assertEqual(scarf.state, "ready", "The clips of the other part stay")
            self._run_cron()
            self.assertEqual(dress.state, "ready")
            self.assertEqual(dress.version, 2, "A new address for the CDN")
            data = live.ocd_clips_screen_data()
            self.assertEqual([row["sequence"] for row in data["parts"]], [1, 2])
            self.assertEqual(len(data["clips"]), 2)
            data = live.ocd_clips_shift(first.id, -5)
            self.assertEqual(first.offset_seconds, 0)

    def test_a_failed_clip_is_tried_three_times_then_says_why(self):
        live = self._live()
        self._moment(live, self.dress, 5)

        def broken(*args, **kwargs):
            raise clip_video.ClipError("ffmpeg")

        with patch.object(clip_video, "make", broken):
            self._send(live, make_video(20))
            self._run_cron()
            clip = live.ocd_clip_ids
            self.assertEqual((clip.state, clip.tries), ("queued", 1), "Tried again by the next run")
            self._run_cron()
            self._run_cron()
        self.assertEqual((clip.state, clip.tries, clip.reason), ("failed", 3, "failed"))
        self.assertIn("ffmpeg", clip.error)
        self.assertFalse(live.ocd_clips_told_at, "Nothing ready: the vendor is not told")
        # An error nobody expected: noted on the clip, the others go on
        clip.write({"state": "queued", "tries": 0})
        with patch.object(clip_video, "overlay", side_effect=OSError("disk full")), \
                mute_logger("odoo.addons.ocd_clips.models.ocd_live_clip"):
            self._run_cron()
        self.assertEqual((clip.state, clip.tries), ("queued", 1))
        self.assertIn("disk full", clip.error)
        # A clip taken by a worker that stopped is made again, its try counted
        clip.write({"state": "processing", "processing_since": fields.Datetime.now() - timedelta(hours=1)})
        with patch.object(clip_video, "make", fake_make):
            self._run_cron()
        self.assertEqual((clip.state, clip.tries), ("ready", 2))
        self.assertTrue(live.ocd_clips_told_at)
        # « Make again » from the screen
        live.ocd_clips_act(clip.id, "remake")
        self.assertEqual((clip.state, clip.tries), ("queued", 0))

    def test_the_vendor_is_told_once_and_no_clips_when_refused(self):
        live = self._live()
        self._moment(live, self.dress, 5)
        told = []
        booking_class = type(self.env["ocd.live.booking"])
        with patch.object(clip_video, "make", fake_make), \
                patch.object(booking_class, "_ocd_tell_clips_ready", lambda self, clips: told.append(clips)):
            self._send(live, make_video(20))
            self._run_cron()
            live.ocd_clip_ids.action_ocd_remake()
            self._run_cron()
        self.assertEqual(len(told), 1, "Once per live")
        # « No clips »: none planned, the live not in « To do »
        other = self._live(vendor=self.fatou)
        self._moment(other, self.butter, 5)
        self.fatou.ocd_clips_off = True
        self.assertNotIn(other, self.env["ocd.live.booking"]._ocd_lives_without_video())
        with patch.object(clip_video, "make", fake_make):
            self._send(other, make_video(20))
            self._run_cron()
        self.assertFalse(other.ocd_clip_ids)

    def test_the_lives_without_video_in_to_do(self):
        live = self._live(start=fields.Datetime.now() - timedelta(days=1, hours=2))
        self._moment(live, self.dress, 5)
        self.assertIn(live, self.env["ocd.live.booking"]._ocd_lives_without_video())
        todos = self.env["ocd.live.dashboard"]._ocd_todos()
        self.assertIn(f"clips_video_{live.id}", [todo["key"] for todo in todos])
        self.env.ref("ocd_clips.automation_clips_video_missing").enabled = False
        todos = self.env["ocd.live.dashboard"]._ocd_todos()
        self.assertNotIn(f"clips_video_{live.id}", [todo["key"] for todo in todos], "Paused by the team")

    def test_the_cleaning_of_the_videos_and_the_clips(self):
        live = self._live()
        self._moment(live, self.dress, 5)
        with patch.object(clip_video, "make", fake_make):
            part = self._send(live, make_video(20))
            self._run_cron()
        clip = live.ocd_clip_ids
        self.assertTrue(os.path.exists(part._ocd_path()))
        part.delete_after = fields.Datetime.now() - timedelta(minutes=1)
        abandoned = self.Recording._ocd_start(live, "other.mp4", 5000)
        self.env.flush_all()
        self.env.cr.execute("UPDATE ocd_live_recording SET write_date = %s WHERE id = %s",
                            [fields.Datetime.now() - timedelta(days=2), abandoned.id])
        abandoned.invalidate_recordset()
        self._run_cron()
        self.assertEqual(part.state, "deleted")
        self.assertFalse(os.path.exists(part._ocd_path()))
        self.assertFalse(abandoned.exists(), "A video not sent to its end is forgotten after a day")
        # A file left without its part (its live deleted by the database) goes after a day
        orphan = os.path.join(self.folder, "999999.video")
        with open(orphan, "wb") as handle:
            handle.write(b"x")
        self.Recording._ocd_remove_orphans()
        self.assertTrue(os.path.exists(orphan), "A day old only")
        old = fields.Datetime.now().timestamp() - 2 * 86400
        os.utime(orphan, (old, old))
        self.Recording._ocd_remove_orphans()
        self.assertFalse(os.path.exists(orphan))
        self.assertEqual(clip.state, "ready", "The clips stay")
        # The product taken off sale for 3 months: the video of its clip goes, the link stays
        self.dress.product_tmpl_id._ocd_vendor_retire()
        self.env.flush_all()
        self.env.cr.execute("UPDATE product_template SET write_date = %s WHERE id = %s",
                            [fields.Datetime.now() - timedelta(days=100), self.dress.product_tmpl_id.id])
        self.dress.product_tmpl_id.invalidate_recordset()
        self._run_cron()
        self.assertEqual(clip.state, "deleted")
        self.assertFalse(clip.video)
        self.assertEqual(clip._ocd_target_url(), f"/ocd/boutique/{self.brenda.id}")

    def test_the_sales_of_a_clip_in_the_seven_days(self):
        live = self._live()
        self._moment(live, self.dress, 5)
        with patch.object(clip_video, "make", fake_make):
            self._send(live, make_video(20))
            self._run_cron()
        clip = live.ocd_clip_ids
        now = fields.Datetime.now()
        order = self.env["sale.order"].create({
            "partner_id": self.estelle.id,
            "order_line": [(0, 0, {"product_id": self.dress.id, "product_uom_qty": 1, "tax_ids": [(5,)]}),
                           (0, 0, {"product_id": self.butter.id, "product_uom_qty": 1, "tax_ids": [(5,)]})],
        })
        order._ocd_note_clips({str(clip.id): (now - timedelta(days=2)).isoformat()})
        order.action_confirm()
        dress_line = order.order_line.filtered(lambda line: line.product_id == self.dress)
        self.assertEqual(dress_line.ocd_clip_id, clip)
        self.assertFalse((order.order_line - dress_line).ocd_clip_id, "Only the product of the clip")
        clip.invalidate_recordset(["order_count"])
        self.assertEqual(clip.order_count, 1)
        self.assertEqual(clip._ocd_sales(), (1, 12000))
        # A visit of more than 7 days: no longer counts
        late = self.env["sale.order"].create({
            "partner_id": self.estelle.id,
            "order_line": [(0, 0, {"product_id": self.dress.id, "product_uom_qty": 1, "tax_ids": [(5,)]})],
        })
        late._ocd_note_clips({str(clip.id): (now - timedelta(days=8)).isoformat()})
        late.action_confirm()
        self.assertFalse(late.order_line.ocd_clip_id)

    def test_the_share_text_has_the_price_of_now(self):
        live = self._live()
        self._moment(live, self.dress, 5)
        with patch.object(clip_video, "make", fake_make):
            self._send(live, make_video(20))
            self._run_cron()
        clip = live.ocd_clip_ids
        text = clip._ocd_share_text()
        self.assertIn("Robe en wax", text)
        self.assertIn("at Brenda Wax", text)
        self.assertIn(clip._ocd_link_text(), text)
        self.assertIn("you pay at the door", text, "Sold by OCD")
        self.dress.product_tmpl_id.list_price = 15000
        self.assertIn("15", clip._ocd_share_text())
        # The video of the card of the vendor in the feed
        self.brenda._ocd_card_video_from_clip(clip)
        self.assertEqual(self.brenda.ocd_card_media, "video")
        self.assertEqual(self.brenda.ocd_card_video_name, f"{clip.code}.mp4")
        self.assertFalse(self.brenda.ocd_card_video_pending, "Already readable by every phone")

    def test_whatsapp_a_few_a_day_and_the_settings(self):
        live = self._live()
        self._moment(live, self.dress, 5)
        with patch.object(clip_video, "make", fake_make):
            self._send(live, make_video(20))
            self._run_cron()
        clip = live.ocd_clip_ids
        self.assertFalse(clip._ocd_send_to_vendor(), "No WhatsApp without ocd_clips_whatsapp")
        clip_class = type(clip)
        self.company.ocd_clip_whatsapp_per_day = 2
        with patch.object(clip_class, "_ocd_whatsapp_ready", lambda self: True), \
                patch.object(clip_class, "_ocd_whatsapp_clip", lambda self: True):
            self.assertTrue(clip._ocd_send_to_vendor())
            self.assertTrue(clip._ocd_send_to_vendor())
            self.assertFalse(clip._ocd_send_to_vendor(), "2 a day at most (setting)")
        # The settings of the clips on the page of OCD Live
        Settings = self.env["ocd.live.settings"]
        page = Settings.get_settings_page()
        section = next(section for section in page["sections"] if section["key"] == "clips")
        self.assertIn("ocd_clip_link_base", [item["key"] for item in section["items"]])
        result = Settings.save_settings_page({"ocd_clip_link_base": "ocdlive.com"})
        self.assertFalse(result["ok"])
        self.assertIn("ocd_clip_link_base", result["errors"])
        result = Settings.save_settings_page({"ocd_clip_link_base": "https://ocd.live", "ocd_clip_max_seconds": 30})
        self.assertTrue(result["ok"], result)
        self.assertEqual(clip._ocd_link(), f"https://ocd.live/p/{clip.code}")
        with self.assertRaises(ValidationError):
            self.company.ocd_clip_min_seconds = 45

    def test_the_letters_of_the_codes(self):
        self.assertFalse(set(ocd_live_clip.CODE_LETTERS) & set("01OIL"))
        codes = {self.Clip._ocd_new_code() for _index in range(50)}
        self.assertEqual(len(codes), 50)
