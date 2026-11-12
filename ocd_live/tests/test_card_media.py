import io
import re
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import BinaryBytes
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.ocd_live import media


def png(colour="orange", size=(40, 50)):
    output = io.BytesIO()
    Image.new("RGB", size, colour).save(output, format="PNG")
    return output.getvalue()


def clip(seconds=2, sound=False, size="160x284"):
    """A short video filmed upright, as a phone sends it (QuickTime)."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "clip.mov"
        command = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=10:duration={seconds}"]
        if sound:
            command += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
        command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(path)]
        subprocess.run(command, check=True, capture_output=True, timeout=120)
        return path.read_bytes()


@tagged("post_install", "-at_install")
class TestOcdLiveCardMedia(TransactionCase):
    """The card of a vendor in the feed: a short video, an image, else its initials (the shop
    adds the carousel of its products)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({
            "name": "Afi Pagnes", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id,
        })

    def test_media_in_their_order(self):
        vendor = self.vendor
        self.assertEqual(vendor._ocd_card_media(), {"kind": "initials"}, "Nothing yet: its initials")
        vendor.image_1920 = BinaryBytes(png())
        self.assertEqual(vendor._ocd_card_media(), {"kind": "image", "image": f"/lives/image/{vendor.id}"})
        vendor.ocd_card_image = BinaryBytes(png("green"))
        image = vendor._ocd_card_media()["image"]
        self.assertTrue(image.startswith(f"/lives/carte/{vendor.id}?v="), "The image chosen for the card")
        vendor.ocd_card_media = "video"
        self.assertEqual(vendor._ocd_card_media()["kind"], "image", "No video yet: the next one")
        self.assertEqual(vendor._ocd_card_shown_label(), "Your image")
        choices = {row["value"]: row for row in vendor._ocd_card_choices()}
        self.assertFalse(choices["video"]["ready"])
        self.assertTrue(choices["image"]["ready"])

    def test_video_made_readable_by_every_phone(self):
        if not media.can_convert():
            self.skipTest("ffmpeg is not installed")
        vendor = self.vendor
        vendor.write({"ocd_card_video": BinaryBytes(clip(sound=True), filename="mon live.mov")})
        self.assertEqual(vendor.ocd_card_video_name, "mon live.mp4")
        self.assertEqual(guess_mimetype(vendor.ocd_card_video.content), "video/mp4")
        self.assertTrue(vendor.ocd_card_video_poster, "Its first image, shown until it plays")
        self.assertTrue(vendor.ocd_card_video_sound)
        card = vendor._ocd_card_media()
        self.assertEqual(card["kind"], "video", "Automatic: the video first")
        self.assertEqual(card["poster"].split("?")[0], f"/lives/video/{vendor.id}/image")
        self.assertTrue(card["sound"])
        vendor.ocd_card_video = BinaryBytes(clip(seconds=1), filename="silence.mov")
        self.assertFalse(vendor.ocd_card_video_sound, "Without sound: no button for it")
        vendor.ocd_card_video = False
        self.assertFalse(vendor.ocd_card_video_poster, "Removed with its poster")
        self.assertEqual(vendor._ocd_card_media(), {"kind": "initials"})

    def test_video_refused(self):
        with self.assertRaisesRegex(UserError, "not a video"):
            self.vendor.ocd_card_video = BinaryBytes(b"Hello, this is a text and not a video at all.")
        with patch.object(media, "MAX_UPLOAD_MB", 0.0001), self.assertRaisesRegex(UserError, "too heavy"):
            self.vendor.ocd_card_video = BinaryBytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 400)
        if media.can_convert():
            with self.assertRaisesRegex(UserError, "too long"):
                self.vendor.ocd_card_video = BinaryBytes(clip(seconds=125, size="64x64"))
        self.assertFalse(self.vendor.ocd_card_video)

    def test_without_ffmpeg_mp4_kept_as_it_is(self):
        video = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 400
        with patch.object(media, "can_convert", return_value=False):
            self.assertEqual(media.prepare(video), (video, None, "video/mp4", None))
            with self.assertRaises(media.VideoError) as error:
                media.prepare(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 400)
        self.assertEqual(error.exception.code, "format", "A QuickTime video would not play everywhere")


