import re
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import HttpCase, tagged

from .test_delivery_rates import OcdRatesCommon


@tagged("post_install", "-at_install")
class TestOcdVendorTeam(HttpCase, OcdRatesCommon):
    """The team of a vendor (chantier 22, A.9 of the plan of « My products », design
    EquipeDuVendeur): the person who holds a store logs in with her number and sees the stock and
    the parcels of her store only, without the prices or the payouts; 5 people at most, OCD
    Business only (paused after, nothing deleted)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False,
                           "ocd_place_proof_required": False, "ocd_store_pickup": True, "ocd_collect_days": 3,
                           "ocd_hold_enabled": True, "ocd_hold_hours": 24, "ocd_vendor_team_max": 5,
                           "ocd_vendor_login": "link"})
        cls.dress.product_tmpl_id.write({"is_storable": True, "allow_out_of_stock_order": False, "is_published": True,
                                         "ocd_review_state": "approved"})
        cls.Place = cls.env["ocd.vendor.place"]
        cls.store = cls.Place._ocd_vendor_create(cls.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "district_id": cls.akwa.id, "city_id": cls.douala.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
        })
        cls.market = cls.Place._ocd_vendor_create(cls.brenda, {
            "name": "Marché central", "kind": "store", "district_id": cls.akwa.id, "city_id": cls.douala.id,
            "landmark": "Allée des tissus", "latitude": 4.0490, "longitude": 9.7000,
        })
        for place in cls.store | cls.market:
            place._ocd_set_hours(cls.company._ocd_place_default_intervals())
        cls.dress._ocd_change_stock(3, cls.store._ocd_location())
        cls.dress._ocd_change_stock(2, cls.market._ocd_location())
        cls.Member = cls.env["ocd.vendor.member"]
        cls.MemberClass = type(cls.Member)
        cls.Partner = type(cls.env["res.partner"])

    def setUp(self):
        super().setUp()
        self.links, self.told = [], []
        for name, effect in (
            ("_ocd_link_sent", lambda member: self.links.append(member) or True),
            ("_ocd_tell_parcel", lambda member, parcel: self.told.append(("parcel", member, parcel))),
            ("_ocd_tell_hold", lambda member, hold: self.told.append(("hold", member, hold))),
        ):
            patcher = patch.object(self.MemberClass, name, effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _aicha(self, place=None):
        return self.Member._ocd_add(self.brenda, "Aïcha Njoya", "+237699123456", place or self.store)

    def _post(self, url, **data):
        return self.url_open(url, data={"csrf_token": self.csrf_token(), **data})

    def _open_her_space(self, member):
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/mon-magasin/{member.partner_id._ocd_get_space_token()}")
        self.assertTrue(response.url.endswith("/ocd/mon-magasin"), response.url)
        return response

    # === THE RULES === #

    def test_added_with_her_number_then_removed(self):
        aicha = self._aicha()
        self.assertEqual((aicha.vendor_id, aicha.place_id, aicha.state), (self.brenda, self.store, "waiting"))
        self.assertEqual((aicha.partner_id.name, aicha.partner_id.phone), ("Aïcha Njoya", "+237699123456"))
        self.assertEqual(self.links, [aicha], "Her link leaves at once")
        self.assertTrue(aicha.invited_at)
        self.assertEqual(self.Member._ocd_of_partner(aicha.partner_id), aicha)
        self.assertEqual(self.Member._ocd_find_by_phone("699 12 34 56"), aicha, "Found by the end of her number")
        aicha._ocd_visit()
        self.assertEqual(aicha.state, "active")
        # Twice, or a vendor, or a courier: refused
        with self.assertRaisesRegex(UserError, "already in your team"):
            self._aicha()
        self.courier.phone = "+237650112233"
        with self.assertRaisesRegex(UserError, "vendor or a courier"):
            self.Member._ocd_add(self.brenda, "Junior", "+237650112233", self.store)
        with self.assertRaisesRegex(UserError, "one of your stores"):
            self.Member._ocd_add(self.brenda, "Paul", "+237677001122", self.env["ocd.vendor.place"])
        # In the team of another vendor: refused
        fatou_store = self.Place._ocd_vendor_create(self.fatou, {
            "name": "Karité Makepe", "kind": "store", "district_id": self.makepe.id, "city_id": self.douala.id,
            "latitude": 4.07, "longitude": 9.75,
        })
        with self.assertRaisesRegex(UserError, "another vendor"):
            self.Member._ocd_add(self.fatou, "Aïcha", "+237699123456", fatou_store)
        # Another store of the vendor, then removed: she no longer opens anything
        aicha._ocd_move(self.market)
        self.assertEqual(aicha.place_id, self.market)
        with self.assertRaises(UserError):
            aicha._ocd_move(fatou_store)
        aicha._ocd_remove()
        self.assertFalse(aicha.active)
        self.assertFalse(self.Member._ocd_of_partner(aicha.partner_id))
        # Added again: the same person, her history kept
        again = self._aicha()
        self.assertEqual(again, aicha)
        self.assertTrue(again.active)

    def test_five_at_most_and_business_only(self):
        self.brenda.ocd_team_max = 2
        self._aicha()
        self.Member._ocd_add(self.brenda, "Paul Eto'o", "+237677001122", self.market)
        with self.assertRaisesRegex(UserError, "2 people at most"):
            self.Member._ocd_add(self.brenda, "Rose", "+237677001133", self.store)
        self.brenda.ocd_team_max = 0
        self.assertEqual(self.brenda._ocd_team_allowed(), 5, "The setting of OCD Live")
        # OCD Business ended: paused, nothing deleted, nobody added
        self.company.ocd_business_offered_all = False
        self.brenda.ocd_business_until = fields.Date.subtract(fields.Date.today(), days=1)
        team = self.brenda.ocd_team_ids
        self.assertEqual(len(team), 2)
        self.assertEqual(set(team.mapped("state")), {"paused"})
        self.assertEqual(self.brenda._ocd_team_allowed(), 0)
        with self.assertRaisesRegex(UserError, "OCD Business"):
            self.Member._ocd_add(self.brenda, "Rose", "+237677001133", self.store)
        # Back with the formula
        self.brenda.ocd_business_until = fields.Date.add(fields.Date.today(), days=30)
        self.assertEqual(set(team.mapped("state")), {"waiting"})
        # The back office checks the same rules
        with self.assertRaises(ValidationError):
            self.Member.create({"name": "Junior", "vendor_id": self.brenda.id, "partner_id": self.courier.id,
                                "place_id": self.store.id})

    # === THE PAGE OF THE VENDOR === #

    def test_my_team_page(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn('href="/ocd/espace/moi/equipe"', page)
        page = self.url_open("/ocd/espace/moi/equipe").text
        self.assertIn("No one yet", page)
        self.assertIn("Brenda Wax Akwa", page)
        self.assertIn("offered during the launch", page)
        response = self._post("/ocd/espace/moi/equipe", name="Aïcha Njoya", phone="699 12 34 56",
                              country_id=self.cameroon.id, place_id=self.store.id)
        aicha = self.Member.search([("vendor_id", "=", self.brenda.id)])
        self.assertTrue(response.url.endswith(f"/ocd/espace/moi/equipe?ajoute={aicha.id}"))
        self.assertIn("Aïcha is in your team: her link left on WhatsApp", response.text)
        self.assertIn("Not come yet", response.text)
        self.assertIn("1 person out of 5", response.text)
        # A wrong number keeps what was typed
        response = self._post("/ocd/espace/moi/equipe", name="Paul", phone="12", country_id=self.cameroon.id,
                              place_id=self.market.id)
        self.assertIn("o_ocd_alert", response.text)
        self.assertIn('value="Paul"', response.text)
        # Her link again: once a minute at most
        aicha.partner_id.ocd_link_sent_at = False
        response = self._post(f"/ocd/espace/moi/equipe/{aicha.id}/lien")
        self.assertIn("Her link left on WhatsApp", response.text)
        response = self._post(f"/ocd/espace/moi/equipe/{aicha.id}/lien")
        self.assertIn("less than a minute ago", response.text)
        # Without WhatsApp: the vendor sends her link from their own WhatsApp
        with patch.object(self.MemberClass, "_ocd_link_sent", lambda member: False):
            aicha.partner_id.ocd_link_sent_at = False
            aicha.invited_at = False
            response = self._post(f"/ocd/espace/moi/equipe/{aicha.id}/lien")
        self.assertIn("https://wa.me/237699123456?text=", response.text)
        # Another store, then removed
        self._post(f"/ocd/espace/moi/equipe/{aicha.id}/magasin", place_id=self.market.id)
        self.assertEqual(aicha.place_id, self.market)
        response = self._post(f"/ocd/espace/moi/equipe/{aicha.id}/retirer")
        self.assertIn("Removed", response.text)
        self.assertFalse(aicha.active)
        # The team of another vendor: not found
        paul = self.Member._ocd_add(self.brenda, "Paul", "+237677001122", self.store)
        self.url_open("/ocd/deconnexion", data={"csrf_token": self.csrf_token()})
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.fatou._ocd_get_space_token()}")
        self.assertEqual(self._post(f"/ocd/espace/moi/equipe/{paul.id}/retirer").status_code, 404)
        self.assertTrue(paul.active)

    # === HER SPACE === #

    def test_she_logs_in_with_a_code(self):
        aicha = self._aicha()
        self.company.ocd_vendor_login = "whatsapp_code"
        self.authenticate(None, None)
        # Her link leads to the page of the number in the code mode
        response = self.url_open(f"/ocd/mon-magasin/{aicha.partner_id._ocd_get_space_token()}")
        self.assertTrue(response.url.endswith("/ocd/mon-magasin/connexion"))
        self.assertIn("Your store.", response.text)
        sent = []
        with patch.object(self.Partner, "_ocd_deliver_login_code", lambda partner, code: sent.append((partner, code)) or True):
            response = self._post("/ocd/mon-magasin/connexion", phone="699 12 34 56", country_id=self.cameroon.id)
        self.assertEqual([partner for partner, _code in sent], [aicha.partner_id])
        self.assertIn("Open my store", response.text)
        response = self._post("/ocd/mon-magasin/code", code=sent[0][1])
        self.assertTrue(response.url.endswith("/ocd/mon-magasin"))
        self.assertIn("Hello Aïcha", response.text)
        self.assertIn("Brenda Wax Akwa", response.text)
        self.assertIn("The stock of the store", response.text)
        self.assertTrue(aicha.last_visit)
        # « Me » of the menu leads her to her store, never to a space of vendor
        self.assertTrue(self.url_open("/ocd/espace/moi").url.endswith("/ocd/mon-magasin"))
        # The page of the vendors also answers her number
        self.url_open("/ocd/mon-magasin/deconnexion", data={"csrf_token": self.csrf_token()})
        sent.clear()
        with patch.object(self.Partner, "_ocd_deliver_login_code", lambda partner, code: sent.append((partner, code)) or True):
            self._post("/ocd/connexion", phone="699 12 34 56", country_id=self.cameroon.id)
        self.assertEqual([partner for partner, _code in sent], [aicha.partner_id])
        response = self._post("/ocd/connexion/code", code=sent[0][1])
        self.assertTrue(response.url.endswith("/ocd/mon-magasin"))
        # Removed from the team: her phone asks for the number again
        aicha._ocd_remove()
        self.assertTrue(self.url_open("/ocd/mon-magasin").url.endswith("/ocd/mon-magasin/connexion"))

    def test_her_link_and_the_pause(self):
        aicha = self._aicha()
        token = aicha.partner_id._ocd_get_space_token()
        self.authenticate(None, None)
        # Her personal link never opens a space of vendor
        self.assertEqual(self.url_open(f"/ocd/espace/{token}").status_code, 404)
        self._open_her_space(aicha)
        # The cookie of her phone opens her space again when the session of Odoo is lost
        self.opener.cookies.set("session_id", None)
        self.assertIn("Hello Aïcha", self.url_open("/ocd/mon-magasin").text)
        # Paused: she is told, her pages are closed
        self.company.ocd_business_offered_all = False
        page = self.url_open("/ocd/mon-magasin").text
        self.assertIn("The team of Brenda Wax is paused", page)
        self.assertNotIn("The stock of the store", page)
        self.assertIn("The team of Brenda Wax is paused", self.url_open("/ocd/mon-magasin/stock").text)
        self.assertTrue(self.url_open("/ocd/livrer/moi").url.endswith("/ocd/mon-magasin"))
        # A new personal link ends the phones opened with the old one
        self.company.ocd_business_offered_all = True
        aicha.partner_id.action_ocd_reset_space_link()
        self.opener.cookies.set("session_id", None)
        self.assertTrue(self.url_open("/ocd/mon-magasin").url.endswith("/ocd/mon-magasin/connexion"))

    def test_her_whatsapp_choice_and_the_buttons_of_her_messages(self):
        aicha = self._aicha()
        token = aicha.partner_id._ocd_get_space_token()
        self.authenticate(None, None)
        # The button of a message opens the page it speaks of
        response = self.url_open(f"/ocd/mon-magasin/{token}?vers=stock")
        self.assertTrue(response.url.endswith("/ocd/mon-magasin/stock"))
        self.assertTrue(self.url_open(f"/ocd/mon-magasin/{token}?vers=ailleurs").url.endswith("/ocd/mon-magasin"))
        # The news of her store: her choice, the same consent as everywhere
        aicha.partner_id.ocd_whatsapp_optin = False
        self.assertIn("Yes, tell me", self.url_open("/ocd/mon-magasin").text)
        self._post("/ocd/mon-magasin/whatsapp", oui="1")
        self.assertTrue(aicha.partner_id.ocd_whatsapp_optin)
        self.assertIn("Stop these messages", self.url_open("/ocd/mon-magasin").text)
        self._post("/ocd/mon-magasin/whatsapp", oui="0")
        self.assertFalse(aicha.partner_id.ocd_whatsapp_optin)

    def test_the_stock_of_her_store(self):
        aicha = self._aicha()
        bag = self._product("Sac en raphia", 8000, self.brenda)  # its stock is not counted
        self._open_her_space(aicha)
        page = self.url_open("/ocd/mon-magasin/stock").text
        self.assertIn("Robe en wax", page)
        self.assertIn("Sac en raphia", page)
        self.assertNotIn("12,000", page)
        self.assertNotIn("12 000", page)
        self.assertNotIn("Beurre de karite", page, "Only the products of her vendor")
        self.assertIn("Its stock is not counted", page)
        response = self._post("/ocd/mon-magasin/stock", variante=self.dress.id, delta=2)
        self.assertIn(f"#v-{self.dress.id}", response.url)
        self.assertEqual(self.dress._ocd_free_qty(self.store.location_id), 5)
        self.assertEqual(self.dress._ocd_free_qty(self.market.location_id), 2, "Only her store")
        move = self.env["stock.move"].search([("product_id", "=", self.dress.id), ("ocd_member_id", "=", aicha.id)])
        self.assertEqual(len(move), 1)
        # Her store only, the products of her vendor only, a stock not counted stays so
        self._post("/ocd/mon-magasin/stock", variante=bag.id, delta=3)
        self.assertFalse(bag.is_storable)
        self.assertEqual(self._post("/ocd/mon-magasin/stock", variante=self.butter.id, delta=1).status_code, 404)
        # The vendor sees who changed it
        self.url_open("/ocd/mon-magasin/deconnexion", data={"csrf_token": self.csrf_token()})
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open(f"/ocd/espace/moi/produits/{self.dress.product_tmpl_id.id}/mon-stock").text
        self.assertIn("by Aïcha Njoya", page)

    def test_the_parcels_of_her_store(self):
        aicha = self._aicha()
        self.brenda.ocd_vendor_collects = True
        # Picked up at her store by Estelle; one parcel of Fatou
        order = self._cart(self.estelle, [(self.dress, 1)])
        order._ocd_set_collect_places(self.store)
        rate = self.carrier_ocd.rate_shipment(order)
        order.set_delivery_line(self.carrier_ocd, rate["price"])
        order.action_confirm()
        parcel = self._parcel(order, self.brenda)
        self.assertEqual((parcel.ocd_collect, parcel.ocd_pickup_place_id), (True, self.store))
        self.assertIn(("parcel", aicha, parcel), self.told, "She learns there is a parcel to prepare")
        other = self._parcel(self._order(self.herve, [(self.butter, 1)]), self.fatou)
        self._open_her_space(aicha)
        self.assertIn("1 to prepare", self.url_open("/ocd/mon-magasin").text)
        page = self.url_open("/ocd/livrer/moi").text
        self.assertIn("Estelle comes to pick it up", page)
        self.assertIn("Brenda Wax Akwa · the store of Brenda Wax", page)
        self.assertNotIn("Beurre de karite", page)
        self.assertNotIn("you receive", page, "No payout")
        base = "/ocd/livrer/moi/colis"
        with patch.object(type(parcel), "_ocd_notify_customer", lambda pickings, event: None):
            response = self._post(f"{base}/{parcel.id}/ready")
        self.assertEqual(parcel.ocd_stage, "ready")
        self.assertIn("receives the code on WhatsApp", response.text)
        self.assertTrue(any("Done by Aïcha Njoya" in str(body) for body in parcel.message_ids.mapped("body")))
        # At the counter: the cash goes to her vendor, then the code of the customer
        self._post(f"{base}/{parcel.id}/collect", method="cash")
        self.assertEqual((parcel.ocd_cod_state, parcel.ocd_cod_collected_by_id), ("collected", self.brenda))
        response = self._post(f"{base}/{parcel.id}/code", code=parcel.sudo().ocd_delivery_code)
        self.assertEqual(parcel.ocd_stage, "delivered")
        self.assertIn("collected in cash", response.text)
        self.assertNotIn("next payout", response.text)
        # Another store, another vendor: not found
        self.assertEqual(self._post(f"{base}/{other.id}/ready").status_code, 404)

    def test_the_pieces_to_try_at_her_store(self):
        aicha = self._aicha()
        self.dress.product_tmpl_id.is_published = True
        Hold = self.env["ocd.product.hold"]
        with patch.object(type(Hold), "_ocd_notify_customer", lambda holds, event: None):
            hold = Hold._ocd_request(self.store, self.dress, self.estelle)
            elsewhere = Hold._ocd_request(self.market, self.dress, self.herve)
            self.assertIn(("hold", aicha, hold), self.told)
            self._open_her_space(aicha)
            page = self.url_open("/ocd/livrer/moi?vue=essayer").text
            self.assertIn("Estelle wants to try it", page)
            self.assertNotIn("Herve", page, "Only her store")
            self._post(f"/ocd/livrer/moi/essai/{hold.id}/accept")
            self.assertEqual((hold.state, hold.ocd_member_id), ("accepted", aicha))
            self.assertEqual(self._post(f"/ocd/livrer/moi/essai/{elsewhere.id}/accept").status_code, 404)
            self.assertEqual(self._post(f"/ocd/livrer/moi/essai/{hold.id}/unblock").status_code, 404)

    def test_the_back_office(self):
        aicha = self._aicha()
        action = aicha.action_ocd_send_link()
        self.assertEqual(action["params"]["message"], "The link was sent on WhatsApp.")
        with patch.object(self.MemberClass, "_ocd_link_sent", lambda member: False):
            action = aicha.action_ocd_send_link()
        self.assertIn(f"/ocd/mon-magasin/{aicha.partner_id._ocd_get_space_token()}", action["params"]["message"])
        self.assertTrue(re.search(r"People in the team", str(self.env["ocd.live.settings"]._ocd_sections())))
