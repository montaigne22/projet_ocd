import re
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live import page_cache
from odoo.addons.ocd_live.controllers import feed
from odoo.addons.ocd_live.tests.test_card_media import png

TOKEN = re.compile(r"[0-9a-f]{40}o[0-9]{10}")


@tagged("post_install", "-at_install")
class TestPageCache(HttpCase):
    """The public pages kept in memory a few seconds: given again to the visitors who have
    nothing of their own on the site, with the token of the forms of each one; built for the
    others."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({
            "name": "Afi Pagnes", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id, "phone": "+228 90 00 00 51",
        })

    def setUp(self):
        super().setUp()
        patcher = patch.object(page_cache, "IN_TESTS", True)
        patcher.start()
        self.addCleanup(patcher.stop)
        page_cache.clear()
        self.addCleanup(page_cache.clear)
        feed._moments.clear()
        self.addCleanup(feed._moments.clear)

    def _open(self, path, **kwargs):
        """`path` opened by a new visitor: its answer and where it came from (hit: from memory,
        miss: built and kept, pass: built for this visitor)."""
        self.authenticate(None, None)
        response = self.url_open(path, **kwargs)
        self.assertEqual(response.status_code, 200)
        return response, response.headers.get(page_cache.HEADER)

    def test_page_given_again_with_the_token_of_each_visitor(self):
        first, origin = self._open("/lives")
        self.assertEqual(origin, "miss")
        second, origin = self._open("/lives")
        self.assertEqual(origin, "hit", "The next visitor gets the page kept")
        tokens = set(TOKEN.findall(second.text))
        self.assertEqual(len(tokens), 1)
        self.assertFalse(tokens & set(TOKEN.findall(first.text)), "The token of the forms of each visitor")
        self.assertEqual(TOKEN.sub("", second.text), TOKEN.sub("", first.text), "The same page")
        # The token works for this visitor: a form of the site accepts it
        response = self.url_open("/ocd/deconnexion", data={"csrf_token": tokens.pop()}, allow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def test_parameters_of_the_address(self):
        self._open("/lives")
        self.assertEqual(self._open("/lives?fbclid=IwAR0abc&utm_source=facebook")[1], "hit", "The links of the networks")
        self.assertEqual(self._open("/lives?pays=cm")[1], "miss", "Another country first: another page")
        self.assertEqual(self._open("/lives?pays=cm")[1], "hit")
        self.assertEqual(self._open("/lives?note=1")[1], "pass", "After a form: built for its visitor")
        self._open(f"/lives/tg?categorie={self.env.ref('ocd_live.category_food').id}")
        self.assertEqual(self._open("/lives/tg")[1], "miss", "Another category: another page")

    def test_page_showing_the_parameter_of_a_network_not_kept(self):
        """With two languages, the buttons of the languages keep the parameters of the address:
        the page of a link of Facebook is built for its visitor, not kept for the others."""
        self.env["res.lang"]._activate_lang("fr_FR")
        website = self.env.ref("base.default_website")
        website.language_ids |= self.env.ref("base.lang_fr") | self.env.ref("base.lang_en")
        response, origin = self._open("/lives?fbclid=IwAR0first")
        self.assertIn("IwAR0first", response.text)
        self.assertEqual(origin, "miss")
        response, origin = self._open("/lives?fbclid=IwAR0second")
        self.assertEqual(origin, "miss", "Not kept: the other visitors do not get the link of the first one")
        self.assertNotIn("IwAR0first", response.text)
        self.assertEqual(self._open("/lives")[1], "miss")
        self.assertEqual(self._open("/lives")[1], "hit")

    def test_known_visitors_get_their_own_page(self):
        self._open("/lives")
        self.authenticate(None, None)
        response = self.url_open("/lives", cookies={"ocd_vendor": f"{self.vendor.id}.signature"})
        self.assertEqual(response.headers.get(page_cache.HEADER), "pass", "A vendor known on this browser")
        self.authenticate(None, None, session_extra={"ocd_vendor_id": self.vendor.id})
        self.assertEqual(self.url_open("/lives").headers.get(page_cache.HEADER), "pass", "Something of its own")
        self.authenticate("admin", "admin")
        self.assertEqual(self.url_open("/lives").headers.get(page_cache.HEADER), "pass", "Logged in")

    def test_next_cards_of_the_feed(self):
        payload = {"jsonrpc": "2.0", "method": "call", "params": {"offset": 8, "pays": "tg"}}
        first, origin = self._open("/lives/flux", json=payload)
        self.assertEqual(origin, "miss")
        second, origin = self._open("/lives/flux", json=payload)
        self.assertEqual(origin, "hit")
        self.assertEqual(second.json()["result"], first.json()["result"])
        other = dict(payload, params={"offset": 8, "pays": "tg", "other": 1})
        self.assertEqual(self._open("/lives/flux", json=other)[1], "pass")

    def test_new_lives_read_again_after_some_seconds(self):
        since = fields.Datetime.to_string(fields.Datetime.now() - timedelta(minutes=10))

        def count():
            return self.make_jsonrpc_request("/lives/nouveaux", {"since": since})["count"]

        self.assertEqual(count(), 0)
        now = fields.Datetime.now()
        self.env["ocd.directory.listing"].sudo().create({
            "partner_id": self.vendor.id, "url": "https://www.tiktok.com/@afi/live", "state": "published",
            "country_id": self.vendor.country_id.id, "category_id": self.env.ref("ocd_live.category_food").id,
            "window_start": now - timedelta(hours=1), "window_end": now + timedelta(hours=1),
            "checked_at": now - timedelta(minutes=1),
        })
        self.assertEqual(count(), 0, "Read again after a few seconds only")
        feed._moments.clear()
        self.assertEqual(count(), 1)

    def test_switched_off_in_the_settings(self):
        self.env["website"].search([]).ocd_page_cache = False
        self._open("/lives")
        self.assertIsNone(self._open("/lives")[1], "Every page built for its visitor")

    def test_kept_seconds(self):
        self._open("/lives")
        self.assertEqual(self._open("/lives")[1], "hit")
        page_cache.expire()
        self.assertEqual(self._open("/lives")[1], "miss", "Built again after its seconds")

    def test_shared_by_the_workers_of_the_server(self):
        """A page built by one worker is given by the others: their memory is shared in files."""
        first, origin = self._open("/lives")
        self.assertEqual(origin, "miss")
        with page_cache._lock:
            page_cache._pages.clear()  # another worker: nothing in its own memory
        second, origin = self._open("/lives")
        self.assertEqual(origin, "hit", "Given from the pages shared by the workers")
        self.assertEqual(TOKEN.sub("", second.text), TOKEN.sub("", first.text), "The same page")
        self.assertNotEqual(TOKEN.findall(second.text), TOKEN.findall(first.text), "The token of each visitor")
        # After an update of the modules (a new version of the registry): a new folder, no old page
        with page_cache._lock:
            page_cache._pages.clear()
        with patch.object(page_cache, "_version", lambda: "after-an-update"):
            self.assertEqual(self._open("/lives")[1], "miss", "No page of the version before")

    def test_a_folder_not_writable_leaves_the_pages_to_each_worker(self):
        with patch.object(page_cache, "SHARED_ROOTS", ()), patch.object(page_cache.tempfile, "gettempdir", return_value="/proc/ocd"):
            with patch.dict(page_cache._shared, broken=False), self.assertLogs(page_cache.__name__, "WARNING"):
                self.assertEqual(self._open("/lives")[1], "miss")
                self.assertEqual(self._open("/lives")[1], "hit", "Kept by the worker itself")
                self.assertTrue(page_cache._shared["broken"])

    def test_media_kept_by_the_browsers_and_the_cdn(self):
        """The photos and the videos of the approved vendors: a year with their version, a day
        without, for the browsers and the CDN, and without cookies."""
        self.vendor.image_1920 = BinaryBytes(png())
        version = self.vendor._ocd_card_version()
        self.authenticate(None, None)
        response = self.url_open(f"/lives/image/{self.vendor.id}?v={version}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertNotIn("Set-Cookie", response.headers)
        response = self.url_open(f"/lives/image/{self.vendor.id}")
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=86400")
        self.assertEqual(self.vendor._ocd_card_media()["image"], f"/lives/image/{self.vendor.id}?v={version}")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers, "Same address: nothing to allow")
        # Asked by the CDN (no session): the pages of the site may use it from the address of the
        # CDN (the browsers ask it for the fonts of the icons)
        self.opener.cookies.clear()
        response = self.url_open(
            f"/lives/image/{self.vendor.id}?v={version}", headers={"X-Odoo-Database": self.env.cr.dbname}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertNotIn("Set-Cookie", response.headers)
