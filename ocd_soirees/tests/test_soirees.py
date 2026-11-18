from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdSoirees(HttpCase, OcdShopCommon):
    """The big events (chantier 7, design ProgrammeSoirees): an evening, a day or several days; the
    vendors of the countries invited join with a live and their promos of the event, checked by the
    team."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cameroon = cls.env.ref("base.cm")
        cls.togo = cls.env.ref("base.tg")
        cls.brenda.country_id = cls.cameroon
        cls.fatou.country_id = cls.togo
        cls.robe = cls.dress.product_tmpl_id
        cls.robe.write({"ocd_review_state": "approved", "is_published": True, "website_published": True})
        cls.company.write({"ocd_promo_max_discount": 50, "ocd_promo_reference_days": 14,
                           "ocd_evening_registration_days": 3, "ocd_evening_alert_minutes": 15,
                           "ocd_evening_max_days": 14})
        cls.Evening = cls.env["ocd.evening"]
        cls.EveningClass = type(cls.Evening)
        cls.Participation = cls.env["ocd.evening.participation"]

    def _evening(self, days=6, **values):
        start = fields.Datetime.now().replace(microsecond=0) + timedelta(days=days)
        return self.Evening.create({
            "name": "Vendredi noir", "date_start": start, "date_end": start + timedelta(hours=5),
            "country_ids": [fields.Command.set(self.cameroon.ids)], "max_discount": 40, **values,
        })

    def _live(self, vendor, start, minutes=90, slot=0):
        """A confirmed live of `vendor` at `start` (written directly: no slot of the studio)."""
        later = self.company._ocd_local_today() + timedelta(days=40)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": vendor.id, "start_datetime": self.company._ocd_slot_starts(later)[slot], "mode": "remote",
        })
        booking.write({"state": "confirmed"})
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [start, start + timedelta(minutes=minutes), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        return booking

    def _pricelist_price(self, product):
        pricelist = self.env["product.pricelist"].create({"name": "Test", "currency_id": self.company.currency_id.id})
        return pricelist._get_product_price(product, 1.0)

    def test_an_evening_invites_the_vendors_of_its_countries(self):
        evening = self._evening()
        self.assertEqual(evening.slug, "vendredi-noir")
        self.assertEqual(evening.registration_end, evening.date_start - timedelta(days=3))
        self.assertEqual(evening.tz, "Africa/Douala")
        self.assertFalse(evening._ocd_public())
        invited = []
        with patch.object(self.EveningClass, "_ocd_tell_invited", lambda records, vendors: invited.append(vendors)):
            evening.action_ocd_open()
            evening.action_ocd_open()
        self.assertEqual(evening.state, "open")
        self.assertEqual(len(invited), 1, "Once")
        self.assertIn(self.brenda, invited[0])
        self.assertNotIn(self.fatou, invited[0], "Not of the countries of the evening")
        self.assertIn(evening, self.Evening._ocd_shown())
        with self.assertRaisesRegex(UserError, "vendors of Cameroon"):
            self.Participation._ocd_submit(evening, self.fatou, {})
        with self.assertRaisesRegex(ValidationError, "14 days at most"):
            self._evening(name="Trop long", date_end=evening.date_start + timedelta(days=15))
        with self.assertRaisesRegex(ValidationError, "before the end of the event"):
            evening.registration_end = evening.date_end
        with self.assertRaisesRegex(ValidationError, "between 1 and 60"):
            self.company.ocd_evening_max_days = 0

    def test_the_promos_of_the_evening_during_its_hours(self):
        evening = self._evening()
        evening.action_ocd_open()
        with self.assertRaisesRegex(UserError, "40 % of discount at most"):
            self.Participation._ocd_submit(evening, self.brenda, {self.robe: 6000})
        participation = self.Participation._ocd_submit(evening, self.brenda, {self.robe: 7200})
        promo = participation.promo_ids
        self.assertEqual((participation.state, promo.state, promo.discount), ("to_check", "waiting", 40))
        with freeze_time(evening.date_start + timedelta(hours=1)):
            self.assertEqual(self._pricelist_price(self.dress), 12000, "Not before the check of the team")
        participation.action_ocd_approve()
        self.assertTrue(promo.active)
        self.assertEqual(self._pricelist_price(self.dress), 12000, "Before the evening")
        with freeze_time(evening.date_start + timedelta(hours=1)):
            self.assertEqual(self._pricelist_price(self.dress), 7200, "During the evening")
            self.assertTrue(evening._ocd_running())
        with freeze_time(evening.date_end + timedelta(minutes=1)):
            self.assertEqual(self._pricelist_price(self.dress), 12000, "After the evening")
        # A promo of the vendor lower than the one of the evening: the lowest price, never higher
        self.env["ocd.product.promo"]._ocd_put(self.robe, 6500, fields.Datetime.now() + timedelta(days=20))
        with freeze_time(evening.date_start + timedelta(hours=1)):
            self.assertEqual(self._pricelist_price(self.dress), 6500)
        # Sent again: the promos taken off stop, the participation is checked again
        self.Participation._ocd_submit(evening, self.brenda, {})
        self.assertTrue(promo.stopped_at)
        self.assertEqual(participation.state, "to_check")
        # Moved: its promos follow its hours; cancelled: they stop
        again = self.Participation._ocd_submit(evening, self.brenda, {self.robe: 8000}).promo_ids.filtered(
            lambda p: not p.stopped_at)
        evening.write({"date_start": evening.date_start + timedelta(days=1), "date_end": evening.date_end + timedelta(days=1)})
        self.assertEqual(again.date_start, evening.date_start)
        evening.action_ocd_cancel()
        self.assertTrue(again.stopped_at)

    def test_the_registrations_close(self):
        evening = self._evening(days=2)
        evening.action_ocd_open()
        self.assertFalse(evening._ocd_registration_open(), "3 days before, the registrations are closed")
        with self.assertRaisesRegex(UserError, "closed"):
            self.Participation._ocd_submit(evening, self.brenda, {self.robe: 9000})

    def test_the_people_who_asked_are_told(self):
        evening = self._evening()
        evening.action_ocd_open()
        self.env["ocd.evening.alert"].create({"evening_id": evening.id, "partner_id": self.estelle.id})
        empty = self._evening(name="Sans vendeur")
        empty.action_ocd_open()
        self.env["ocd.evening.alert"].create({"evening_id": empty.id, "partner_id": self.estelle.id})
        self.Participation.create({"evening_id": evening.id, "vendor_id": self.brenda.id, "state": "approved"})
        told = []
        with patch.object(self.EveningClass, "_ocd_tell_alerts", lambda records: told.append(records)):
            self.Evening._cron_ocd_evenings()
            self.assertFalse(told, "Not yet")
            with freeze_time(evening.date_start - timedelta(minutes=10)):
                self.Evening._cron_ocd_evenings()
                self.Evening._cron_ocd_evenings()
        self.assertEqual(told, [evening], "Not the event without a vendor accepted")
        self.assertTrue(empty.told_at)

    def test_the_pages_and_the_vendor(self):
        evening = self._evening(description="La soirée des grosses promos.")
        evening.action_ocd_open()
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        self.assertIn("Vendredi noir: join", self.url_open("/ocd/espace/moi").text, "The invitation in the space")
        page = self.url_open(f"/ocd/espace/moi/evenements/{evening.id}").text
        self.assertIn("Book at the studio", page)
        self.assertIn(f'name="p_{self.robe.id}"', page)
        self.assertIn(evening._ocd_when_sentence(self.brenda._ocd_tz_name() or evening.tz, capital=True), page)
        response = self.url_open(f"/ocd/espace/moi/evenements/{evening.id}", data={
            "csrf_token": self.csrf_token(), f"p_{self.robe.id}": "30",
        })
        self.assertIn("the team checks your participation", response.text)
        self.assertIn("Vendredi noir", self.url_open("/ocd/espace/moi").text)
        participation = self.Participation.search([("evening_id", "=", evening.id)])
        self.assertEqual(participation.promo_ids.price, 8400)
        # The team checks it (« To check »)
        Verification = self.env["ocd.live.verification"]
        items = next(column for column in Verification._ocd_columns() if column["key"] == "evening")["items"]
        self.assertEqual([item["id"] for item in items], [participation.id])
        Verification.ocd_approve("evening_participation", participation.id)
        self.assertEqual(participation.state, "approved")
        # The page of the evening, its promos « soon », « Tell me on WhatsApp »
        self.authenticate(None, None)
        page = self.url_open("/evenements").text
        self.assertIn("Vendredi noir", page)
        self.assertIn(evening._ocd_kicker(), page)
        page = self.url_open(evening._ocd_public_path()).text
        for text in ("La soirée des grosses promos.", "Tell me on WhatsApp", "Robe en wax", "-30 %", "The promos of the event"):
            self.assertIn(text, page)
        # The first addresses (/soirees) lead to the ones of now
        response = self.url_open("/soirees/vendredi-noir?categorie=1", allow_redirects=False)
        location = urlsplit(response.headers["Location"])
        self.assertEqual((response.status_code, location.path, location.query),
                         (301, "/evenements/vendredi-noir", "categorie=1"))
        self.assertEqual(urlsplit(self.url_open("/soirees").url).path, "/evenements")
        self.url_open(f"{evening._ocd_public_path()}/prevenir", data={
            "csrf_token": self.csrf_token(), "phone": "670000000", "country_id": self.cameroon.id,
        })
        self.assertEqual(evening.alert_ids.partner_id, self.estelle)
        self.assertIn("Noted: we write to you", self.url_open(f"{evening._ocd_public_path()}?prevenu=1").text)
        # On the programme of the lives
        page = self.url_open("/lives/programme?pays=tous").text
        self.assertIn(evening._ocd_public_path(), page)
        self.assertIn("o_ocd_programme_day_evening", page)
        draft = self._evening(name="Noël")
        self.assertEqual(self.url_open(draft._ocd_public_path()).status_code, 404)

    def test_the_back_office(self):
        evening = self._evening()
        sections = str(self.env["ocd.live.settings"]._ocd_sections())
        self.assertIn("Registrations of the vendors", sections)
        self.assertIn("Length of an event", sections)
        self.assertIn("evenings", str(self.env["ocd.automation"].get_automations_page()))
        self.assertEqual(evening.action_ocd_view_participations()["domain"], [("evening_id", "=", evening.id)])
        self.assertEqual(evening.action_ocd_open_page()["url"], "/evenements/vendredi-noir")
        self.assertEqual(evening.kind_text, evening._ocd_kind_text())

    def test_the_kind_and_the_texts_of_an_event(self):
        """An evening, an evening until the night, a day, several days: their texts (at the hour of
        Douala, UTC+1)."""
        def event(start, end):
            return self.Evening.new({"name": "Test", "country_ids": [fields.Command.set(self.cameroon.ids)],
                                     "date_start": fields.Datetime.to_datetime(start),
                                     "date_end": fields.Datetime.to_datetime(end), "company_id": self.company.id})

        evening = event("2026-11-27 17:00:00", "2026-11-27 22:00:00")
        self.assertTrue(evening._ocd_one_day())
        self.assertEqual(evening._ocd_kind_text(), "Big evening")
        self.assertEqual(evening._ocd_when_text(), "Friday 27 November · 18:00 – 23:00")
        self.assertEqual(evening._ocd_when_sentence(), "Friday 27 November from 18:00 to 23:00")
        self.assertEqual(evening._ocd_until_text(), "23:00")
        night = event("2026-11-27 19:00:00", "2026-11-28 01:00:00")
        self.assertTrue(night._ocd_one_day(), "An evening until 2:00 is an evening")
        self.assertEqual(night._ocd_days(), [fields.Date.to_date("2026-11-27")])
        midnight = event("2026-11-27 17:00:00", "2026-11-27 23:00:00")
        self.assertEqual(midnight._ocd_hours_text(), "18:00 – midnight")
        day = event("2026-11-28 09:00:00", "2026-11-28 19:00:00")
        self.assertEqual(day._ocd_kind_text(), "Big day")
        week = event("2026-12-01 08:00:00", "2026-12-06 23:00:00")
        self.assertFalse(week._ocd_one_day())
        self.assertEqual(week._ocd_day_count(), 6, "Until Sunday midnight: 6 days, not 7")
        self.assertEqual(week._ocd_kind_text(), "Big event · 6 days")
        self.assertEqual(week._ocd_kicker(), "Big event · 6 days · OCD Live")
        self.assertEqual(week._ocd_when_text(), "From Tuesday 1 December to Sunday 6 December")
        self.assertEqual(week._ocd_when_sentence(capital=True),
                         "From Tuesday 1 December at 09:00 to Sunday 6 December at midnight")
        self.assertEqual(week._ocd_until_text(), "Sunday 6 December at midnight")
        self.assertEqual(week._ocd_start_short(), "Tue 1 Dec")
        self.assertEqual(len(week._ocd_days("Africa/Douala")), 6)

    def test_an_event_of_several_days(self):
        """A week of promos: the promos run without a break, each day is on the programme, the lives
        of the page are by day."""
        start = fields.Datetime.now().replace(microsecond=0) + timedelta(days=4)
        evening = self._evening(name="Semaine Tabaski", date_start=start, date_end=start + timedelta(days=5),
                                registration_end=start + timedelta(days=2))
        self.assertEqual(evening._ocd_kind_text(), "Big event · %s days" % evening._ocd_day_count())
        evening.action_ocd_open()
        # The registrations stay open during the event, until the date chosen by the team
        with freeze_time(start + timedelta(days=1)):
            self.assertTrue(evening._ocd_registration_open())
        with freeze_time(start + timedelta(days=2, minutes=1)):
            self.assertFalse(evening._ocd_registration_open())
        participation = self.Participation._ocd_submit(evening, self.brenda, {self.robe: 8400})
        participation.action_ocd_approve()
        for moment in (timedelta(hours=1), timedelta(days=2, hours=12), timedelta(days=5) - timedelta(minutes=1)):
            with freeze_time(start + moment):
                self.assertEqual(self._pricelist_price(self.dress), 8400, f"During the event: {moment}")
        with freeze_time(start + timedelta(days=5, minutes=1)):
            self.assertEqual(self._pricelist_price(self.dress), 12000, "After the event")
        # Two lives on two days: the page shows them by day
        first = self._live(self.brenda, start + timedelta(hours=2))
        second = self._live(self.brenda, start + timedelta(days=1, hours=2), slot=1)
        participation.invalidate_recordset(["booking_id"])
        self.assertEqual(participation.booking_id, first)
        self.assertEqual(evening._ocd_lives(), first | second)
        self.authenticate(None, None)
        tz_name = self.company.ocd_studio_tz or "Africa/Lome"
        page = self.url_open(evening._ocd_public_path()).text
        self.assertEqual(page.count('class="o_ocd_evening_day"'), 2, "One title per day of lives")
        self.assertIn(evening._ocd_when_sentence(tz_name, capital=True), page)
        # Each day of the event in the next 7 days is marked on the programme
        page = self.url_open("/lives/programme?pays=tous").text
        today = evening._ocd_local(fields.Datetime.now(), tz_name).date()
        days = [day for day in evening._ocd_days(tz_name) if day < today + timedelta(days=7)]
        self.assertEqual(page.count("o_ocd_programme_day_evening"), len(days))
