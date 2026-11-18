from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdPromo(HttpCase, OcdShopCommon):
    """The promo price (plan, 3.1; chantier 7, design ProgrammeSoirees): lower than the lowest price
    of the last days, until a date, applied where Odoo computes every price."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_promo_max_discount": 50, "ocd_promo_max_days": 30, "ocd_promo_reference_days": 14})
        cls.Promo = cls.env["ocd.product.promo"]
        cls.robe = cls.dress.product_tmpl_id
        (cls.robe | cls.butter.product_tmpl_id).write({
            "ocd_review_state": "approved", "is_published": True, "website_published": True,
        })

    def _put(self, product, price, days=14, **kwargs):
        return self.Promo._ocd_put(product, price, fields.Datetime.now() + timedelta(days=days), **kwargs)

    def _pricelist_price(self, product, **context):
        pricelist = self.env["product.pricelist"].create({"name": "Test", "currency_id": self.company.currency_id.id})
        return pricelist._get_product_price(product.with_context(**context), 1.0)

    # === THE RULES === #

    def test_the_rules_of_a_promo(self):
        with self.assertRaisesRegex(UserError, "under"):
            self._put(self.robe, 12000)
        with self.assertRaisesRegex(UserError, "50 % of discount at most"):
            self._put(self.robe, 5000)
        with self.assertRaisesRegex(UserError, "30 days at most"):
            self._put(self.robe, 9000, days=40)
        promo = self._put(self.robe, 9000)
        self.assertEqual((promo.reference_price, promo.discount, promo.state), (12000, 25, "running"))
        self.assertEqual(promo._ocd_off_text(), "-25 %")
        # One promo at a time: a new one replaces it
        second = self._put(self.robe, 10000)
        self.assertFalse(promo.active)
        self.assertEqual(promo.stop_reason, "Replaced by a new promo.")
        self.assertEqual(self.Promo._ocd_running(self.robe)[self.robe.id], second)
        # A product not on sale yet has no promo
        waiting = self._product("Pagne", 18000, self.brenda).product_tmpl_id
        waiting.ocd_review_state = "to_check"
        with self.assertRaisesRegex(UserError, "not on sale yet"):
            self._put(waiting, 15000)

    def test_a_price_raised_just_before_does_not_make_a_promo(self):
        """The price struck through is the lowest price of the last 14 days."""
        self.robe.list_price = 15000
        self.assertEqual(self.robe._ocd_reference_price(), 12000)
        with self.assertRaisesRegex(UserError, r"under .*12,000"):
            self._put(self.robe, 12000)
        promo = self._put(self.robe, 10000)
        self.assertEqual((promo.reference_price, promo.discount), (12000, 17))
        with freeze_time(fields.Datetime.now() + timedelta(days=15)):
            self.assertEqual(self.robe._ocd_reference_price(), 15000, "The 14 days passed")
        # A price lowered under the promo ends it
        self.robe.list_price = 9500
        self.assertFalse(promo.active)
        self.assertIn("went under the price of the promo", promo.stop_reason)

    # === THE PRICE EVERYWHERE === #

    def test_the_price_of_the_promo_everywhere(self):
        self.assertEqual(self._pricelist_price(self.dress), 12000)
        promo = self._put(self.robe, 9000, days=3)
        self.assertEqual(self._pricelist_price(self.dress), 9000, "The pricelists start from the price of the promo")
        self.assertEqual(self._pricelist_price(self.robe), 9000)
        self.assertEqual(self._pricelist_price(self.dress, ocd_without_promo=True), 12000)
        self.assertEqual(self.robe._ocd_on_sale_price(), (9000, 12000))
        # An order: the price of the promo, the commission on the price paid
        order = self.env["sale.order"].create({
            "partner_id": self.estelle.id,
            "order_line": [Command.create({"product_id": self.dress.id, "product_uom_qty": 2, "tax_ids": [Command.clear()]})],
        })
        line = order.order_line
        self.assertEqual((line.price_unit, line.ocd_promo_id), (9000, promo))
        self.assertEqual(line.ocd_vendor_share, 15300, "85 % of 18,000")
        # After the end: the promo keeps a little while the order is paid, then the price of now
        with freeze_time(promo.date_end + timedelta(minutes=30)):
            self.assertEqual(self._pricelist_price(self.dress), 12000, "A new cart pays the price of now")
            order._recompute_prices()
            self.assertEqual(line.price_unit, 9000, "Started during the promo, paid in the time to pay")
            self.assertFalse(order._ocd_refresh_promos())
        with freeze_time(promo.date_end + timedelta(hours=3)):
            self.assertEqual(order._ocd_refresh_promos(), self.robe)
            self.assertEqual((line.price_unit, line.ocd_promo_id.id), (12000, False))

    def test_the_sizes_and_the_colours_in_promo(self):
        """An extra price of a size follows the promo in the same proportion."""
        size = self.env["product.attribute"].create({"name": "Taille test", "create_variant": "always"})
        values = self.env["product.attribute.value"].create([{"name": "M", "attribute_id": size.id},
                                                             {"name": "XL", "attribute_id": size.id}])
        product = self._product("Robe longue", 10000, self.brenda).product_tmpl_id
        product.write({"ocd_review_state": "approved", "attribute_line_ids": [
            Command.create({"attribute_id": size.id, "value_ids": [Command.set(values.ids)]})]})
        xl_value = product.attribute_line_ids.product_template_value_ids.filtered(lambda v: v.name == "XL")
        xl_value.price_extra = 2000
        xl = product.product_variant_ids.filtered(lambda variant: xl_value in variant.product_template_attribute_value_ids)
        self.assertEqual(self._pricelist_price(xl), 12000)
        self._put(product, 8000)
        self.assertEqual(self._pricelist_price(xl), 9600, "-20 % on the extra price too")

    # === THE PAGES === #

    def test_the_pages_show_the_promo(self):
        self._put(self.robe, 9000)
        self.authenticate(None, None)
        page = self.url_open("/shop").text
        self.assertIn("-25 %", page)
        self.assertIn("o_ocd_product_was", page)
        self.assertIn("In promo", page, "The filter of the shop")
        page = self.url_open("/shop?promo=1").text
        self.assertIn("Robe en wax", page)
        self.assertNotIn("Beurre de karite", page, "Only the products in promo")
        page = self.url_open(self.robe.website_url).text
        self.assertIn("Promo until", page)
        self.assertIn("o_ocd_variant_was", page)
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn("-25 %", page)
        tile = self.env["ocd.live.regie"]._ocd_product_tile(self.env["ocd.live.booking"], self.robe)
        self.assertIn("9,000", tile["price"])
        self.assertIn("12,000", tile["was"])

    def test_the_vendor_puts_a_product_in_promo(self):
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open(f"/ocd/espace/moi/produits/{self.robe.id}/promo").text
        self.assertIn("Put in promo", page)
        self.assertIn("-25 %", page)
        response = self.url_open(f"/ocd/espace/moi/produits/{self.robe.id}/promo", data={
            "csrf_token": self.csrf_token(), "percent": "25", "days": "7",
        })
        self.assertIn("Done: your promo is shown at once.", response.text)
        promo = self.Promo._ocd_running(self.robe)[self.robe.id]
        self.assertEqual((promo.price, promo.source), (9000, "vendor"))
        self.assertGreater(promo.date_end, fields.Datetime.now() + timedelta(days=5))
        self.assertLessEqual(promo.date_end, fields.Datetime.now() + timedelta(days=7))
        self.assertIn("In promo now", response.text)
        page = self.url_open(f"/ocd/espace/moi/produits/{self.robe.id}/promo", data={
            "csrf_token": self.csrf_token(), "percent": "autre", "price": "4 000", "days": "7",
        }).text
        self.assertIn("50 % of discount at most", page)
        self.url_open(f"/ocd/espace/moi/produits/{self.robe.id}/promo/arreter", data={"csrf_token": self.csrf_token()})
        self.assertFalse(promo.active)
        page = self.url_open("/ocd/espace/moi/produits").text
        self.assertIn(f"/ocd/espace/moi/produits/{self.robe.id}/promo", page)
        # Another vendor does not reach it
        self.assertEqual(self.url_open(
            f"/ocd/espace/moi/produits/{self.butter.product_tmpl_id.id}/promo").status_code, 404)

