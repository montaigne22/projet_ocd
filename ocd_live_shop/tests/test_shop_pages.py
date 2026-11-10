import base64
from urllib.parse import parse_qs, urlparse

from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon

# A small PNG image (1 x 1 pixel)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestOcdShopPages(HttpCase, OcdShopCommon):
    """Pages of the shop of Odoo with the look of the validated design: the logic of Odoo
    (cart, delivery, payment) is kept, the forms post to small routes that call it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        cls.dress.product_tmpl_id.is_published = True
        cls.butter.product_tmpl_id.is_published = True
        cls.category = cls.env["ocd.live.category"].search([], limit=1) or cls.env["ocd.live.category"].create(
            {"name": "Habits"}
        )
        cls.brenda.write({"ocd_category_id": cls.category.id, "city": "Douala", "phone": "+237 670000001"})
        cls.awa = cls.env["res.partner"].create({
            "name": "Awa Mensah",
            "ocd_is_vendor": True,
            "ocd_vendor_state": "approved",
            "ocd_sale_mode": "direct",
            "phone": "+228 90 00 00 07",
        })
        cls.cake = cls.env["product.template"].create({
            "name": "Gateau ananas",
            "list_price": 5000,
            "ocd_vendor_id": cls.awa.id,
            "is_published": True,
        })
        cls.carrier = cls.env.ref("delivery_cameroon.carrier_douala_home")
        cls.carrier.write({"is_published": True, "fixed_price": 1000})
        cls.carrier.product_id.list_price = 1000
        # The team publishes the delivery methods of OCD Live only
        cls.env["delivery.carrier"].search([("id", "!=", cls.carrier.id), ("is_published", "=", True)]).is_published = False
        cls.douala = cls.akwa.city_id

    def _add_dress(self, quantity=1):
        self.authenticate(None, None)
        return self.url_open("/ocd/panier/ajouter", data={
            "csrf_token": self.csrf_token(),
            "product_template_id": self.dress.product_tmpl_id.id,
            "quantity": quantity,
        }, allow_redirects=False)

    def _cart(self):
        return self.env["sale.order"].sudo().search(
            [("order_line.product_id", "=", self.dress.id), ("state", "=", "draft")], order="id desc", limit=1
        )

    # === SHOP AND PRODUCT === #

    def test_shop_page_with_the_categories_of_the_vendors(self):
        response = self.url_open("/shop")
        self.assertEqual(response.status_code, 200)
        self.assertIn("o_ocd_shop", response.text)
        self.assertIn("Robe en wax", response.text)
        self.assertIn(self.category.name, response.text)
        response = self.url_open(f"/shop?categorie={self.category.id}")
        self.assertIn("Robe en wax", response.text)
        self.assertNotIn("Beurre de karite", response.text, "Fatou has no category: not in Habits")
        response = self.url_open("/shop?search=nothing-like-this")
        self.assertIn("No product found.", response.text)

    def test_product_sold_by_ocd(self):
        response = self.url_open(self.dress.product_tmpl_id.website_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("o_ocd_product_page", response.text)
        self.assertIn("Add to the cart", response.text)
        self.assertIn("Sold by Brenda Wax", response.text)
        self.assertIn('action="/ocd/panier/ajouter"', response.text)

    def test_product_in_direct_contact_is_not_sold_on_the_website(self):
        response = self.url_open(self.cake.website_url)
        self.assertIn("Write to Awa on WhatsApp", response.text)
        self.assertIn(f'action="/ocd/wa/{self.cake.id}"', response.text)
        self.assertNotIn("o_ocd_variant_add", response.text)
        # Even posted by hand, the product does not go in the cart
        self.authenticate(None, None)
        response = self.url_open("/ocd/panier/ajouter", data={
            "csrf_token": self.csrf_token(), "product_template_id": self.cake.id, "quantity": 1,
        }, allow_redirects=False)
        self.assertIn("erreur=", response.headers["Location"])
        self.assertFalse(self.env["sale.order.line"].sudo().search([("product_id.product_tmpl_id", "=", self.cake.id)]))

    def test_whatsapp_message_gives_the_choice_and_the_link(self):
        color = self.env["product.attribute"].create({
            "name": "Couleur", "value_ids": [(0, 0, {"name": "Bleu"}), (0, 0, {"name": "Rouge"})],
        })
        self.cake.attribute_line_ids = [(0, 0, {"attribute_id": color.id, "value_ids": [(6, 0, color.value_ids.ids)]})]
        line = self.cake.attribute_line_ids
        blue = line.product_template_value_ids.filtered(lambda v: v.name == "Bleu")
        response = self.url_open(f"/ocd/wa/{self.cake.id}?attribute_{line.id}={blue.id}", allow_redirects=False)
        text = parse_qs(urlparse(response.headers["Location"]).query)["text"][0]
        self.assertIn("Couleur Bleu", text)
        self.assertIn(self.cake.website_url, text)

    # === CART === #

    def test_add_to_the_cart_and_change_the_quantity(self):
        response = self._add_dress(quantity=2)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith("/shop/cart"))
        order = self._cart()
        line = order.order_line.filtered(lambda l: l.product_id == self.dress)
        self.assertEqual(line.product_uom_qty, 2)
        response = self.url_open("/shop/cart")
        self.assertIn("My cart", response.text)
        self.assertIn("Robe en wax", response.text)
        self.url_open("/ocd/panier/ligne", data={"csrf_token": self.csrf_token(), "line_id": line.id, "quantity": 3})
        self.assertEqual(line.product_uom_qty, 3)
        self.url_open("/ocd/panier/ligne", data={"csrf_token": self.csrf_token(), "line_id": line.id, "quantity": 0})
        self.assertFalse(line.exists())

    # === DELIVERY ADDRESS, PAYMENT === #

    def test_delivery_address_without_email_then_payment(self):
        self._add_dress()
        response = self.url_open("/shop/checkout")
        self.assertIn("Where do we deliver?", response.text)
        cameroon = self.env.ref("base.cm")
        form = {
            "csrf_token": self.csrf_token(),
            "name": "Estelle Ngono",
            "country_id": cameroon.id,
            "delivery_country_id": cameroon.id,
            "phone": "670 00 00 99",
            "city_id": self.douala.id,
            "district_id": self.akwa.id,
            "delivery_landmark": "En face de la pharmacie",
            "optin": "1",
        }
        # The landmark is required: the courier uses it
        response = self.url_open("/ocd/livraison", data={**form, "delivery_landmark": ""})
        self.assertIn("Give a well-known place near your home", response.text)
        response = self.url_open("/ocd/livraison", data=form, allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:500])
        self.assertTrue(response.headers["Location"].endswith("/shop/payment"))
        order = self._cart()
        self.assertEqual(order.partner_id.name, "Estelle Ngono")
        self.assertEqual(order.partner_id.phone, "+237 670000099")
        self.assertFalse(order.partner_id.email)
        self.assertTrue(order.partner_id.ocd_whatsapp_optin)
        self.assertEqual(order.partner_shipping_id.district_id, self.akwa)
        self.assertEqual(order.carrier_id, self.carrier)
        self.assertEqual(order.amount_delivery, 1000)
        # Odoo checks the address again before the payment: complete without an e-mail
        response = self.url_open("/shop/payment")
        self.assertEqual(response.status_code, 200)
        self.assertIn("o_ocd_pay_lines", response.text)
        self.assertIn("Delivery to Akwa, Douala", response.text)

    def test_delivery_price_shown_while_typing(self):
        self._add_dress()
        result = self.make_jsonrpc_request("/ocd/livraison/tarif", {
            "country_id": self.env.ref("base.cm").id, "city_id": self.douala.id, "district_id": self.akwa.id,
        })
        self.assertIn(self.akwa.id, [row["id"] for row in result["districts"]])
        self.assertEqual(result["method"]["name"], self.carrier.name)

    # === TRACKING OF THE ORDER === #

    def test_tracking_page_rating_and_return(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        token = order._portal_ensure_token()
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/ocd/suivi/{order.id}?access_token=wrong").status_code, 404)
        response = self.url_open(f"/ocd/suivi/{order.id}?access_token={token}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("your order is confirmed", response.text)
        self.assertIn("Parcel of Brenda Wax", response.text)
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        response = self.url_open(f"/ocd/suivi/{order.id}?access_token={token}")
        self.assertIn("Your code for this parcel", response.text)
        self.assertIn(parcel.sudo().ocd_delivery_code, response.text)
        parcel._ocd_collect("cash", self.courier)
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        response = self.url_open(f"/ocd/suivi/{order.id}?access_token={token}")
        self.assertIn("Did you like your order?", response.text)
        self.url_open(f"/ocd/suivi/{order.id}/note?access_token={token}", data={
            "csrf_token": self.csrf_token(), "stars": 5,
        })
        self.assertEqual(order.ocd_rating, 5)
        self.url_open(f"/ocd/suivi/{order.id}/retour?access_token={token}", data={"csrf_token": self.csrf_token()})
        self.assertTrue(order.ocd_return_requested_at)
        self.assertTrue(order.activity_ids, "The team has an activity to organise the return")
        self.assertFalse(order._ocd_can_request_return(), "One return request per order")

    # === MY PRODUCTS === #

    def test_vendor_adds_a_product_checked_by_the_team(self):
        token = self.brenda._ocd_get_space_token()
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{token}")
        response = self.url_open("/ocd/espace/moi/produits")
        self.assertIn("Add a product", response.text)
        # A photo is required
        response = self.url_open("/ocd/espace/moi/produits", data={
            "csrf_token": self.csrf_token(), "name": "Jupe en wax", "price": "8000", "quantity": "2",
        })
        self.assertIn("Add a photo of your product.", response.text)
        response = self.url_open("/ocd/espace/moi/produits", data={
            "csrf_token": self.csrf_token(), "name": "Jupe en wax", "price": "8 000", "quantity": "2",
        }, files={"photo": ("jupe.png", PNG, "image/png")}, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        product = self.env["product.template"].search([("name", "=", "Jupe en wax"), ("ocd_vendor_id", "=", self.brenda.id)])
        self.assertEqual(product.ocd_review_state, "to_check")
        self.assertFalse(product.is_published)
        self.assertEqual(product.list_price, 8000)
        self.assertTrue(product.image_128)
        self.assertEqual(product.qty_available, 2)
        self.url_open(f"/ocd/espace/moi/produits/{product.id}/stock", data={"csrf_token": self.csrf_token(), "quantity": 0})
        product.invalidate_recordset(["qty_available"])
        self.assertEqual(product.qty_available, 0)
        # Another vendor cannot change it
        self.url_open(f"/ocd/espace/{self.fatou._ocd_get_space_token()}")
        response = self.url_open(f"/ocd/espace/moi/produits/{product.id}/stock", data={
            "csrf_token": self.csrf_token(), "quantity": 5,
        })
        self.assertEqual(response.status_code, 404)

    # === DELIVERY APP: THE MONEY IS NEVER LEFT BEHIND === #

    def test_no_code_while_the_money_is_to_collect(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        self.assertEqual(parcel.ocd_cod_state, "to_collect")
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        token = self.courier._ocd_get_space_token()
        self.authenticate(None, None)
        response = self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/code", data={
            "csrf_token": self.csrf_token(), "code": parcel.sudo().ocd_delivery_code,
        })
        self.assertIn("Collect the payment first", response.text)
        self.assertEqual(parcel.ocd_stage, "on_the_way")
        self.assertEqual(parcel.ocd_code_attempts, 0, "Not a wrong code")

    def test_resumed_delivery_is_traced(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_report_problem("absent")
        token = self.courier._ocd_get_space_token()
        self.authenticate(None, None)
        self.url_open(f"/ocd/livrer/{token}/colis/{parcel.id}/retry", data={"csrf_token": self.csrf_token()})
        self.assertEqual(parcel.ocd_stage, "picked")
        self.assertIn("Delivery resumed by Junior Ekwalla", "\n".join(parcel.message_ids.mapped("body")))
