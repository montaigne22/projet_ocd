import io
from unittest.mock import patch

from PIL import Image

from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from .. import clip_video
from .common import OcdClipsCommon, make_video
from .test_clips import fake_make

PHONE = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0 Mobile Safari/537.36"}


def jpeg():
    output = io.BytesIO()
    Image.new("RGB", (36, 64), "orange").save(output, format="JPEG")
    return output.getvalue()


@tagged("post_install", "-at_install")
class TestOcdClipPages(HttpCase, OcdClipsCommon):
    """The clips on the site: the short link and its sales, the product page and the replay, the
    space of the vendor, the video sent by the team."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        cls.brenda.phone = "+237 670000001"

    def setUp(self):
        super().setUp()
        self.live = self._live()
        self._moment(self.live, self.dress, 5)
        with patch.object(clip_video, "make", fake_make):
            self._send(self.live, make_video(20))
            self._run_cron()
        self.clip = self.live.ocd_clip_ids
        self.clip.poster = BinaryBytes(jpeg())
        self.assertEqual(self.clip.state, "ready")
        self.Count = self.env["ocd.vendor.count"]

    def _visits(self):
        return self.Count._ocd_record_totals(self.brenda, "clip_visit", [self.clip.id]).get(self.clip.id, 0)

    def _vendor_login(self, vendor=None):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{(vendor or self.brenda)._ocd_get_space_token()}")

    def _post(self, url, **data):
        return self.url_open(url, data={"csrf_token": self.csrf_token(), **data}, allow_redirects=False)

    def test_the_short_link_one_visit_a_day_without_the_robots(self):
        url = f"/p/{self.clip.code}"
        response = self.url_open(url, headers={"User-Agent": "WhatsApp/2.24.1 A"}, allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith(self.dress.product_tmpl_id.website_url))
        self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex")
        self.assertEqual(self._visits(), 0, "The preview of WhatsApp is not a visit")
        self.url_open(url, headers=PHONE, allow_redirects=False)
        self.url_open(url.lower(), headers=PHONE, allow_redirects=False)
        self.assertEqual(self._visits(), 1, "One visit per phone and per day")
        # Unknown, product taken off sale: never an error
        response = self.url_open("/p/ZZZZZZ", headers=PHONE, allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith("/shop"))
        self.dress.product_tmpl_id._ocd_vendor_retire()
        response = self.url_open(url, headers=PHONE, allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith(f"/ocd/boutique/{self.brenda.id}"))
        self.assertIn("Disallow: /p/", self.url_open("/robots.txt").text)

    def test_the_sale_by_the_short_link(self):
        self.authenticate(None, None)
        self.url_open(f"/p/{self.clip.code}", headers=PHONE)
        self.url_open("/ocd/panier/ajouter", data={
            "csrf_token": self.csrf_token(), "product_template_id": self.dress.product_tmpl_id.id, "quantity": 1,
        }, headers=PHONE, allow_redirects=False)
        order = self.env["sale.order"].search([("order_line.product_id", "=", self.dress.id)], order="id desc", limit=1)
        self.assertIn(str(self.clip.id), order.ocd_clip_visits or {}, "The cart remembers the clip")
        order.order_line.tax_ids = False
        order.action_confirm()
        self.assertEqual(order.order_line.filtered(lambda line: line.product_id == self.dress).ocd_clip_id, self.clip)

    def test_seen_in_live_on_the_product_page_and_the_replay(self):
        self.authenticate(None, None)
        page = self.url_open(self.dress.product_tmpl_id.website_url).text
        self.assertIn("Seen in live", page)
        self.assertIn(f"/ocd/clips/{self.clip.id}/video?v=", page)
        self.assertIn(f"/ocd/clips/{self.clip.id}/lu", page)
        self.assertNotIn("<video", page.split("o_ocd_seen_live", 1)[1][:600], "Nothing loads before the touch")
        self.live.write({"replay_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "state": "done"})
        self.live.action_publish_replay()
        page = self.url_open(self.dress.product_tmpl_id.website_url).text
        self.assertIn(f"/ocd/boutique/{self.brenda.id}/replay?live={self.live.id}&amp;t=5", page)
        replay = self.url_open(f"/ocd/boutique/{self.brenda.id}/replay?live={self.live.id}").text
        self.assertIn("o_ocd_moment_clip", replay)
        # Hidden, or the vendor refuses the clips: no longer shown
        self.clip.action_ocd_hide()
        self.assertNotIn("Seen in live", self.url_open(self.dress.product_tmpl_id.website_url).text)
        self.assertNotIn("o_ocd_moment_clip", self.url_open(f"/ocd/boutique/{self.brenda.id}/replay?live={self.live.id}").text)

    def test_the_video_of_a_clip_and_its_plays(self):
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/clips/{self.clip.id}/video?v={self.clip.version}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "video/mp4")
        self.assertIn("public", response.headers["Cache-Control"])
        response = self.url_open(f"/ocd/clips/{self.clip.id}/video", headers={"Range": "bytes=0-9"})
        self.assertEqual(response.status_code, 206, "The phones ask a video by parts")
        response = self.url_open(f"/ocd/clips/{self.clip.id}/video?dl=1")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(self.url_open(f"/ocd/clips/{self.clip.id}/image").status_code, 200)
        self.assertEqual(self.url_open(f"/ocd/clips/{self.clip.id}/lu", data={"v": "1"}, headers=PHONE).status_code, 204)
        self.url_open(f"/ocd/clips/{self.clip.id}/lu", data={"v": "1"}, headers={"User-Agent": "Googlebot/2.1"})
        plays = self.Count._ocd_record_totals(self.brenda, "clip_play", [self.clip.id])
        self.assertEqual(plays, {self.clip.id: 1}, "The robots do not play")
        # A hidden clip: its vendor still sees it, nobody else
        self.clip.action_ocd_hide()
        self.assertEqual(self.url_open(f"/ocd/clips/{self.clip.id}/video").status_code, 404)
        self._vendor_login()
        self.assertEqual(self.url_open(f"/ocd/clips/{self.clip.id}/video").status_code, 200)

    def test_the_clips_in_the_space_of_the_vendor(self):
        self._vendor_login()
        self.assertIn("Your clip is ready", self.url_open("/ocd/espace/moi").text)
        page = self.url_open("/ocd/espace/moi/clips").text
        self.assertIn(f"/ocd/espace/moi/clips/{self.clip.id}", page)
        self.assertIn("My clips", page)
        clip_class = type(self.clip)
        with patch.object(clip_class, "_ocd_whatsapp_ready", lambda self: False):
            page = self.url_open(f"/ocd/espace/moi/clips/{self.clip.id}").text
        self.assertIn(self.clip._ocd_link_text(), page)
        self.assertIn("o_ocd_clip_share_file", page)
        self.assertNotIn(f"/ocd/espace/moi/clips/{self.clip.id}/whatsapp", page, "No WhatsApp: no button")
        with patch.object(clip_class, "_ocd_whatsapp_ready", lambda self: True):
            page = self.url_open(f"/ocd/espace/moi/clips/{self.clip.id}").text
        self.assertIn(f"/ocd/espace/moi/clips/{self.clip.id}/whatsapp", page)
        response = self._post(f"/ocd/espace/moi/clips/{self.clip.id}/masquer")
        self.assertTrue(self.clip.hidden)
        self.assertEqual(self.clip.hidden_by, "vendor")
        self.assertIn("no longer shows on the site", self.url_open(response.headers["Location"]).text)
        self._post(f"/ocd/espace/moi/clips/{self.clip.id}/masquer")
        self.assertFalse(self.clip.hidden)
        self._post(f"/ocd/espace/moi/clips/{self.clip.id}/carte")
        self.assertEqual(self.brenda.ocd_card_media, "video")
        with patch.object(clip_class, "_ocd_whatsapp_ready", lambda self: False):
            response = self._post(f"/ocd/espace/moi/clips/{self.clip.id}/whatsapp")
        self.assertIn("erreur=whatsapp", response.headers["Location"])
        products = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn("1 clip", products)
        self.assertIn(f"/ocd/espace/moi/clips?produit={self.dress.product_tmpl_id.id}", products)
        page = self.url_open(f"/ocd/espace/moi/clips?produit={self.scarf.product_tmpl_id.id}").text
        self.assertIn("Show it in your next live", page)
        # « From my clips » in « My figures » (OCD Business)
        self.company.ocd_business_offered_all = True
        self.Count._ocd_add(self.brenda, "clip_visit", self.clip.id)
        figures = self.url_open("/ocd/espace/moi/chiffres").text
        self.assertIn("From my clips", figures)
        self.assertIn("Best clip: Robe en wax", figures)
        # The link of the WhatsApp opens « My clips »
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}/clips", allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith("/ocd/espace/moi/clips"))
        # Not the clip of another vendor
        self._vendor_login(self.fatou)
        self.assertEqual(self.url_open(f"/ocd/espace/moi/clips/{self.clip.id}").status_code, 404)

    def test_the_team_sends_the_video_in_pieces(self):
        live = self._live()
        self._moment(live, self.scarf, 4)
        data = make_video(20)
        # Not the team: no sending
        self.authenticate(None, None)
        part = self.env["ocd.live.recording"]._ocd_start(live, "studio.mp4", len(data))
        response = self.url_open(f"/ocd/clips/envoi/{part.id}?token={part.token}&offset=0", data=data[:100],
                                 headers={"Content-Type": "application/octet-stream"}, allow_redirects=False)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(part.received, 0)
        self.authenticate("admin", "admin")
        start = live.with_user(self.env.ref("base.user_admin")).ocd_clips_start_upload("studio.mp4", len(data))
        self.assertEqual(start["id"], part.id, "The same file goes on")
        bad = self.url_open(f"/ocd/clips/envoi/{part.id}?token=wrong&offset=0", data=data[:100],
                            headers={"Content-Type": "application/octet-stream"})
        self.assertEqual(bad.status_code, 404)
        received = 0
        while received < len(data):
            response = self.url_open(f"/ocd/clips/envoi/{part.id}?token={part.token}&offset={received}",
                                     data=data[received:received + 4096],
                                     headers={"Content-Type": "application/octet-stream"})
            received = response.json()["received"]
        self.assertEqual(response.json()["state"], "checking")
        with patch.object(clip_video, "make", fake_make):
            self._run_cron()
        self.assertEqual(part.state, "ready")
        self.assertEqual(live.ocd_clip_ids.state, "ready")
        preview = self.url_open(f"/ocd/clips/apercu/{live.id}")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.headers["Content-Type"], "video/mp4")
        # The control room at the end of the live
        regie = self.env["ocd.live.regie"].get_regie_data(live.id)
        self.assertEqual(regie["clips"]["line"], "1 clip ready.")
        self.assertTrue(regie["clips"]["sent"])
