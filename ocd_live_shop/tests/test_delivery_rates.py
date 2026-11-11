from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


class OcdRatesCommon(OcdShopCommon):
    """OCD Live delivers in Douala with its couriers, and by travel agency to the other cities
    of Cameroon and to Togo. Fatou delivers herself in Akwa and Makepe; Brenda's parcels are
    picked up by an OCD courier."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rate = cls.env["ocd.delivery.rate"]
        cls.cameroon = cls.env.ref("base.cm")
        cls.togo = cls.env.ref("base.tg")
        cls.douala = cls.akwa.city_id
        cls.yaounde = cls.env["res.city"].search([("country_id", "=", cls.cameroon.id), ("id", "!=", cls.douala.id)], limit=1)
        cls.lome = cls.env["res.city"].search([("country_id", "=", cls.togo.id)], limit=1) or cls.env["res.city"].create(
            {"name": "Lomé", "country_id": cls.togo.id}
        )
        # Only the rates of the test
        cls.Rate.with_context(active_test=False).search([]).unlink()
        cls.company.write({"ocd_vendor_rate_min": 0, "ocd_vendor_rate_max": 0, "ocd_delivery_commission": 0})
        (cls.brenda | cls.fatou).write({"country_id": cls.cameroon.id, "city_id": cls.douala.id})
        cls.brenda.district_id = cls.akwa
        cls.fatou.district_id = cls.makepe
        cls.courier_douala = cls.Rate.create({
            "operator": "courier", "origin_city_id": cls.douala.id, "country_id": cls.cameroon.id,
            "city_ids": [Command.set(cls.douala.ids)], "price": 1000, "description": "24 to 48 hours",
        })
        cls.agency_cameroon = cls.Rate.create({
            "operator": "agency", "origin_country_id": cls.cameroon.id, "country_id": cls.cameroon.id,
            "price": 2500, "allow_cod": False, "sequence": 20,
        })
        cls.agency_togo = cls.Rate.create({
            "operator": "agency", "origin_country_id": cls.cameroon.id, "country_id": cls.togo.id,
            "price": 6000, "allow_cod": False, "sequence": 30,
        })
        cls.fatou_akwa = cls.Rate.create({
            "vendor_id": cls.fatou.id, "operator": "vendor", "country_id": cls.cameroon.id,
            "city_ids": [Command.set(cls.douala.ids)], "district_ids": [Command.set(cls.akwa.ids)], "price": 800,
        })
        cls.carrier_ocd = cls.env.ref("ocd_live_shop.carrier_ocd")
        cls.carrier_ocd.is_published = True

    def _customer(self, city, district=None, country=None):
        return self.env["res.partner"].create({
            "name": "Client",
            "phone": "+237 690000000",
            "country_id": (country or city.country_id).id,
            "city_id": city.id,
            "district_id": district.id if district else False,
            "delivery_landmark": "Repère",
        })

    def _quote(self, vendor, customer, amount=10000):
        return self.Rate._ocd_quote(vendor, customer, amount, self.company.currency_id, self.company)

    def _cart(self, customer, lines):
        order = self.env["sale.order"].create({
            "partner_id": customer.id,
            "order_line": [
                Command.create({"product_id": product.id, "product_uom_qty": qty, "tax_ids": [Command.clear()]})
                for product, qty in lines
            ],
        })
        return order


@tagged("post_install", "-at_install")
class TestOcdDeliveryRates(OcdRatesCommon):

    # === THE RATE OF A PARCEL === #

    def test_the_most_precise_rate_is_used(self):
        akwa_courier = self.Rate.create({
            "operator": "courier", "origin_city_id": self.douala.id, "country_id": self.cameroon.id,
            "city_ids": [Command.set(self.douala.ids)], "district_ids": [Command.set(self.akwa.ids)], "price": 700,
        })
        quote = self._quote(self.brenda, self.estelle)
        self.assertEqual(quote["rate"], akwa_courier)
        self.assertEqual(quote["price"], 700)
        quote = self._quote(self.brenda, self.herve)
        self.assertEqual(quote["rate"], self.courier_douala, "Bonaberi: the rate of the whole city")
        self.assertEqual(quote["operator"], "courier")
        self.assertTrue(quote["allow_cod"])

    def test_vendor_who_delivers(self):
        # Her own price in Akwa
        quote = self._quote(self.fatou, self.estelle)
        self.assertEqual((quote["rate"], quote["operator"], quote["price"]), (self.fatou_akwa, "vendor", 800))
        # In her zones without a price: she delivers at the price of the OCD courier
        makepe_customer = self._customer(self.douala, self.makepe)
        quote = self._quote(self.fatou, makepe_customer)
        self.assertEqual((quote["rate"], quote["operator"], quote["price"]), (self.courier_douala, "vendor", 1000))
        # Outside her zones: an OCD courier, as the team allows it
        quote = self._quote(self.fatou, self.herve)
        self.assertEqual((quote["operator"], quote["price"]), ("courier", 1000))
        # Not allowed: the parcel cannot be delivered, and the customer is told why
        self.fatou.ocd_zone_fallback = False
        quote = self._quote(self.fatou, self.herve)
        self.assertFalse(quote["rate"])
        self.assertIn("Fatou Karite (", quote["error"])

    def test_other_city_and_other_country(self):
        if not self.yaounde:
            self.skipTest("No second city in Cameroon")
        quote = self._quote(self.brenda, self._customer(self.yaounde))
        self.assertEqual((quote["operator"], quote["price"]), ("agency", 2500))
        self.assertFalse(quote["allow_cod"], "No payment at the door through an agency")
        quote = self._quote(self.brenda, self._customer(self.lome))
        self.assertEqual((quote["operator"], quote["price"]), ("agency", 6000))
        self.assertFalse(quote["allow_cod"])
        # A country without a rate: refused
        quote = self._quote(self.brenda, self._customer(self.env["res.city"].create(
            {"name": "Abidjan", "country_id": self.env.ref("base.ci").id}
        )))
        self.assertTrue(quote["error"])

    def test_a_travel_agency_never_delivers_inside_its_city(self):
        self.courier_douala.active = False
        quote = self._quote(self.brenda, self.estelle)
        self.assertFalse(quote["rate"], "Without an OCD courier in Douala, no agency inside Douala")
        self.assertTrue(quote["error"])

    def test_no_payment_at_the_door_towards_another_country(self):
        self.agency_togo.allow_cod = True
        quote = self._quote(self.brenda, self._customer(self.lome))
        self.assertFalse(quote["allow_cod"])

    def test_free_above_an_amount_and_other_currency(self):
        self.courier_douala.free_above = 10000
        self.assertEqual(self._quote(self.brenda, self.estelle, amount=12000)["price"], 0)
        self.assertEqual(self._quote(self.brenda, self.estelle, amount=5000)["price"], 1000)
        other = self.env["res.currency"].with_context(active_test=False).search(
            [("id", "!=", self.company.currency_id.id)], limit=1
        )
        other.active = True
        self.env["res.currency.rate"].create({
            "currency_id": other.id, "company_id": self.company.id, "name": fields.Date.today(),
            "rate": 2.0 * (self.company.currency_id.rate or 1.0),
        })
        self.courier_douala.write({"currency_id": other.id, "price": 3000, "free_above": 0})
        expected = other._convert(3000, self.company.currency_id, self.company, fields.Date.today())
        self.assertAlmostEqual(self._quote(self.brenda, self.estelle)["price"], self.company.currency_id.round(expected))

    def test_prices_of_the_vendors_stay_within_the_limits(self):
        self.company.write({"ocd_vendor_rate_min": 300, "ocd_vendor_rate_max": 3000})
        with self.assertRaises(ValidationError):
            self.fatou_akwa.price = 5000
        with self.assertRaises(ValidationError):
            self.fatou_akwa.price = 100
        self.fatou_akwa.price = 1500
        self.courier_douala.price = 5000  # The rates of OCD Live are free of these limits

    def test_zones_must_be_coherent(self):
        with self.assertRaises(ValidationError):
            self.Rate.create({
                "operator": "courier", "country_id": self.togo.id,
                "city_ids": [Command.set(self.douala.ids)], "price": 1000,
            })
        with self.assertRaises(ValidationError):
            self.Rate.create({"vendor_id": self.fatou.id, "operator": "courier", "country_id": self.cameroon.id, "price": 1000})

    # === THE ORDER AND ITS PARCELS === #

    def test_one_price_per_parcel_and_each_parcel_gets_its_price(self):
        self.company.ocd_delivery_commission = 10
        order = self._cart(self.estelle, [(self.dress, 1), (self.butter, 1)])
        rate = self.carrier_ocd.rate_shipment(order)
        self.assertTrue(rate["success"], rate.get("error_message"))
        self.assertEqual(rate["price"], 1800, "Brenda's parcel by an OCD courier 1000 + Fatou's 800")
        order.set_delivery_line(self.carrier_ocd, rate["price"])
        self.assertEqual(len(order.ocd_delivery_line_ids), 2)
        order.action_confirm()
        brenda_parcel = self._parcel(order, self.brenda)
        fatou_parcel = self._parcel(order, self.fatou)
        self.assertEqual(brenda_parcel.ocd_fee_amount, 1000)
        self.assertEqual(brenda_parcel.ocd_delivery_mode, "pickup")
        self.assertEqual(brenda_parcel.ocd_courier_id, self.courier)
        self.assertEqual(brenda_parcel.ocd_vendor_fee_amount, 0, "OCD keeps the delivery of its courier")
        self.assertEqual(fatou_parcel.ocd_fee_amount, 800)
        self.assertEqual(fatou_parcel.ocd_delivery_mode, "vendor")
        self.assertEqual(fatou_parcel.ocd_courier_id, self.fatou)
        self.assertEqual(fatou_parcel.ocd_vendor_fee_amount, 720, "800 minus the 10 % of OCD")
        self.assertEqual(fatou_parcel.ocd_rate_id, self.fatou_akwa)
        # The vendor is paid her delivery, after the share of OCD
        fatou_parcel.action_ocd_ready()
        fatou_parcel.action_ocd_leave()
        fatou_parcel.sudo()._ocd_deliver()
        bill = fatou_parcel.ocd_vendor_bill_ids.filtered(lambda m: m.move_type == "in_invoice")
        delivery_product = self.env.ref("ocd_live_shop.product_vendor_delivery").product_variant_id
        delivery_line = bill.invoice_line_ids.filtered(lambda l: l.product_id == delivery_product)
        self.assertEqual(delivery_line.price_unit, 720)

    def test_the_cart_follows_the_quantities(self):
        order = self._cart(self.estelle, [(self.dress, 1)])
        order.set_delivery_line(self.carrier_ocd, self.carrier_ocd.rate_shipment(order)["price"])
        self.assertEqual(order.ocd_delivery_line_ids.mapped("amount"), [1000])
        order.order_line.filtered(lambda l: not l.is_delivery).product_uom_qty = 2
        order._verify_cart_after_update()
        self.assertEqual(sum(order.ocd_delivery_line_ids.mapped("amount")), order._ocd_delivery_fee())
        order._remove_delivery_line()
        self.assertFalse(order.ocd_delivery_line_ids)

    def test_an_address_a_parcel_cannot_reach_is_refused(self):
        self.fatou.ocd_zone_fallback = False
        order = self._cart(self.herve, [(self.dress, 1), (self.butter, 1)])
        rate = self.carrier_ocd.rate_shipment(order)
        self.assertFalse(rate["success"])
        self.assertIn("Fatou Karite", rate["error_message"])
        self.assertFalse(self.carrier_ocd._is_available_for_order(order))
        self.assertFalse(order._get_delivery_methods(), "No other method once the delivery of OCD Live is published")

    def test_payment_at_the_door_only_when_every_parcel_allows_it(self):
        cod = self.env.ref("delivery.payment_provider_cod")
        cod.write({"is_published": True, "company_id": self.company.id})
        cod.with_context(active_test=False).payment_method_ids.active = True
        local = self._cart(self.estelle, [(self.dress, 1)])
        local.set_delivery_line(self.carrier_ocd, self.carrier_ocd.rate_shipment(local)["price"])
        self.assertTrue(local._ocd_cod_allowed())
        providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, local.partner_id.id, local.amount_total, sale_order_id=local.id
        )
        self.assertIn(cod, providers, "Every parcel allows the payment at the door")
        far = self._cart(self._customer(self.lome), [(self.dress, 1)])
        far.set_delivery_line(self.carrier_ocd, self.carrier_ocd.rate_shipment(far)["price"])
        self.assertFalse(far._ocd_cod_allowed())
        providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, far.partner_id.id, far.amount_total, sale_order_id=far.id
        )
        self.assertNotIn(cod, providers)

    def test_rates_created_from_the_delivery_methods(self):
        def method(name, price, cities):
            # The fixed price of a delivery method is the price of its product: one product each
            product = self.env["product.product"].create({"name": name, "type": "service", "list_price": price})
            return self.env["delivery.carrier"].create({
                "name": name,
                "delivery_type": "fixed",
                "product_id": product.id,
                "country_ids": [Command.set(self.cameroon.ids)],
                "city_ids": [Command.set(cities.ids)],
                "is_published": True,
            })
        carrier = method("Livraison Douala", 1200, self.douala)
        unpriced = method("Livraison Cameroun", 0, self.env["res.city"])
        created = self.Rate._ocd_rates_from_carriers(self.company)
        douala = created.filtered(lambda r: r.source_carrier_id == carrier)
        self.assertEqual((douala.operator, douala.origin_city_id, douala.price, douala.active), ("courier", self.douala, 1200, True))
        self.assertFalse(carrier.is_published, "Replaced by the delivery of OCD Live")
        archived = self.Rate.with_context(active_test=False).search([("source_carrier_id", "=", unpriced.id)])
        self.assertEqual((archived.operator, archived.active), ("agency", False), "No price: archived for the team")
        self.assertFalse(self.Rate._ocd_rates_from_carriers(self.company), "Once each")


@tagged("post_install", "-at_install")
class TestOcdDeliveryRatesWebsite(HttpCase, OcdRatesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        (cls.dress.product_tmpl_id | cls.butter.product_tmpl_id).write({"is_published": True})

    def _fill_cart(self):
        self.authenticate(None, None)
        for product in (self.dress, self.butter):
            self.url_open("/ocd/panier/ajouter", data={
                "csrf_token": self.csrf_token(), "product_template_id": product.product_tmpl_id.id, "quantity": 1,
            })
        return self.env["sale.order"].sudo().search(
            [("order_line.product_id", "=", self.butter.id), ("state", "=", "draft")], order="id desc", limit=1
        )

    def _address(self, district):
        return {
            "csrf_token": self.csrf_token(),
            "name": "Estelle Ngono",
            "country_id": self.cameroon.id,
            "delivery_country_id": self.cameroon.id,
            "phone": "670 00 00 98",
            "city_id": district.city_id.id,
            "district_id": district.id,
            "delivery_landmark": "En face de la pharmacie",
        }

    def test_checkout_shows_each_parcel_and_saves_them(self):
        order = self._fill_cart()
        result = self.make_jsonrpc_request("/ocd/livraison/tarif", {
            "country_id": self.cameroon.id, "city_id": self.douala.id, "district_id": self.akwa.id,
        })
        self.assertTrue(result["method"]["ok"])
        self.assertEqual([row["fee"].replace(" ", " ").replace("\xa0", " ") != "" for row in result["method"]["rows"]], [True, True])
        response = self.url_open("/ocd/livraison", data=self._address(self.akwa), allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:300])
        self.assertEqual(order.carrier_id, self.carrier_ocd)
        self.assertEqual(order.amount_delivery, 1800)
        self.assertEqual(sorted(order.ocd_delivery_line_ids.mapped("amount")), [800, 1000])
        response = self.url_open("/shop/payment")
        self.assertIn("Delivery of the parcel of Fatou Karite", response.text)

    def test_a_vendor_who_cannot_deliver_is_said_and_can_be_removed(self):
        self.fatou.ocd_zone_fallback = False
        order = self._fill_cart()
        response = self.url_open("/ocd/livraison", data=self._address(self.bonaberi))
        self.assertIn("does not deliver to", response.text)
        self.assertNotEqual(order.carrier_id, self.carrier_ocd)
        self.url_open("/ocd/panier/retirer", data={"csrf_token": self.csrf_token(), "vendor_id": self.fatou.id})
        self.assertFalse(order.order_line.filtered(lambda l: l.product_id == self.butter))
        response = self.url_open("/ocd/livraison", data=self._address(self.bonaberi), allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(order.amount_delivery, 1000)

    def test_vendor_sets_a_price_within_the_limits(self):
        self.company.write({"ocd_vendor_rate_min": 300, "ocd_vendor_rate_max": 3000})
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.fatou._ocd_get_space_token()}")
        response = self.url_open("/ocd/espace/moi/livraison")
        self.assertIn("My delivery prices", response.text)
        self.assertIn("Akwa", response.text)
        form = {"csrf_token": self.csrf_token(), "city_id": self.douala.id, "district_ids": self.bonaberi.id}
        response = self.url_open("/ocd/espace/moi/livraison", data={**form, "price": "5000"})
        self.assertIn("between", response.text)
        self.assertFalse(self.Rate.search([("vendor_id", "=", self.fatou.id), ("price", "=", 5000)]), "Refused: not saved")
        self.url_open("/ocd/espace/moi/livraison", data={**form, "price": "1 500"})
        rate = self.Rate.search([("vendor_id", "=", self.fatou.id), ("district_ids", "=", self.bonaberi.id)])
        self.assertEqual(rate.price, 1500)
        self.url_open(f"/ocd/espace/moi/livraison/{rate.id}/supprimer", data={"csrf_token": self.csrf_token()})
        self.assertFalse(rate.active, "Archived: the orders already paid keep their rate")
        # The price of another vendor cannot be removed
        response = self.url_open(f"/ocd/espace/moi/livraison/{self.courier_douala.id}/supprimer", data={"csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 404)
