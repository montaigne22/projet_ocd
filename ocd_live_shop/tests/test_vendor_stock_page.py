from odoo import Command
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorStockPage(HttpCase, OcdShopCommon):
    """« My stock » (chantier 18): the sizes and the colours of a product, in each place of the
    vendor, changed with − and +."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_vendor_login": "link", "ocd_business_offered_all": True, "ocd_vendor_places_max": 5,
                           "ocd_place_check": False})
        cls.akwa = cls.env.ref("delivery_cameroon.district_douala_akwa")
        cls.bonapriso = cls.env.ref("delivery_cameroon.district_douala_bonapriso")
        cls.dress.write({"is_storable": True, "allow_out_of_stock_order": False})
        colour = cls.env["product.attribute"].create({"name": "Couleur", "display_type": "color", "value_ids": [
            Command.create({"name": "Bleu", "html_color": "#2F6FB8"}), Command.create({"name": "Rouge", "html_color": "#C4162A"}),
        ]})
        size = cls.env["product.attribute"].create({"name": "Taille", "value_ids": [
            Command.create({"name": "S"}), Command.create({"name": "M"}),
        ]})
        cls.shirt = cls.env["product.template"].create({
            "name": "Chemise wax", "list_price": 9000, "ocd_vendor_id": cls.brenda.id, "is_storable": True,
            "allow_out_of_stock_order": False,
            "attribute_line_ids": [
                Command.create({"attribute_id": colour.id, "value_ids": [Command.set(colour.value_ids.ids)]}),
                Command.create({"attribute_id": size.id, "value_ids": [Command.set(size.value_ids.ids)]}),
            ],
        })

    def _place(self, name, district):
        return self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": name, "kind": "store", "district_id": district.id, "city_id": district.city_id.id,
        })

    def _variant(self, colour, size):
        return self.shirt.product_variant_ids.filtered(
            lambda v: set(v.product_template_attribute_value_ids.mapped("name")) == {colour, size}
        )

    def _login(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")

    def test_one_place_the_sizes_and_the_colours(self):
        self.dress._ocd_set_free_stock(3)
        self._place("Brenda Wax Akwa", self.akwa)
        self._login()
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn(f'href="/ocd/espace/moi/produits/{self.shirt.id}/mon-stock"', page, "Sizes and colours: « My stock »")
        self.assertIn(f'action="/ocd/espace/moi/produits/{self.dress.product_tmpl_id.id}/stock"', page,
                      "One size in one place: the − and + stay in the list")
        page = self.url_open(f"/ocd/espace/moi/produits/{self.shirt.id}/mon-stock").text
        self.assertIn("Chemise wax", page)
        self.assertNotIn("o_ocd_stock_places", page, "One place: nothing to choose")
        blue_m = self._variant("Bleu", "M")
        response = self.url_open(f"/ocd/espace/moi/produits/{self.shirt.id}/mon-stock", allow_redirects=False,
                                 data={"csrf_token": self.csrf_token(), "variante": blue_m.id, "delta": "2"})
        self.assertTrue(response.headers["Location"].endswith(f"#v-{blue_m.id}"))
        self.assertEqual(blue_m._ocd_free_qty(), 2)
        page = self.url_open(f"/ocd/espace/moi/produits/{self.shirt.id}/mon-stock").text
        self.assertIn("Bleu M: +2 at Brenda Wax Akwa", page, "The last changes")

    def test_two_places_side_by_side(self):
        self.dress._ocd_set_free_stock(5)
        akwa = self._place("Brenda Wax Akwa", self.akwa)
        bonapriso = self._place("Brenda Wax Bonapriso", self.bonapriso)
        self._login()
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn("5 in stock · Brenda Wax Akwa 5 · Brenda Wax Bonapriso 0", page)
        self.assertIn("My stock by store", page)
        self.assertNotIn(f'action="/ocd/espace/moi/produits/{self.dress.product_tmpl_id.id}/stock"', page,
                         "Two places: the stock is changed place by place")
        url = f"/ocd/espace/moi/produits/{self.dress.product_tmpl_id.id}/mon-stock"
        page = self.url_open(f"{url}?magasin={bonapriso.id}").text
        self.assertIn("o_ocd_stock_places", page)
        self.assertRegex(page, rf'magasin={bonapriso.id}"\s+class="o_ocd_on"')
        self.assertIn("<b>Sold out here</b> · 5 at Brenda Wax Akwa", page)
        variant = self.dress
        self.url_open(url, data={"csrf_token": self.csrf_token(), "variante": variant.id, "lieu": bonapriso.id, "delta": "3"})
        self.assertEqual(self.brenda._ocd_free_pieces(bonapriso.location_id).get(variant), 3)
        self.assertEqual(self.brenda._ocd_free_pieces(akwa.location_id).get(variant), 5)
        # Never below 0, never the place of another vendor
        self.url_open(url, data={"csrf_token": self.csrf_token(), "variante": variant.id, "lieu": bonapriso.id, "delta": "-9"})
        self.assertFalse(self.brenda._ocd_free_pieces(bonapriso.location_id).get(variant))
        fatou_place = self.env["ocd.vendor.place"]._ocd_vendor_create(self.fatou, {
            "name": "Fatou Akwa", "kind": "store", "district_id": self.akwa.id, "city_id": self.akwa.city_id.id,
        })
        self.url_open(url, data={"csrf_token": self.csrf_token(), "variante": variant.id, "lieu": fatou_place.id, "delta": "1"})
        self.assertFalse(self.fatou._ocd_free_pieces(fatou_place.location_id), "Not in the place of another vendor")
        self.assertEqual(self.url_open(f"/ocd/espace/moi/produits/{self.butter.product_tmpl_id.id}/mon-stock").status_code, 404)
