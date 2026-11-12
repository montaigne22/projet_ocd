from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

from .common import OcdLiveCommon

TOGO_LIVE = "https://www.tiktok.com/@ocdlive.tg/live"
MAIN_LIVE = "https://www.tiktok.com/@ocdlive/live"


@tagged("post_install", "-at_install")
class TestOcdLivePlatforms(OcdLiveCommon):
    """The platforms of the lives are a list of the team: a link is recognised from its address."""

    def test_platform_of_a_link(self):
        Platform = self.env["ocd.live.platform"]
        tiktok = self.env.ref("ocd_live.platform_tiktok")
        self.assertEqual(Platform._ocd_for_url("https://www.tiktok.com/@awa/live"), tiktok)
        self.assertEqual(Platform._ocd_for_url("https://vm.tiktok.com/ZM123/"), tiktok, "Its sub-addresses too")
        self.assertEqual(
            Platform._ocd_for_url("https://m.facebook.com/awa/videos/1"), self.env.ref("ocd_live.platform_facebook")
        )
        self.assertEqual(Platform._ocd_for_url("https://youtu.be/abc"), self.env.ref("ocd_live.platform_youtube"))
        self.assertFalse(Platform._ocd_for_url("http://www.tiktok.com/@awa/live"), "https only")
        self.assertFalse(Platform._ocd_for_url("https://faketiktok.com/@awa"), "Not a sub-address")
        self.assertFalse(Platform._ocd_for_url("https://www.twitch.tv/awa"))
        twitch = Platform.create({"name": "Twitch", "code": "twitch", "domains": "twitch.tv"})
        self.assertEqual(Platform._ocd_for_url("https://www.twitch.tv/awa"), twitch, "Added by the team: known at once")
        self.assertIn("Twitch", Platform._ocd_names_text(), "In the messages that name the platforms")
        twitch.active = False
        self.assertFalse(Platform._ocd_for_url("https://www.twitch.tv/awa"), "Archived: no longer known")
        with self.assertRaises(ValidationError):
            Platform.create({"name": "Bad", "code": "bad", "domains": "https://bad.example/live"})

    def test_link_of_the_directory_says_its_platform(self):
        now = fields.Datetime.now()
        listing = self.env["ocd.directory.listing"].create({
            "partner_id": self.vendor.id,
            "url": "https://www.facebook.com/brenda/live",
            "window_start": now,
            "window_end": now + timedelta(hours=2),
        })
        self.assertEqual(listing.platform_id, self.env.ref("ocd_live.platform_facebook"))
        self.assertIn("TikTok", listing._ocd_link_error())


