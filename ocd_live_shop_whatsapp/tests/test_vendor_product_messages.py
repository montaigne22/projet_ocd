from odoo.tests import HttpCase, tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorProductMessages(HttpCase, OcdShopCommon):
    """The messages about the products of a vendor (accepted, refused with its reason, stock
    low), written now to be approved by Meta before they are sent."""

    def test_the_messages_render_and_their_button_opens_my_products(self):
        self.company.ocd_vendor_login = "link"
        reason = self.env.ref("ocd_live_shop.refuse_reason_product_photo")
        skirt = self.env["product.template"].create({
            "name": "Jupe wax", "list_price": 8000, "is_storable": True, "ocd_vendor_id": self.brenda.id,
            "ocd_review_state": "to_check",
        })
        skirt._ocd_set_stock(2)
        skirt.action_ocd_refuse(reason)
        for xmlid in ("template_product_accepted", "template_product_refused", "template_stock_low"):
            for suffix in ("", "_en"):
                template = self.env.ref(f"ocd_live_shop_whatsapp.{xmlid}{suffix}")
                with self.subTest(template=template.name):
                    values = [template._render(variable.value, skirt)[skirt.id] for variable in template.variable_ids]
                    self.assertTrue(all(values), values)
                    self.assertEqual(values[0], "Brenda Wax")
                    path = template._render(template.button_url_value, skirt)[skirt.id]
                    self.assertEqual(path, f"ocd/espace/{self.brenda.ocd_space_token}/produits")
        stock = self.env.ref("ocd_live_shop_whatsapp.template_stock_low")
        self.assertEqual(stock._render(stock.variable_ids[1].value, skirt)[skirt.id], "2")
        # The button: the personal link opens « My products » on the phone
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/espace/{self.brenda.ocd_space_token}/produits")
        self.assertEqual(response.url.split("?")[0].removeprefix(self.base_url()), "/ocd/espace/moi/produits")
        self.assertIn("Jupe wax", response.text)
        response = self.url_open("/ocd/espace/not-a-good-link-at-all/produits", allow_redirects=False)
        self.assertIn("/ocd/connexion", response.headers["Location"])
