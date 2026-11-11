from odoo.fields import Command
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeliveryCameroon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cameroon = cls.env.ref("base.cm")
        cls.douala = cls.env.ref("delivery_cameroon.city_cm_douala")
        cls.yaounde = cls.env.ref("delivery_cameroon.city_cm_yaounde")
        cls.kribi = cls.env.ref("delivery_cameroon.city_cm_kribi")
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        cls.bonaberi = cls.env.ref("delivery_cameroon.district_douala_bonaberi")
        cls.product = cls.env["product.product"].create({"name": "Delivery", "type": "service"})
        cls.carrier = cls.env["delivery.carrier"].create({
            "name": "Test carrier",
            "delivery_type": "fixed",
            "product_id": cls.product.id,
        })

    def _partner(self, **vals):
        return self.env["res.partner"].create({"name": "Client", "country_id": self.cameroon.id, **vals})

    def test_regions_cities_and_districts_are_loaded(self):
        self.assertEqual(len(self.cameroon.state_ids), 10)
        self.assertEqual(self.douala.state_id, self.env.ref("delivery_cameroon.state_cm_lt"))
        self.assertIn(self.akwa, self.douala.district_ids)
        self.assertTrue(self.cameroon.enforce_cities)
        self.assertTrue(self.cameroon._enforce_city_choice())

    def test_address_form_fields(self):
        # The portal address form must work with the Cameroonian address format (no zip code).
        fields_list = self.cameroon._get_address_fields()
        self.assertIn("city_id", fields_list)
        self.assertIn("state_id", fields_list)
        self.assertNotIn("zip", fields_list)

    def test_district_completes_city_and_region(self):
        partner = self._partner(district_id=self.akwa.id)
        self.assertEqual(partner.city_id, self.douala)
        self.assertEqual(partner.city, "Douala")
        self.assertEqual(partner.state_id, self.env.ref("delivery_cameroon.state_cm_lt"))

    def test_display_address_with_district_and_landmark(self):
        partner = self._partner(district_id=self.akwa.id, delivery_landmark="Face pharmacie du Port")
        address = partner._display_address(without_name=True)
        self.assertIn("Akwa", address)
        self.assertIn("Face pharmacie du Port", address)
        self.assertIn("Douala", address)

    def test_carrier_city_restriction(self):
        self.carrier.city_ids = [Command.set([self.douala.id])]
        self.assertTrue(self.carrier._match_address(self._partner(city_id=self.douala.id)))
        self.assertFalse(self.carrier._match_address(self._partner(city_id=self.yaounde.id)))
        self.assertFalse(self.carrier._match_address(self._partner()))

    def test_carrier_district_restriction(self):
        self.carrier.district_ids = [Command.set([self.akwa.id])]
        self.assertTrue(self.carrier._match_address(self._partner(district_id=self.akwa.id)))
        self.assertFalse(self.carrier._match_address(self._partner(district_id=self.bonaberi.id)))

    def test_carrier_exclusions(self):
        self.carrier.write({
            "country_ids": [Command.set([self.cameroon.id])],
            "excluded_city_ids": [Command.set([self.douala.id])],
        })
        self.assertFalse(self.carrier._match_address(self._partner(city_id=self.douala.id)))
        self.assertTrue(self.carrier._match_address(self._partner(city_id=self.kribi.id)))

        international = self.carrier.copy({
            "country_ids": [Command.clear()],
            "excluded_city_ids": [Command.clear()],
            "excluded_country_ids": [Command.set([self.cameroon.id])],
        })
        france = self.env["res.partner"].create({"name": "Client", "country_id": self.env.ref("base.fr").id})
        self.assertFalse(international._match_address(self._partner(city_id=self.kribi.id)))
        self.assertTrue(international._match_address(france))

    def test_mandatory_address_fields(self):
        Partner = self.env["res.partner"]
        fields_cm = Partner._get_mandatory_address_fields(self.cameroon, city_id=str(self.douala.id))
        self.assertNotIn("street", fields_cm)
        self.assertIn("delivery_landmark", fields_cm)
        self.assertIn("district_id", fields_cm)
        self.assertIn("city_id", fields_cm)
        fields_kribi = Partner._get_mandatory_address_fields(self.cameroon, city_id=str(self.kribi.id))
        self.assertNotIn("district_id", fields_kribi)
        fields_fr = Partner._get_mandatory_address_fields(self.env.ref("base.fr"))
        self.assertIn("street", fields_fr)
        self.assertNotIn("delivery_landmark", fields_fr)

    def test_preset_delivery_methods(self):
        douala_home = self.env.ref("delivery_cameroon.carrier_douala_home")
        other_cities = self.env.ref("delivery_cameroon.carrier_cameroon_other_cities")
        international = self.env.ref("delivery_cameroon.carrier_international")
        client_akwa = self._partner(district_id=self.akwa.id)
        client_kribi = self._partner(city_id=self.kribi.id)
        self.assertTrue(douala_home._match_address(client_akwa))
        self.assertFalse(other_cities._match_address(client_akwa))
        self.assertTrue(other_cities._match_address(client_kribi))
        self.assertFalse(international._match_address(client_kribi))
        self.assertTrue(douala_home.allow_cash_on_delivery)


@tagged("post_install", "-at_install")
class TestDistrictsRoute(HttpCase):

    def test_districts_route(self):
        douala = self.env.ref("delivery_cameroon.city_cm_douala")
        self.authenticate(None, None)
        districts = self.make_jsonrpc_request("/delivery_cameroon/districts", {"city_id": douala.id})
        names = [d["name"] for d in districts]
        self.assertIn("Akwa", names)
        self.assertIn("Bonapriso", names)
        kribi = self.env.ref("delivery_cameroon.city_cm_kribi")
        self.assertEqual(
            self.make_jsonrpc_request("/delivery_cameroon/districts", {"city_id": kribi.id}), []
        )