@tagged("post_install", "-at_install")
class TestOcdLiveAccounts(OcdLiveCommon):
    """The accounts of OCD Live: each live takes the one of its mode and of the country of its
    vendor, free at its hour."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env["ocd.live.account"]
        Account.search([]).active = False  # the ones of the demonstration
        cls.togo = cls.env.ref("base.tg")
        cls.togo_remote = Account.create({
            "name": "OCD Live Togo", "handle": "@ocdlive.tg", "live_url": TOGO_LIVE, "mode": "remote",
            "country_ids": [Command.set(cls.togo.ids)], "sequence": 20,
        })
        cls.main = Account.create({"name": "OCD Live", "handle": "@ocdlive", "live_url": MAIN_LIVE, "sequence": 10})

    def test_each_live_takes_its_account(self):
        remote_togo = self._book(self.starts[0], partner=self.other_vendor, mode="remote")
        self.assertEqual(remote_togo.account_id, self.togo_remote, "The account of its country first")
        remote_cameroon = self._book(self.starts[2], mode="remote")
        self.assertEqual(remote_cameroon.account_id, self.main, "No account for Cameroon: the one for all")
        studio_togo = self._book(self.starts[4], partner=self.other_vendor, mode="studio")
        self.assertEqual(studio_togo.account_id, self.main, "The account of Togo takes the remote lives only")
        studio_togo.mode = "remote"
        self.assertEqual(studio_togo.account_id, self.togo_remote)
        self.assertEqual(studio_togo._ocd_watch_url(), TOGO_LIVE, "Its link by default")
        studio_togo.live_url = "https://www.tiktok.com/@ocdlive.tg/live/123"
        self.assertEqual(studio_togo._ocd_watch_url(), "https://www.tiktok.com/@ocdlive.tg/live/123")

    def test_two_lives_at_the_same_hour_take_two_accounts(self):
        second = self.togo_remote.copy({"name": "OCD Live Togo 2", "handle": "@ocdlive.tg2", "sequence": 30})
        first = self._book(self.starts[0], partner=self.other_vendor, mode="remote")
        self.assertEqual(first.account_id, self.togo_remote)
        other = self.env["ocd.live.booking"].new({
            "partner_id": self.other_vendor.id, "mode": "remote", "company_id": self.company.id,
            "start_datetime": first.start_datetime, "end_datetime": first.end_datetime,
        })
        self.assertEqual(self.env["ocd.live.account"]._ocd_pick(other), second, "The first one is busy")

    def test_accounts_added_or_removed_later(self):
        (self.togo_remote | self.main).active = False
        booking = self._book(self.starts[0], partner=self.other_vendor, mode="remote")
        self.assertFalse(booking.account_id)
        self.togo_remote.active = True
        self.assertEqual(booking.account_id, self.togo_remote, "The lives to come take the new account")
        self.togo_remote.country_ids = [Command.set(self.env.ref("base.cm").ids)]
        self.assertFalse(booking.account_id, "It no longer fits: none left")

    def test_link_of_an_account_is_on_its_platform(self):
        with self.assertRaises(ValidationError):
            self.env["ocd.live.account"].create({
                "name": "Wrong", "handle": "@wrong", "live_url": "https://www.facebook.com/ocd/live",
            })


@tagged("post_install", "-at_install")
class TestOcdLiveRemoteJoin(OcdLiveCommon):
    """Before a remote live: the host calls (30 min), the vendor is invited (15 min), the host is
    alerted when the vendor is not ready (5 min)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ocd.live.account"].search([]).active = False
        cls.account = cls.env["ocd.live.account"].create({
            "name": "OCD Live Cameroun", "handle": "@ocdlive.cm", "live_url": "https://www.tiktok.com/@ocdlive.cm/live",
            "country_ids": [Command.set(cls.env.ref("base.cm").ids)],
        })
        cls.booking = cls._book(cls.starts[4], mode="remote", state="confirmed", animatrice_id=cls.host.id)
        cls.call = cls.env.ref("mail.mail_activity_data_call")
        cls.alert = cls.env.ref("ocd_live.mail_activity_type_vendor_alert")

    def _run(self, minutes_before):
        with freeze_time(self.booking.start_datetime - timedelta(minutes=minutes_before)):
            self.env["ocd.live.booking"]._cron_remote_join()

    def _activities(self, activity_type):
        return self.booking.activity_ids.filtered(lambda activity: activity.activity_type_id == activity_type)

    def _sending(self, sent):
        return patch.object(type(self.booking), "_ocd_send_join_invitation", return_value=sent)

    def test_steps_before_the_hour(self):
        booking = self.booking
        self.assertEqual(booking.account_id, self.account)
        self._run(40)
        self.assertFalse(booking.ocd_call_planned, "Not yet")
        self._run(29)
        call = self._activities(self.call)
        self.assertEqual(len(call), 1, "The host calls the vendor for a test")
        self.assertIn("Brenda Wax", call.summary)
        self.assertIn("@ocdlive.cm", str(call.note))
        self.assertEqual(call.user_id, self.env.ref("base.user_admin"), "The host has no user: the manager of the live")
        self.assertFalse(booking.ocd_join_tried)
        self._run(25)
        self.assertEqual(len(self._activities(self.call)), 1, "Once")
        with self._sending(True):
            self._run(14)
        self.assertTrue(booking.ocd_join_sent_at)
        self.assertEqual(booking.ocd_join_state, "invited")
        self._run(4)
        self.assertTrue(booking.ocd_not_ready_alerted)
        self.assertEqual(len(self._activities(self.alert)), 1, "Not ready 5 minutes before: the host is alerted")
        self._run(3)
        self.assertEqual(len(self._activities(self.alert)), 1, "Once")
        booking._ocd_vendor_says_ready()
        self.assertEqual(booking.ocd_join_state, "ready")
        self.assertFalse(self._activities(self.alert), "Done once the vendor is ready")
        booking.action_ocd_host_called()
        self.assertTrue(booking.ocd_host_called_at)
        self.assertFalse(self._activities(self.call), "The call is done")

    def test_invitation_that_cannot_go(self):
        with self._sending(False):
            self._run(14)
        self.assertTrue(self.booking.ocd_join_tried, "Not tried again every 5 minutes")
        self.assertFalse(self.booking.ocd_join_sent_at)
        self.assertEqual(self.booking.ocd_join_state, "waiting")
        self.assertIn(self.booking._ocd_join_path(), self.booking.message_ids[0].body, "The team has the link to give")

    def test_problem_of_the_vendor(self):
        self.booking._ocd_vendor_says_problem("no_invite", "Pas de notification")
        self.assertEqual(self.booking.ocd_join_state, "problem")
        alert = self._activities(self.alert)
        self.assertEqual(len(alert), 1)
        self.assertIn("did not receive the invitation", alert.summary)
        self.assertIn("Problem", self.booking._ocd_join_status_text())
        self.booking._ocd_vendor_says_problem("not a problem code")
        self.assertEqual(self.booking.ocd_vendor_problem, "other")

    def test_a_live_moved_starts_again(self):
        booking = self.booking
        token = booking._ocd_join_token()
        self.assertTrue(booking._ocd_join_check(token))
        self.assertFalse(booking._ocd_join_check("x" * 32))
        booking._ocd_vendor_says_ready()
        booking.start_datetime = self.starts[6]
        self.assertFalse(booking.ocd_vendor_ready_at, "Another hour: the steps start again")
        self.assertFalse(booking._ocd_join_check(token), "The former link no longer opens the page")

    def test_only_the_confirmed_remote_lives(self):
        studio = self._book(self.starts[1], partner=self.other_vendor, state="confirmed")
        held = self._book(self.starts[2], partner=self.other_vendor, mode="remote")
        with freeze_time(studio.start_datetime - timedelta(minutes=10)):
            self.env["ocd.live.booking"]._cron_remote_join()
        with freeze_time(held.start_datetime - timedelta(minutes=10)):
            self.env["ocd.live.booking"]._cron_remote_join()
        self.assertFalse(studio.ocd_call_planned or held.ocd_call_planned)

    def test_switched_off_in_the_automations(self):
        self.env.ref("ocd_live.ir_cron_remote_join").active = False
        self._run(10)
        self.assertFalse(self.booking.ocd_call_planned)