@tagged("post_install", "-at_install")
class TestOcdLiveCardPages(HttpCase):
    """The media of the cards on the website, and the page « My card in the lives »."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({"ocd_studio_tz": "Africa/Lome", "ocd_booking_open_date": False})
        cls.vendor = cls.env["res.partner"].create({
            "name": "Afi Pagnes", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id, "phone": "+228 90 00 00 71",
            "ocd_card_image": BinaryBytes(png()), "ocd_card_media": "image",
        })

    def test_media_of_the_cards(self):
        vendor = self.vendor
        response = self.url_open(f"/lives/carte/{vendor.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/png")
        self.assertEqual(self.url_open(f"/lives/video/{vendor.id}").status_code, 404, "No video")
        if media.can_convert():
            vendor.ocd_card_video = BinaryBytes(clip(), filename="clip.mov")
            whole = self.url_open(f"/lives/video/{vendor.id}")
            self.assertEqual(whole.headers["Content-Type"], "video/mp4")
            part = self.url_open(f"/lives/video/{vendor.id}", headers={"Range": "bytes=0-99"})
            self.assertEqual(part.status_code, 206, "The phones ask the video by parts")
            self.assertEqual(len(part.content), 100)
            self.assertEqual(self.url_open(f"/lives/video/{vendor.id}/image").status_code, 200)
        vendor.ocd_vendor_state = "to_check"
        self.assertEqual(self.url_open(f"/lives/carte/{vendor.id}").status_code, 404, "Not approved")

    def test_card_of_the_feed(self):
        product = self.env.ref("ocd_live.product_package_discovery").product_variant_id
        day = fields.Date.today() + timedelta(days=5)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": self.vendor.id, "start_datetime": self.env.company._ocd_slot_starts(day)[2],
            "slot_count": 1, "product_id": product.id, "state": "confirmed",
        })
        html = self.url_open("/lives?pays=tg").text
        card = re.search(rf'data-key="n{booking.id}".*?</article>', html, re.S).group(0)
        self.assertIn("o_ocd_feed_media_image", card)
        self.assertIn(f"/lives/carte/{self.vendor.id}", card)
        self.assertIn("o_ocd_feed_name", card)

    def test_my_card_page(self):
        self.authenticate(None, None)
        self.assertIn("/ocd/connexion", self.url_open("/ocd/espace/moi/carte").url, "Logged in vendors only")
        self.url_open(f"/ocd/espace/{self.vendor._ocd_get_space_token()}")
        response = self.url_open("/ocd/espace/moi/carte")
        self.assertEqual(response.status_code, 200)
        self.assertIn("o_ocd_card_preview", response.text, "The card as the feed shows it")
        self.assertIn('value="image" checked', response.text)
        response = self.url_open("/ocd/espace/moi/carte", data={
            "csrf_token": self.csrf_token(), "choice": "video",
        }, files={"image": ("photo.png", png("blue"), "image/png")})
        self.assertIn("enregistre=1", response.url)
        self.assertEqual(self.vendor.ocd_card_media, "video")
        self.assertIn("Until then, your card shows your image. Add your video below.", self.url_open("/ocd/espace/moi/carte").text)
        response = self.url_open("/ocd/espace/moi/carte", data={
            "csrf_token": self.csrf_token(), "choice": "video",
        }, files={"video": ("clip.mov", b"not a video", "video/quicktime")})
        self.assertIn("This file is not a video.", response.text, "Said next to the field")
        self.assertIn("changed their card in the lives", self.vendor.message_ids[0].body, "The team sees it")
