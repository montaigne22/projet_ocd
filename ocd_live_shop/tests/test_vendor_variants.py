from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon
from .test_shop_pages import PNG


@tagged("post_install", "-at_install")
class TestOcdVendorVariants(HttpCase, OcdShopCommon):
    """Sizes and colours from the creation (chantier 21, 3.5 of the plan of « My products »,
    design TaillesCouleurs): the values the team offers, the stock of each choice, a size or a
    colour added to a product on sale."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        Attribute = cls.env["product.attribute"]
        Attribute.search([]).ocd_for_vendors = False
        cls.size = Attribute.create({"name": "Taille OCD", "display_type": "pills", "create_variant": "always",
                                     "ocd_for_vendors": True, "value_ids": [(0, 0, {"name": n}) for n in ("M", "L", "XL")]})
        cls.colour = Attribute.create({"name": "Couleur OCD", "display_type": "color", "create_variant": "always",
                                       "ocd_for_vendors": True, "value_ids": [
                                           (0, 0, {"name": "Bleu", "html_color": "#1F4FA3"}),
                                           (0, 0, {"name": "Rouge", "html_color": "#C8102E"}),
                                       ]})
        cls.m, cls.l, cls.xl = cls.size.value_ids
        cls.blue, cls.red = cls.colour.value_ids

    def _key(self, *values):
        return "stock_" + "-".join(str(value_id) for value_id in sorted(value.id for value in values))

    def _open_space(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")

    def test_the_team_offers_sizes_and_colours(self):
        Attribute = self.env["product.attribute"]
        self.assertEqual(Attribute._ocd_vendor_attributes(), self.size | self.colour)
        Attribute.search([]).ocd_for_vendors = False
        size, colour = self.env.ref("product.pa_size"), self.env.ref("product.pa_color")
        Attribute._ocd_init_vendor_attributes()
        self.assertTrue(size.ocd_for_vendors and colour.ocd_for_vendors)
        self.assertTrue(size.value_ids and colour.value_ids)
        counts = (len(size.value_ids), len(colour.value_ids))
        Attribute._ocd_init_vendor_attributes()
        self.assertEqual((len(size.value_ids), len(colour.value_ids)), counts, "Never twice")

    def test_a_new_product_with_its_sizes_and_colours(self):
        self._open_space()
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn("Several sizes or colours", page)
        self.assertIn("Couleur OCD", page)
        form = {"csrf_token": self.csrf_token(), "name": "Robe sur mesure", "price": "12000", "quantity": "1",
                "variantes": "1"}
        # Nothing ticked
        page = self.url_open("/ocd/espace/moi/produits", data=form, files={"photo": ("robe.png", PNG, "image/png")}).text
        self.assertIn("Tick at least one size or one colour.", page)
        # Ticked, without the grid (no JavaScript): the grid comes, to fill in
        ticked = {**form, "valeurs": [self.m.id, self.l.id, self.blue.id, self.red.id]}
        page = self.url_open("/ocd/espace/moi/produits", data=ticked, files={"photo": ("robe.png", PNG, "image/png")}).text
        self.assertIn("Write how many you have of each choice.", page)
        self.assertIn(f'name="{self._key(self.m, self.blue)}"', page)
        self.assertFalse(self.env["product.template"].search([("name", "=", "Robe sur mesure")]))
        stock = {self._key(self.m, self.blue): "3", self._key(self.l, self.blue): "2",
                 self._key(self.m, self.red): "1", self._key(self.l, self.red): "0"}
        response = self.url_open("/ocd/espace/moi/produits", data={**ticked, **stock},
                                 files={"photo": ("robe.png", PNG, "image/png")}, allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:300])
        self.assertIn("couleurs=", response.headers["Location"])
        product = self.env["product.template"].search([("name", "=", "Robe sur mesure")])
        self.assertEqual(len(product.product_variant_ids), 4)
        self.assertEqual(product.ocd_review_state, "to_check")
        free = product.product_variant_ids._ocd_free_qties()
        by_values = {frozenset(v.product_template_attribute_value_ids.product_attribute_value_id.ids): free[v.id]
                     for v in product.product_variant_ids}
        self.assertEqual(by_values[frozenset((self.m | self.blue).ids)], 3)
        self.assertEqual(by_values[frozenset((self.l | self.red).ids)], 0)
        self.assertEqual(sum(free.values()), 6)
        page = self.url_open(response.headers["Location"]).text
        self.assertIn("Add the photo of each colour", page)
        self.assertIn("M, L · Bleu, Rouge", page)

    def test_a_size_added_to_a_product_on_sale(self):
        template = self.env["product.template"].create({
            "name": "Pagne", "list_price": 5000, "ocd_vendor_id": self.brenda.id, "is_storable": True,
            "ocd_review_state": "approved", "is_published": True, "sale_ok": True,
            "attribute_line_ids": [(0, 0, {"attribute_id": self.size.id, "value_ids": [(6, 0, (self.m | self.l).ids)]}),
                                   (0, 0, {"attribute_id": self.colour.id, "value_ids": [(6, 0, self.blue.ids)]})],
        })
        self.assertEqual(template._ocd_vendor_addable_values(), {self.size: self.xl, self.colour: self.red})
        with self.assertRaises(UserError):
            template._ocd_vendor_add_values(self.env["product.attribute.value"])
        self._open_space()
        page = self.url_open(f"/ocd/espace/moi/produits/{template.id}/modifier").text
        self.assertIn("Add a size or a colour", page)
        response = self.url_open(f"/ocd/espace/moi/produits/{template.id}/tailles",
                                 data={"csrf_token": self.csrf_token(), "valeurs": [self.xl.id, self.red.id]},
                                 allow_redirects=False)
        self.assertIn("ajoute=", response.headers["Location"])
        self.assertEqual(len(template.product_variant_ids), 6, "3 sizes × 2 colours")
        self.assertEqual(sum(template.product_variant_ids._ocd_free_qties().values()), 0, "Without stock")
        page = self.url_open(response.headers["Location"]).text
        self.assertIn("Added:", page)
        self.assertNotIn("Add a size or a colour", page, "Nothing left to add")
