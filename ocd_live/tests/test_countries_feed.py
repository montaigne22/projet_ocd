import re
from datetime import datetime, time, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.ocd_live import countries


@tagged("post_install", "-at_install")
class TestOcdLiveCountries(TransactionCase):

    def test_offered_countries_and_their_order(self):
        Country = self.env["res.country"]
        codes = set(Country._ocd_offered().mapped("code"))
        self.assertTrue(set(countries.AFRICA) <= codes, "Every country of Africa")
        for code in ("FR", "BE", "US", "CA", "BR", "CN", "IN", "AE"):
            self.assertIn(code, codes)
        rows = Country._ocd_ordered(self.env.ref("base.fr"))
        self.assertEqual(rows[0][0].code, "FR", "The country of the person first")
        self.assertEqual([country.code for country, _group in rows[1:6]], list(countries.MAIN_COUNTRIES))
        groups = [group for _country, group in rows]
        self.assertLess(groups.index("africa"), groups.index("europe"))
        self.assertLess(groups.index("americas"), groups.index("asia"))
        japan = self.env.ref("base.jp")
        japan.action_ocd_withdraw()
        self.assertNotIn(japan, Country._ocd_offered(), "The team chooses the countries")
        japan.action_ocd_offer()
        self.assertIn(japan, Country._ocd_offered())

    def test_continents(self):
        self.assertEqual(countries.continent("CV"), "africa")
        self.assertEqual(countries.continent("FR"), "europe")
        self.assertEqual(countries.continent("HT"), "americas")
        self.assertEqual(countries.continent("JP"), "asia")
        self.assertEqual(self.env.ref("base.mu").ocd_continent, "africa")

    def test_phone_numbers_of_every_country(self):
        ref = self.env.ref
        cases = [
            (ref("base.tg"), "90 00 00 07", "+228 90000007"),
            (ref("base.tg"), "+228 90 00 00 07", "+228 90000007"),
            (ref("base.fr"), "06 12 34 56 78", "+33 612345678"),
            (ref("base.ci"), "07 07 07 07 07", "+225 0707070707"),
            (ref("base.cm"), "6 70 00 00 02", "+237 670000002"),
        ]
        for library in (countries.phonenumbers, None):
            with patch.object(countries, "phonenumbers", library):
                for country, typed, stored in cases:
                    self.assertEqual(countries.normalize(country, typed), stored, (country.code, typed, library))
                self.assertFalse(countries.normalize(ref("base.tg"), "900"))
                self.assertFalse(countries.normalize(ref("base.cm"), "+33 6 12 34 56 78"), "A number of another country")
                self.assertEqual(countries.local_digits(ref("base.cm"), "+237 670000002"), "670000002")
        if countries.phonenumbers:
            self.assertTrue(countries.example(ref("base.cm")))


