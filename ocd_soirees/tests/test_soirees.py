from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdSoirees(HttpCase, OcdShopCommon):
    """The big evenings (chantier 7, design ProgrammeSoirees): the vendors of the countries invited
    join with a live and their promos of the evening, checked by the team."""

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
                           "ocd_evening_registration_days": 3, "ocd_evening_alert_minutes": 15})
        cls.Evening = cls.env["ocd.evening"]
        cls.EveningClass = type(cls.Evening)
        cls.Participation = cls.env["ocd.evening.participation"]

    def _evening(self, days=6, **values):
        start = fields.Datetime.now().replace(microsecond=0) + timedelta(days=days)
        return self.Evening.create({
            "name": "Vendredi noir", "date_start": start, "date_end": start + timedelta(hours=5),
            "country_ids": [fields.Command.set(self.cameroon.ids)], "max_discount": 40, **values,
        })

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
        with self.assertRaises(Exception):
            self._evening(name="Trop long", date_end=evening.date_start + timedelta(hours=30))

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
        told = []
        with patch.object(self.EveningClass, "_ocd_tell_alerts", lambda records: told.append(records)):
            self.Evening._cron_ocd_evenings()
            self.assertFalse(told, "Not yet")
            with freeze_time(evening.date_start - timedelta(minutes=10)):
                self.Evening._cron_ocd_evenings()
                self.Evening._cron_ocd_evenings()
        self.assertEqual(told, [evening])

    def test_the_pages_and_the_vendor(self):
        evening = self._evening(description="La soirée des grosses promos.")
        evening.action_ocd_open()
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        self.assertIn("Vendredi noir: join", self.url_open("/ocd/espace/moi").text, "The invitation in the space")
        page = self.url_open(f"/ocd/espace/moi/soirees/{evening.id}").text
        self.assertIn("Book at the studio", page)
        self.assertIn(f'name="p_{self.robe.id}"', page)
        response = self.url_open(f"/ocd/espace/moi/soirees/{evening.id}", data={
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
        page = self.url_open("/soirees").text
        self.assertIn("Vendredi noir", page)
        page = self.url_open(evening._ocd_public_path()).text
        for text in ("La soirée des grosses promos.", "Tell me on WhatsApp", "Robe en wax", "-30 %", "The promos of the evening"):
            self.assertIn(text, page)
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
        self.assertIn("evenings", str(self.env["ocd.automation"].get_automations_page()))
        self.assertEqual(evening.action_ocd_view_participations()["domain"], [("evening_id", "=", evening.id)])
        self.assertEqual(evening.action_ocd_open_page()["url"], "/soirees/vendredi-noir")
