from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon
from odoo.addons.ocd_live_shop.tests.test_shop_pages import PNG
from odoo.addons.whatsapp_cloud.models.whatsapp_template import WhatsappTemplate


@tagged("post_install", "-at_install")
class TestOcdVendorProductMessages(HttpCase, OcdShopCommon):
    """The messages about the products and the stores of a vendor (accepted, refused with its
    reason, stock low). A message leaves once Meta approved its template."""

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

    def _store(self):
        akwa = self.env.ref("delivery_cameroon.district_douala_akwa")
        self.company.write({"ocd_place_check": True, "ocd_business_offered_all": True})
        return self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {
            "name": "Brenda Wax Akwa", "kind": "store", "city_id": akwa.city_id.id, "district_id": akwa.id,
            "landmark": "En face de la pharmacie du Port", "latitude": 4.0511, "longitude": 9.6942,
            "photo": BinaryBytes(PNG, filename="devanture.png"),
        })

    def test_the_messages_of_a_store_open_my_stores(self):
        self.company.ocd_vendor_login = "link"
        store = self._store()
        store.action_ocd_refuse(self.env.ref("ocd_live_shop.refuse_reason_store_front"))
        for xmlid in ("template_store_accepted", "template_store_refused"):
            for suffix in ("", "_en"):
                template = self.env.ref(f"ocd_live_shop_whatsapp.{xmlid}{suffix}")
                with self.subTest(template=template.name):
                    values = [template._render(variable.value, store)[store.id] for variable in template.variable_ids]
                    self.assertTrue(all(values), values)
                    self.assertEqual(values[:2], ["Brenda Wax", "Brenda Wax Akwa"])
                    path = template._render(template.button_url_value, store)[store.id]
                    self.assertEqual(path, f"ocd/espace/{self.brenda.ocd_space_token}/magasins")
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/espace/{self.brenda.ocd_space_token}/magasins")
        self.assertEqual(response.url.split("?")[0].removeprefix(self.base_url()), "/ocd/espace/moi/magasins")
        self.assertIn("Brenda Wax Akwa", response.text)

    def test_the_vendor_is_told_once_what_the_team_checked(self):
        self.brenda.write({"ocd_whatsapp_optin": True, "whatsapp_opt_in": True})
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        Product = self.env["product.template"]
        products = Product.create([
            {"name": name, "ocd_vendor_id": self.brenda.id, "ocd_review_state": "to_check"} for name in ("Pagne", "Sac")
        ])
        with patch.object(WhatsappTemplate, "_send", fake_send):
            # Two products accepted at once: one message
            products.action_ocd_approve()
            products.action_ocd_refuse(self.env.ref("ocd_live_shop.refuse_reason_product_photo"))
            store = self._store()
            home = self.env["ocd.vendor.place"]._ocd_vendor_create(self.brenda, {"name": "Chez moi", "kind": "home"})
            store.action_ocd_approve()
            home.action_ocd_approve()
        self.assertEqual([name for name, _records in calls], ["ocd_produit_accepte", "ocd_produit_refuse", "ocd_magasin_accepte"])
        self.assertEqual(calls[0][1], products[0])
        # Paused by the team: nothing leaves
        calls.clear()
        self.env.ref("ocd_live_shop.automation_vendor_review").enabled = False
        with patch.object(WhatsappTemplate, "_send", fake_send):
            store.action_ocd_refuse(self.env.ref("ocd_live_shop.refuse_reason_store_front"))
        self.assertFalse(calls)

    def test_the_product_back_names_its_stores(self):
        """« Tell me when it is back » (chantier 18): the stores of the vendor where the product
        came back, once Meta approved this message; the message without the stores until then."""
        self.company.write({"ocd_business_offered_all": True, "ocd_vendor_places_max": 5, "ocd_place_check": False})
        Place = self.env["ocd.vendor.place"]
        akwa, bonapriso = (self.env.ref(f"delivery_cameroon.district_douala_{name}") for name in ("akwa", "bonapriso"))
        stores = Place.browse([Place._ocd_vendor_create(self.brenda, {
            "name": name, "kind": "store", "district_id": district.id, "city_id": district.city_id.id,
        }).id for name, district in (("Brenda Wax Akwa", akwa), ("Brenda Wax Bonapriso", bonapriso))])
        self.dress.write({"is_storable": True, "allow_out_of_stock_order": False})
        self.dress.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        Alert = self.env["ocd.stock.alert"]
        calls = []

        def fake_send(template, records):
            calls.append(template.template_name)
            return template.env["whatsapp.message"]

        in_store = self.env.ref("ocd_live_shop_whatsapp.template_product_back_in_store")
        for template in (in_store, self.env.ref("ocd_live_shop_whatsapp.template_product_back_in_store_en")):
            with self.subTest(template=template.name):
                alert = Alert._ocd_register(self.dress, phone="+237 670000009")
                self.dress._ocd_change_stock(1, stores[1].location_id)
                values = [template._render(variable.value, alert)[alert.id] for variable in template.variable_ids]
                self.assertEqual(values, ["Robe en wax", "Robe en wax", "Brenda Wax Bonapriso"])
                self.dress._ocd_change_stock(-1, stores[1].location_id)
                alert.unlink()
        with patch.object(WhatsappTemplate, "_send", fake_send):
            for status, expected in (("unknown", "ocd_produit_de_retour"), ("pending", "ocd_produit_de_retour"),
                                     ("approved", "ocd_produit_de_retour_magasin")):
                in_store.status = status
                Alert._ocd_register(self.dress, phone="+237 670000009")
                self.dress._ocd_change_stock(1, stores[0].location_id)
                Alert._ocd_send_back()
                self.assertEqual(calls[-1], expected, f"Message in store {status}")
                self.dress._ocd_change_stock(-1, stores[0].location_id)
            # Back at no store of the vendor: the message without the stores
            home = Place._ocd_vendor_create(self.brenda, {"name": "Chez moi", "kind": "home", "district_id": akwa.id})
            Alert._ocd_register(self.dress, phone="+237 670000009")
            self.dress._ocd_change_stock(1, home.location_id)
            Alert._ocd_send_back()
            self.assertEqual(calls[-1], "ocd_produit_de_retour")

    def test_the_vendor_is_told_about_a_change(self):
        """A change of a product on sale (chantier 19): accepted, the message of a product
        accepted; refused, its own message once Meta approved it (the message of a product
        refused would say it is not online)."""
        self.brenda.write({"ocd_whatsapp_optin": True, "whatsapp_opt_in": True})
        product = self.env["product.template"].create({
            "name": "Pagne", "ocd_vendor_id": self.brenda.id, "ocd_review_state": "approved", "is_published": True,
        })
        calls = []

        def fake_send(template, records):
            calls.append(template.template_name)
            return template.env["whatsapp.message"]

        reason = self.env.ref("ocd_live_shop.refuse_reason_product_photo")
        template = self.env.ref("ocd_live_shop_whatsapp.template_product_change_refused")
        with patch.object(WhatsappTemplate, "_send", fake_send):
            product._ocd_vendor_change("Pagne wax", product.list_price)
            product.action_ocd_approve_change()
            self.assertEqual(calls, ["ocd_produit_accepte"])
            product._ocd_vendor_change("Pagne", product.list_price)
            product.action_ocd_refuse_change(reason)
            self.assertEqual(calls, ["ocd_produit_accepte"], "Nothing until Meta approves the message")
            template.status = "approved"
            product._ocd_vendor_change("Pagne bleu", product.list_price)
            product.action_ocd_refuse_change(reason)
            self.assertEqual(calls[-1], "ocd_modification_refusee")
        for record in (template, self.env.ref("ocd_live_shop_whatsapp.template_product_change_refused_en")):
            values = [record._render(variable.value, product)[product.id] for variable in record.variable_ids]
            self.assertEqual(values[:2], ["Brenda Wax", "Pagne wax"])
            self.assertTrue(values[2], "The reason, in the language of the vendor")
