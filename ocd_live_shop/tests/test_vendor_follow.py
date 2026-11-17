from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.modules.module import load_script
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorFollow(HttpCase, OcdShopCommon):
    """Follow a vendor (chantier 1, design SuivreVendeur) and their news (A.8): a WhatsApp at each
    live (2 a day at most), the news on Friday (once a month, each week with OCD Business), the
    vendor sees how many follow them."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_news_weekday": "4", "ocd_live_messages_per_day": 2,
                           "ocd_vendor_login": "link"})
        cls.cameroon = cls.env.ref("base.cm")
        (cls.brenda | cls.fatou).write({"country_id": cls.cameroon.id})
        cls.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved",
                                         "ocd_review_date": fields.Datetime.now() - timedelta(days=2)})
        cls.Follower = cls.env["ocd.vendor.follower"]
        cls.FollowerClass = type(cls.Follower)

    def _post(self, url, **data):
        return self.url_open(url, data={"csrf_token": self.csrf_token(), **data})

    def _live(self, vendor, start, minutes=90):
        """A confirmed live of `vendor` from `start` (written directly: no slot needed)."""
        # A free slot far away first (the start is written after)
        self._slot = getattr(self, "_slot", 0) + 1
        later = self.company._ocd_local_today() + timedelta(days=30 + self._slot)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": vendor.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "remote",
        })
        booking.state = "confirmed"
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [start, start + timedelta(minutes=minutes), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        return booking

    # === FOLLOW, CHANGE, STOP === #

    def test_follow_with_a_number_then_change_and_stop(self):
        self.authenticate(None, None)
        boutique = f"/ocd/boutique/{self.brenda.id}"
        page = self.url_open(boutique).text
        self.assertIn(f'href="/ocd/suivre/{self.brenda.id}?depuis=', page)
        self.assertIn("Follow: a WhatsApp at each live", page)
        page = self.url_open(f"/ocd/suivre/{self.brenda.id}?depuis={boutique}").text
        self.assertIn("Follow Brenda Wax", page)
        self.assertIn('name="phone"', page)
        response = self._post(f"/ocd/suivre/{self.brenda.id}", phone="6 70 00 00 01", country_id=self.cameroon.id,
                              lives="1", news="1", depuis=boutique)
        self.assertTrue(response.url.endswith(f"{boutique}?suivi=1"), response.url)
        self.assertIn("You follow Brenda: a WhatsApp at each live, and their news.", response.text)
        self.assertIn("Followed", response.text)
        self.assertIn("1 follower", response.text)
        follower = self.Follower.search([("vendor_id", "=", self.brenda.id)])
        self.assertEqual((follower.lives, follower.news, follower.source), (True, True, "boutique"))
        self.assertEqual(follower.partner_id.phone, "+237 670000001")
        self.assertTrue(follower.partner_id.ocd_whatsapp_optin, "Following is the consent to its messages")
        # « Followed »: change what comes, then stop
        page = self.url_open(f"/ocd/suivre/{self.brenda.id}").text
        self.assertIn("You follow Brenda", page)
        self.assertIn("Stop following", page)
        self._post(f"/ocd/suivre/{self.brenda.id}", lives="1", depuis=boutique)
        self.assertEqual((follower.lives, follower.news), (True, False))
        response = self._post(f"/ocd/suivre/{self.brenda.id}", action="stop", depuis=boutique)
        self.assertIn("You no longer follow Brenda.", response.text)
        self.assertFalse(follower.active)
        # Again: the same follow comes back
        self._post(f"/ocd/suivre/{self.brenda.id}", phone="6 70 00 00 01", country_id=self.cameroon.id, lives="1",
                   depuis=boutique)
        self.assertTrue(follower.active)
        self.assertEqual(self.Follower.search_count([("vendor_id", "=", self.brenda.id)]), 1)
        # Nothing chosen, a wrong number: said on the page
        response = self._post(f"/ocd/suivre/{self.fatou.id}", phone="6 70 00 00 01", country_id=self.cameroon.id)
        self.assertIn("Choose the lives, the news, or both.", response.text)

    def test_a_number_typed_opens_only_the_follows_of_this_browser(self):
        elsewhere = self.Follower._ocd_follow(self.fatou, self.Follower._ocd_contact("+237 670000002"))
        self.authenticate(None, None)
        self._post(f"/ocd/suivre/{self.brenda.id}", phone="6 70 00 00 02", country_id=self.cameroon.id, lives="1", news="1")
        page = self.url_open("/ocd/suivis").text
        self.assertIn("Brenda Wax", page)
        self.assertNotIn("Fatou Karite", page, "A number typed is not checked: only the follows made here")
        # The page of the number leads to them
        self.assertIn("My followed vendors · 1", self.url_open("/ocd/connexion").text)
        # The button of a message: its phone now knows all its follows
        self.assertEqual(self.url_open(f"/ocd/abonne/{elsewhere.id}/wrong-token").status_code, 404)
        response = self.url_open(f"/ocd/abonne/{elsewhere.id}/{elsewhere._ocd_link_token()}?vers=nouveautes")
        self.assertIn(f"/ocd/boutique/{self.fatou.id}?nouveautes=1", response.url)
        page = self.url_open("/ocd/suivis").text
        self.assertIn("Fatou Karite", page)
        self.assertIn("Brenda Wax", page)
        # A switch of the list: no news from Fatou; « Stop following »
        self._post(f"/ocd/suivis/{elsewhere.id}", lives="1")
        self.assertEqual((elsewhere.lives, elsewhere.news), (True, False))
        self._post(f"/ocd/suivis/{elsewhere.id}", action="stop")
        self.assertFalse(elsewhere.active)
        stranger = self.Follower._ocd_follow(self.brenda, self.Follower._ocd_contact("+237 670000003"))
        self.assertEqual(self._post(f"/ocd/suivis/{stranger.id}", action="stop").status_code, 404)

    def test_a_vendor_follows_with_their_number(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.fatou._ocd_get_space_token()}")
        page = self.url_open(f"/ocd/suivre/{self.brenda.id}").text
        self.assertNotIn('name="phone"', page)
        self._post(f"/ocd/suivre/{self.brenda.id}", lives="1", news="1")
        self.assertEqual(self.Follower.search([("vendor_id", "=", self.brenda.id)]).partner_id, self.fatou)
        with self.assertRaisesRegex(UserError, "This is your boutique"):
            self.Follower._ocd_follow(self.fatou, self.fatou)
        self.brenda.ocd_vendor_state = "refused"
        self.assertEqual(self.url_open(f"/ocd/suivre/{self.brenda.id}").status_code, 404)

    # === AT EACH LIVE === #

    def test_two_lives_a_day_at_most(self):
        follower = self.Follower._ocd_follow(self.brenda, self.Follower._ocd_contact("+237 670000004"))
        follower.followed_at = fields.Datetime.now() - timedelta(days=3)
        now = fields.Datetime.now()
        told = []
        with patch.object(self.FollowerClass, "_ocd_tell_live", lambda followers, live: told.append(live)):
            for minutes in (300, 200):
                live = self._live(self.brenda, now - timedelta(minutes=minutes), minutes=60)
                live.ocd_followers_told_at = now - timedelta(minutes=minutes)
            self.assertEqual(self.env["ocd.live.booking"].search_count([("partner_id", "=", self.brenda.id)]), 2)
            third = self._live(self.brenda, now - timedelta(minutes=5))
            self.Follower._ocd_send_lives()
        if (now - timedelta(minutes=300)).date() == now.date():
            self.assertEqual(told, [], "Two lives told today already")
            self.assertTrue(third.ocd_followers_skipped)
        # A follower who arrived during the live is not told of it
        late = self.Follower._ocd_follow(self.fatou, self.Follower._ocd_contact("+237 670000005"))
        live = self._live(self.fatou, now - timedelta(minutes=10))
        told.clear()
        with patch.object(self.FollowerClass, "_ocd_tell_live", lambda followers, live: told.append(followers)):
            self.Follower._ocd_send_lives()
        self.assertEqual(told, [], "Followed after the start")
        self.assertTrue(live.ocd_followers_told_at)
        self.assertTrue(late.active)

    # === THE NEWS (A.8) === #

    def test_news_on_friday_weekly_with_business_monthly_otherwise(self):
        wants = self.Follower._ocd_follow(self.brenda, self.Follower._ocd_contact("+237 670000006"))
        lives_only = self.Follower._ocd_follow(self.brenda, self.Follower._ocd_contact("+237 670000007"), news=False)
        friday = datetime(2026, 11, 20, 9, 30)  # 10:30 in Douala, the third Friday of the month
        self.assertTrue(self.brenda._ocd_news_due(friday))
        self.assertFalse(self.brenda._ocd_news_due(friday - timedelta(hours=2)), "From 10:00")
        self.assertFalse(self.brenda._ocd_news_due(friday + timedelta(days=1)), "Friday only")
        told = []
        with patch.object(self.FollowerClass, "_ocd_tell_news", lambda followers, products: told.append((followers, products))):
            self.Follower._ocd_send_news(friday)
            self.assertEqual(told, [(wants, self.dress.product_tmpl_id)])
            self.assertTrue(wants.news_told_at)
            self.assertFalse(lives_only.news_told_at)
            self.assertEqual(self.brenda.ocd_news_product_ids, self.dress.product_tmpl_id)
            told.clear()
            self.brenda.ocd_news_sent_at = friday
            self.Follower._ocd_send_news(friday + timedelta(hours=1))
            self.assertEqual(told, [], "Once a day")
            # Nothing new since the last news: nothing sent
            self.Follower._ocd_send_news(friday + timedelta(days=7))
            self.assertEqual(told, [])
        # Without OCD Business: once a month, the first Friday
        self.company.ocd_business_offered_all = False
        self.assertFalse(self.brenda._ocd_news_due(friday))
        self.assertTrue(self.brenda._ocd_news_due(datetime(2026, 12, 4, 9, 30)))
        self.assertEqual(self.brenda._ocd_next_news_day().weekday(), 4)
        # « Robe en wax, Sac en raphia and 1 more »
        bag = self._product("Sac en raphia", 8000, self.brenda).product_tmpl_id
        coat = self._product("Veste", 20000, self.brenda).product_tmpl_id
        products = self.dress.product_tmpl_id | bag | coat
        self.assertEqual(self.Follower._ocd_news_list(products), "Robe en wax, Sac en raphia and 1 more")

    def test_the_boutique_shows_the_news_first(self):
        old = self._product("Pagne ancien", 4000, self.brenda).product_tmpl_id
        old.write({"is_published": True, "ocd_review_state": "approved",
                   "ocd_review_date": fields.Datetime.now() - timedelta(days=40)})
        self.brenda.ocd_news_product_ids = self.dress.product_tmpl_id
        self.authenticate(None, None)
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}?nouveautes=1").text
        self.assertLess(page.index("Robe en wax"), page.index("Pagne ancien"))
        self.assertEqual(page.count("o_ocd_product_flag_new"), 1, "Only the new one")

    # === THE VENDOR, THE TEAM === #

    def test_my_followers_in_the_space_and_the_back_office(self):
        self.Follower._ocd_follow(self.brenda, self.Follower._ocd_contact("+237 670000008"))
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn("My followers", page)
        self.assertIn("+1 this week", page)
        self.assertIn("1 product put on sale since the last news: Robe en wax", page)
        self.assertNotIn("+237 670000008", page, "Never the numbers of the followers")
        self.assertEqual(self.brenda.ocd_follower_count, 1)
        self.assertEqual(self.brenda.action_ocd_view_followers()["domain"], [("vendor_id", "=", self.brenda.id)])
        sections = str(self.env["ocd.live.settings"]._ocd_sections())
        self.assertIn("News to the followers", sections)
        self.assertIn("Lives told to the followers", sections)

    def test_the_alerts_of_before_become_follows(self):
        Alert = self.env["ocd.boutique.alert"]
        contact = self.Follower._ocd_contact("+237 670000009")
        waiting = Alert.create({"partner_id": contact.id, "vendor_id": self.brenda.id, "kind": "live"})
        back = Alert.create({"partner_id": contact.id, "vendor_id": self.brenda.id, "kind": "back"})
        migration = load_script("ocd_live_shop/migrations/20.0.1.34.0/post-migration.py", "ocd_shop_follow_20_0_1_34_0")
        migration.migrate(self.env.cr, "20.0.1.33.0")
        follower = self.Follower.search([("partner_id", "=", contact.id)])
        self.assertEqual((follower.vendor_id, follower.lives, follower.news, follower.source),
                         (self.brenda, True, False, "alert"))
        self.assertEqual((waiting.state, back.state), ("cancelled", "waiting"))