@tagged("post_install", "-at_install")
class TestOcdLiveJoinPage(HttpCase):
    """The page « Join my live » opens with the secret of the invitation, or for the vendor of
    this browser; what the vendor says reaches the live."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        company.write({"ocd_studio_tz": "Africa/Lome", "ocd_booking_open_date": False})
        cls.vendor = cls.env["res.partner"].create({
            "name": "Afi Pagnes", "ocd_is_vendor": True, "ocd_vendor_state": "approved",
            "country_id": cls.env.ref("base.tg").id, "phone": "+228 90 00 00 61",
        })
        cls.env["ocd.live.account"].search([]).active = False
        cls.account = cls.env["ocd.live.account"].create({"name": "OCD Live Togo", "handle": "@ocdlive.tg", "live_url": TOGO_LIVE})
        day = fields.Date.today() + timedelta(days=4)
        product = cls.env.ref("ocd_live.product_package_discovery").product_variant_id
        cls.booking = cls.env["ocd.live.booking"].create({
            "partner_id": cls.vendor.id, "start_datetime": company._ocd_slot_starts(day)[3], "slot_count": 1,
            "product_id": product.id, "mode": "remote", "state": "confirmed",
        })

    def test_page_and_what_the_vendor_says(self):
        self.authenticate(None, None)
        path = self.booking._ocd_join_path()
        response = self.url_open(path)
        self.assertEqual(response.status_code, 200)
        self.assertIn("@ocdlive.tg", response.text)
        self.assertIn(TOGO_LIVE, response.text, "The live of the account, where the invitation comes")
        self.assertEqual(self.url_open(f"/ocd/live/{self.booking.id}/rejoindre/{'x' * 32}").status_code, 404)
        self.assertEqual(self.url_open(f"/ocd/live/{self.booking.id}/rejoindre").status_code, 404, "Nobody logged in")
        self.url_open(f"{path}/compte", data={"csrf_token": self.csrf_token(), "handle": "afi.pagnes"})
        self.assertEqual(self.vendor.ocd_live_handle, "@afi.pagnes")
        self.url_open(f"{path}/pret", data={"csrf_token": self.csrf_token()})
        self.assertEqual(self.booking.ocd_join_state, "ready")
        self.url_open(f"{path}/probleme", data={"csrf_token": self.csrf_token(), "problem": "late", "note": "10 min"})
        self.assertEqual(self.booking.ocd_vendor_problem, "late")
        self.assertEqual(self.booking.ocd_vendor_problem_note, "10 min")

    def test_space_of_the_vendor_gives_the_page(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.vendor._ocd_get_space_token()}")
        self.assertEqual(self.url_open(f"/ocd/live/{self.booking.id}/rejoindre").status_code, 200, "Logged in")
        with freeze_time(self.booking.start_datetime - timedelta(hours=1)):
            self.assertIn(self.booking._ocd_join_path(), self.url_open("/ocd/espace/moi").text, "The day of the live")
        studio = self.booking.copy({"mode": "studio", "start_datetime": self.booking.start_datetime + timedelta(hours=3)})
        self.assertEqual(self.url_open(f"/ocd/live/{studio.id}/rejoindre").status_code, 404, "A studio live has no page")
