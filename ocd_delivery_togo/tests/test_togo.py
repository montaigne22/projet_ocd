from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTogoAddresses(TransactionCase):

    def test_togo_like_cameroon(self):
        togo = self.env.ref("base.tg")
        lome = self.env.ref("ocd_delivery_togo.city_tg_lome")
        self.assertTrue(togo._enforce_city_choice())
        self.assertGreaterEqual(len(lome.district_ids), 30)
        Partner = self.env["res.partner"]
        fields_lome = Partner._get_mandatory_address_fields(togo, city_id=str(lome.id))
        self.assertIn("delivery_landmark", fields_lome)
        self.assertIn("district_id", fields_lome)
        self.assertNotIn("street", fields_lome)
        kara = self.env.ref("ocd_delivery_togo.city_tg_kara")
        self.assertNotIn("district_id", Partner._get_mandatory_address_fields(togo, city_id=str(kara.id)))

    def test_delivery_methods_of_togo(self):
        lome = self.env.ref("ocd_delivery_togo.city_tg_lome")
        be = self.env.ref("ocd_delivery_togo.district_lome_be")
        customer = self.env["res.partner"].create({
            "name": "Yawa",
            "country_id": self.env.ref("base.tg").id,
            "city_id": lome.id,
            "district_id": be.id,
            "delivery_landmark": "Pres du marche",
        })
        home = self.env.ref("ocd_delivery_togo.carrier_lome_home")
        other = self.env.ref("ocd_delivery_togo.carrier_togo_other_cities")
        self.assertTrue(home._match_address(customer))
        self.assertFalse(other._match_address(customer))