@tagged("post_install", "-at_install")
class TestOcdLiveFeed(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({"ocd_studio_tz": "Africa/Lome", "ocd_booking_open_date": False})
        cls.window_day = fields.Date.today() + timedelta(days=3)
        cls.in_window = datetime.combine(cls.window_day, time(9, 0))  # Lome: UTC
        cls.out_of_window = datetime.combine(cls.window_day, time(13, 0))
        Partner = cls.env["res.partner"]
        cls.togo = Partner.create({
            "name": "Afi Pagnes", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id, "phone": "+228 90 00 00 41",
        })
        cls.cameroon = Partner.create({
            "name": "Ngono Beaute", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.cm").id, "phone": "+237 670000041",
        })

    def _listing(self, vendor, minutes_ago=5):
        now = fields.Datetime.now()
        return self.env["ocd.directory.listing"].sudo().create({
            "partner_id": vendor.id,
            "url": "https://www.tiktok.com/@ocd/live",
            "state": "published",
            "country_id": vendor.country_id.id,
            "category_id": self.env.ref("ocd_live.category_food").id,
            "window_start": now - timedelta(hours=1),
            "window_end": now + timedelta(hours=1),
            "checked_at": now - timedelta(minutes=minutes_ago),
        })

    def _keys(self, html):
        return re.findall(r'<(?:article|div)[^>]*class="o_ocd_feed_card[^"]*"[^>]*data-key="([^"]+)"', html) or \
            re.findall(r'data-key="([^"]+)"', html)

    def test_country_of_the_person_first_then_the_others(self):
        with freeze_time(self.in_window):
            togo, cameroon = self._listing(self.togo), self._listing(self.cameroon)
            keys = self._keys(self.url_open("/lives?pays=cm").text)
            self.assertEqual(keys[0], f"l{cameroon.id}", "Cameroon first")
            self.assertIn("c-tg", keys, "Then a card for Togo")
            self.assertLess(keys.index("c-tg"), keys.index(f"l{togo.id}"))
            keys = self._keys(self.url_open("/lives?pays=tg").text)
            self.assertEqual(keys[0], f"l{togo.id}", "Togo first")
            response = self.url_open("/lives?pays=sn")
            keys = self._keys(response.text)
            self.assertEqual(keys[0], "none-SN", "No live in Senegal: said, then the others")
            self.assertIn("o_ocd_feed_bar", response.text)
            # On a tablet and a computer: the head stays at the top with « I am live » in it,
            # and the sentences of the phone (« swipe up ») have their version for the page
            self.assertIn('class="o_ocd_feed_head"', response.text)
            self.assertIn('href="/lives/pass" class="o_ocd_cta o_ocd_feed_live_cta"', response.text)
            self.assertIn("Here are the lives of the other countries, below.", response.text)

    def test_home_names_the_countries_with_lives_only(self):
        """The home page names the countries with a live (the most first) and the one of the
        visitor even without a live, then « All countries »: never the long list of the countries
        offered, most of them without a live."""
        with freeze_time(self.in_window):
            other = self.env["res.partner"].create({
                "name": "Ewondo Mode", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
                "country_id": self.env.ref("base.cm").id, "phone": "+237 670000042",
            })
            self._listing(self.togo)
            self._listing(self.cameroon)
            self._listing(other)
            self.opener.cookies.set("tz", "Europe/Paris")  # a visitor in France
            home = self.url_open("/reserver").text
            links = re.findall(r'<a\b[^>]*\bclass="o_ocd_chip[^"]*"[^>]*>', home)
            chips = [re.search(r'href="/lives/?([a-z]*)"', link).group(1) for link in links]
            self.assertEqual(chips, ["cm", "tg", "fr", "pays"],
                             "Cameroon (2 lives), Togo (1), France (the visitor), then « All countries »")
            self.assertIn("o_ocd_chip_all", links[-1])

    def test_the_lives_of_a_category(self):
        """The categories of the Lives tab: the lives of a category in every country, the country
        chosen kept, the next cards of the same category."""
        with freeze_time(self.in_window):
            food = self.env.ref("ocd_live.category_food")
            other = self.env["ocd.live.category"].search([("id", "!=", food.id)], limit=1)
            togo, cameroon = self._listing(self.togo), self._listing(self.cameroon)
            cameroon.category_id = other
            page = self.url_open(f"/lives?pays=cm&categorie={food.id}").text
            keys = self._keys(page)
            self.assertIn(f"l{togo.id}", keys)
            self.assertNotIn(f"l{cameroon.id}", keys, "Another category: not in the feed")
            self.assertIn(f"/lives?pays=tg&amp;categorie={food.id}", page, "A country chosen keeps the category")
            self.assertIn('class="o_ocd_feed_cat o_ocd_on"', page)
            result = self.make_jsonrpc_request("/lives/flux", {"offset": 0, "pays": "cm", "categorie": str(other.id)})
            keys = self._keys(result["html"])
            self.assertIn(f"l{cameroon.id}", keys)
            self.assertNotIn(f"l{togo.id}", keys, "The next cards: of the same category")

    def test_search_your_country(self):
        """« Search your country »: by its name, without the accents, its English name, its code or
        a name people type (Ivory Coast); a single country found opens its page."""
        from odoo.addons.ocd_live.controllers import common
        self.assertEqual(common.fold("Côte d'Ivoire"), "cotedivoire")
        for typed, code in (("cote divoire", "ci"), ("ivory", "ci"), ("CM", "cm"), ("rdc", "cd"), ("Togo", "tg")):
            response = self.url_open(f"/lives/pays?q={typed}", allow_redirects=False)
            self.assertEqual(response.status_code, 303, typed)
            self.assertTrue(response.headers["Location"].endswith(f"/lives/{code}"), typed)
        several = self.url_open("/lives/pays?q=gu").text
        for code in ("gn", "gq", "gw"):
            self.assertIn(f'href="/lives/{code}"', several, "Several countries found: the list of them")
        self.assertNotIn('href="/lives/cm"', several)
        self.assertIn("No country found", self.url_open("/lives/pays?q=zzz").text)
        every = self.url_open("/lives/pays").text
        self.assertGreater(every.count('class="o_ocd_chip"'), 50, "All the countries offered")
        home = self.url_open("/reserver").text
        self.assertIn('action="/lives/pays"', home, "The search of the home page, without JavaScript too")
        self.assertIn("ivorycoast", home, "The names typed, for the search as the person types")

    def test_the_lives_of_a_country_with_the_cards_of_the_feed(self):
        with freeze_time(self.in_window):
            listing = self._listing(self.cameroon)
            page = self.url_open("/lives/cm").text
            self.assertIn(f'data-key="l{listing.id}"', page, "The card of the feed")
            self.assertIn("o_ocd_feed_page", page, "The cards one under the other, the page scrolls")
            self.assertIn("1 live", page)
            other = self.env["ocd.live.category"].search([("id", "!=", listing.category_id.id)], limit=1)
            page = self.url_open(f"/lives/cm?categorie={other.id}").text
            self.assertNotIn(f'data-key="l{listing.id}"', page, "Another category: not this live")

    def test_next_pages_and_new_lives(self):
        with freeze_time(self.in_window):
            vendors = self.env["res.partner"].create([{
                "name": f"Vendeuse {number}", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
                "country_id": self.env.ref("base.cm").id,
            } for number in range(12)])
            listings = [self._listing(vendor, minutes_ago=minutes) for minutes, vendor in enumerate(vendors, 1)]
            response = self.url_open("/lives?pays=cm")
            self.assertIn("/lives?pays=cm&amp;page=2", response.text, "Without JavaScript: a link to the next cards")
            first_page = self._keys(response.text)
            result = self.make_jsonrpc_request("/lives/flux", {"offset": 8, "pays": "cm"})
            second_page = self._keys(result["html"])
            self.assertTrue(second_page)
            self.assertFalse(set(first_page) & set(second_page), "No card twice")
            self.assertIn(f"l{listings[0].id}", first_page + second_page)
            since = fields.Datetime.to_string(fields.Datetime.now() - timedelta(minutes=3))
            self.assertEqual(self.make_jsonrpc_request("/lives/nouveaux", {"since": since})["count"], 2)

    def test_closed_feed_shows_next_lives_and_replays(self):
        Booking = self.env["ocd.live.booking"].sudo()
        product = self.env.ref("ocd_live.product_package_discovery").product_variant_id
        starts = self.company._ocd_slot_starts(self.window_day + timedelta(days=1))
        coming = Booking.create({
            "partner_id": self.cameroon.id, "start_datetime": starts[0], "slot_count": 1,
            "product_id": product.id, "state": "confirmed",
        })
        with freeze_time(self.out_of_window):
            keys = self._keys(self.url_open("/lives?pays=cm").text)
        self.assertEqual(keys[0], "closed", "Out of the windows: when the checked lives come back")
        self.assertIn(f"n{coming.id}", keys, "The next lives fill the feed")

    def test_one_next_live_and_one_replay_per_vendor(self):
        """A vendor who booked many lives shows its next one and its last replay: the other
        countries come soon in the feed."""
        Booking = self.env["ocd.live.booking"].sudo()
        product = self.env.ref("ocd_live.product_package_discovery").product_variant_id
        coming = self.company._ocd_slot_starts(self.window_day + timedelta(days=1))
        past = self.company._ocd_slot_starts(self.window_day - timedelta(days=1))
        common = {"partner_id": self.cameroon.id, "slot_count": 1, "product_id": product.id}
        first, second = Booking.create([
            {**common, "start_datetime": coming[0], "state": "confirmed"},
            {**common, "start_datetime": coming[2], "state": "confirmed"},
        ])
        replay = {"state": "done", "replay_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "replay_published": True}
        older, last = Booking.create([
            {**common, **replay, "start_datetime": past[0]},
            {**common, **replay, "start_datetime": past[2]},
        ])
        with freeze_time(self.out_of_window):
            keys = self._keys(self.url_open("/lives?pays=cm").text)
        self.assertIn(f"n{first.id}", keys)
        self.assertNotIn(f"n{second.id}", keys, "Its next live only")
        self.assertIn(f"r{last.id}", keys)
        self.assertNotIn(f"r{older.id}", keys, "Its last replay only")

    def test_picture_of_a_vendor(self):
        self.assertEqual(self.url_open(f"/lives/image/{self.togo.id}").status_code, 404, "No picture")
        self.togo.ocd_vendor_state = "to_check"
        self.assertEqual(self.url_open(f"/lives/image/{self.togo.id}").status_code, 404, "Not approved")

    def test_phone_field_offers_every_country(self):
        response = self.url_open("/ocd/connexion")
        self.assertIn('<optgroup label="Africa"', response.text)
        self.assertIn("Cameroon (+237)", response.text)
        self.assertIn("France (+33)", response.text)
        self.assertIn("o_ocd_dial_sheet", response.text, "The sheet to search a country")
