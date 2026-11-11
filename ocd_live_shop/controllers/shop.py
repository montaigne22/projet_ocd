import json
import re
from urllib.parse import urlencode

from odoo import http
from odoo.fields import Domain
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live.controllers import common
from odoo.addons.payment.controllers.payment_status import PaymentStatus
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.controllers.main import WebsiteSale

from . import shop_common

PAGE_TEMPLATES = {
    "website_sale.products": "ocd_live_shop.shop",
    "website_sale.product": "ocd_live_shop.product",
    "website_sale.cart": "ocd_live_shop.cart",
    "website_sale.payment": "ocd_live_shop.payment",
}


def cart_pill(order=None):
    """Button of the cart in the header: "Cart · 3"."""
    order = order if order is not None else request.cart
    count = int(sum(order.order_line.filtered(lambda l: not l.is_delivery).mapped("product_uom_qty"))) if order else 0
    return {"href": "/shop/cart", "label": request.env._("Cart · %s", count), "count": count}


def order_by_token(order_id, access_token):
    """The order of the link sent to the customer (tracking page)."""
    order = request.env["sale.order"].sudo().browse(order_id).exists()
    if not order or not access_token or not order.access_token or not consteq(order.access_token, access_token):
        raise request.not_found()
    return order


class OcdShop(WebsiteSale):
    """Pages of the shop of Odoo with the look of the validated design (Shop, Produit,
    Livraison, PayerCommande, Suivi). Odoo keeps the logic: products and prices of the
    website, cart, delivery methods, payment and confirmation of the order; these pages only
    change how it is shown, and the forms post to small routes that call the same methods."""

    # === SHOP === #

    def _get_shop_domain(self, search, category, attribute_value_dict, search_in_description=True, tags=None):
        domain = super()._get_shop_domain(
            search, category, attribute_value_dict, search_in_description=search_in_description, tags=tags
        )
        ocd_category = request.params.get("categorie")
        if ocd_category and str(ocd_category).isdigit():
            domain = Domain.AND([domain, Domain("ocd_category_id", "=", int(ocd_category))])
        return domain

    def _get_search_options(self, *args, **kwargs):
        """The category of the vendors (?categorie=) filters the products of the shop."""
        options = super()._get_search_options(*args, **kwargs)
        ocd_category = request.params.get("categorie")
        if ocd_category and str(ocd_category).isdigit():
            extra = [("ocd_category_id", "=", int(ocd_category))]
            options["extra_domain"] = Domain.AND([options["extra_domain"], extra]) if options.get("extra_domain") else extra
        return options

    @http.route()
    def shop(self, *args, **kwargs):
        response = super().shop(*args, **kwargs)
        if getattr(response, "template", None) == "website_sale.products":
            response.template = PAGE_TEMPLATES[response.template]
            response.qcontext.update(self._ocd_shop_values(response.qcontext))
        return response

    def _ocd_shop_values(self, values):
        products = values.get("products") or request.env["product.template"]
        price_by_id = shop_common.prices(products)
        current = request.params.get("categorie")
        search = values.get("search") or ""
        query = {"search": search} if search else {}
        chips = [{
            "label": request.env._("All"),
            "href": "/shop" + (f"?{urlencode(query)}" if query else ""),
            "on": not current,
        }]
        for category in request.env["ocd.live.category"].sudo().search([]):
            chips.append({
                "label": category.name,
                "href": f"/shop?{urlencode({**query, 'categorie': category.id})}",
                "on": str(category.id) == str(current),
            })
        pager = values.get("pager") or {}
        more_url = False
        if pager and pager.get("page_count", 1) > (pager.get("page") or {}).get("num", 1):
            more_url = (pager.get("page_next") or {}).get("url")
        return common.page_values(
            "shop",
            nav="shop",
            header_name=request.env._("Shop OCD"),
            header_pill=cart_pill(),
            cards=[shop_common.card(product, price_by_id) for product in products],
            chips=chips,
            categorie=current,
            countries=self._ocd_countries(),
            country_aria=request.env._("Country of delivery. Change"),
            more_url=more_url,
        )

    def _ocd_countries(self):
        """Country of delivery: the pricelists the visitor can choose, with their country."""
        website = request.env.website
        pricelists = website.get_pricelist_available(show_visible=True)
        current = request.pricelist
        rows = []
        for pricelist in pricelists:
            country = pricelist.country_group_ids.country_ids[:1]
            rows.append({
                "pricelist": pricelist,
                "country": country,
                "flag": country.code.lower() if country else False,
                "label": country.name if country else pricelist.name,
                "on": pricelist == current,
            })
        rows = [row for row in rows if row["country"]]
        if not any(row["on"] for row in rows):
            country = website.company_id.country_id
            rows.insert(0, {
                "pricelist": current, "country": country, "flag": country.code.lower() if country else False,
                "label": country.name if country else "", "on": True,
            })
        return rows

    # === PRODUCT === #

    @http.route()
    def product(self, product, *args, **kwargs):
        response = super().product(product, *args, **kwargs)
        if getattr(response, "template", None) == "website_sale.product":
            response.template = PAGE_TEMPLATES[response.template]
            response.qcontext.update(self._ocd_product_values(response.qcontext.get("product") or product))
        return response

    def _ocd_variants(self, template):
        """Each variant of the product: its values, its price and its stock, read by the page
        to update the price, the stock and the values that are sold out."""
        rows = []
        for variant in template.sudo().product_variant_ids:
            amount, money_currency = shop_common.variant_price(variant)
            qty = shop_common.free_qty(variant) if shop_common.tracked(variant) else None
            rows.append({
                "id": variant.id,
                "values": sorted(variant.product_template_attribute_value_ids.ids),
                "price": amount,
                "price_text": common.money(amount, money_currency),
                "qty": qty,
            })
        return rows

    def _ocd_product_values(self, template):
        env = request.env
        template_sudo = template.sudo()
        vendor = template_sudo.ocd_vendor_id
        ocd = shop_common.sold_by_ocd(template_sudo)
        variants = self._ocd_variants(template_sudo)
        first = variants[0] if variants else {"price": template_sudo.list_price, "qty": None, "values": [], "id": False}
        money_currency = shop_common.currency()
        lines = []
        for line in template_sudo.valid_product_template_attribute_line_ids:
            if line.attribute_id.create_variant == "no_variant":
                continue
            lines.append({
                "line": line,
                "values": line.product_template_value_ids._only_active(),
                "color": line.attribute_id.display_type == "color",
            })
        first_name = (vendor.name or "").split()[0] if vendor.name else ""
        live_now = bool(vendor) and bool(env["ocd.live.booking"].sudo().search_count([
            ("partner_id", "=", vendor.id), ("state", "=", "confirmed"),
            ("start_datetime", "<=", common.now()), ("end_datetime", ">", common.now()),
        ]))
        count = env["product.template"].sudo().search_count([
            ("ocd_vendor_id", "=", vendor.id), ("is_published", "=", True), ("sale_ok", "=", True),
        ]) if vendor else 0
        if self._ocd_carrier() and ocd:
            summary = env["ocd.delivery.rate"].sudo()._ocd_summary(vendor, common.company(), money_currency)
            delivery_lines = ([env._("Sent from %s.", summary["origin"])] if summary["origin"] else []) + summary["lines"]
            if summary["lines"]:
                delivery_lines.append(env._("The exact price for your district shows at the step Delivery."))
            else:
                delivery_lines.append(env._("Write to OCD Live to know the price of the delivery to your city."))
        else:
            carriers = env["delivery.carrier"].sudo().search([("website_published", "=", True)], order="sequence", limit=2)
            delivery_lines = [carrier.carrier_description for carrier in carriers if carrier.carrier_description]
        return common.page_values(
            "produit",
            nav="shop",
            back="/shop",
            back_label=env._("Back to the shop"),
            header_title=env._("Shop OCD"),
            header_pill=cart_pill(),
            template=template_sudo,
            ocd=ocd,
            images=[f"/web/image/product.template/{template_sudo.id}/image_1024"] if template_sudo.image_128 else [],
            first=first,
            variants_json=json.dumps({
                "variants": variants,
                "currency": {"symbol": money_currency.symbol, "position": money_currency.position,
                             "digits": money_currency.decimal_places},
                "texts": {
                    "in_stock": env._("In stock"),
                    "low": env._("Only %s left"),
                    "out": env._("Sold out"),
                    "add": env._("Add to the cart · %s"),
                },
            }),
            lines=lines,
            seen_live=bool(template_sudo.ocd_moment_ids),
            vendor=vendor,
            vendor_initials=common.initials(vendor.name) if vendor else "OCD",
            vendor_title=env._("Sold by %s", vendor.name) if vendor else env._("Sold by OCD Live"),
            vendor_line=" · ".join(part for part in (
                vendor.city,
                env._("%s products", count) if count != 1 else env._("1 product"),
                env._("live now") if live_now else "",
            ) if part) if vendor else "",
            live_now=live_now,
            delivery_lines=delivery_lines,
            direct_line=env._(
                "Payment and delivery are agreed directly with %s. OCD Live does not take the money for this product.",
                first_name,
            ),
            whatsapp_label=env._("Write to %s on WhatsApp", first_name),
            return_line=env._("Return possible within %s days after the delivery.", common.company().ocd_return_days)
            if common.company().ocd_return_days else False,
            add_label=env._("Add to the cart · %s", common.money(first["price"], money_currency)),
            question_url=self._ocd_question_url(template_sudo),
        )

    def _ocd_question_url(self, template):
        digits = re.sub(r"\D", "", common.company().phone or "")
        if len(digits) < 8:
            return False
        text = request.env._("Hello, I have a question about %s.", template.name)
        return f"https://wa.me/{digits}?{urlencode({'text': text})}"

    # === DELIVERY ADDRESS (design: Livraison) === #

    @http.route()
    def shop_checkout(self, try_skip_step=None, pays=None, **query_params):
        order = request.cart
        if not order or not order.order_line:
            return request.redirect("/shop/cart")
        return self._ocd_render_delivery(order, values={"delivery_country_id": pays} if pays else None)

    @http.route()
    def shop_address(self, partner_id=None, address_type="billing", use_delivery_as_billing=None, **query_params):
        order = request.cart
        if not order or not order.order_line:
            return request.redirect("/shop/cart")
        return self._ocd_render_delivery(order)

    def _ocd_delivery_country(self, order):
        """Country of delivery proposed first: the one of the address of the customer, else the
        one chosen in the shop (country of the pricelist), else the one of the company."""
        partner = order.partner_shipping_id if not order._is_anonymous_cart() else request.env["res.partner"]
        pricelist = getattr(request, "pricelist", None)
        pricelist_country = pricelist.country_group_ids.country_ids[:1] if pricelist else request.env["res.country"]
        return (
            partner.country_id or pricelist_country or request.env.website.company_id.country_id
            or common.default_country()
        )

    def _ocd_delivery_countries(self, country):
        """Countries the customer can choose: the destinations of the rates, and `country`."""
        rates = request.env["ocd.delivery.rate"].sudo()._ocd_rates(common.company())
        countries = rates.country_id | country
        return countries.sorted("name")

    def _ocd_render_delivery(self, order, values=None, errors=None, error=None):
        env = request.env
        values = values or {}
        partner = env["res.partner"] if order._is_anonymous_cart() else order.partner_shipping_id
        country = env["res.country"].sudo().browse(int(values["delivery_country_id"])).exists() if str(
            values.get("delivery_country_id") or "").isdigit() else self._ocd_delivery_country(order)
        cities = env["res.city"].sudo().search([("country_id", "=", country.id)], order="name")
        city_id = int(values["city_id"]) if str(values.get("city_id") or "").isdigit() else partner.city_id.id
        city = cities.filtered(lambda c: c.id == city_id)[:1] or cities[:1]
        district_id = int(values["district_id"]) if str(values.get("district_id") or "").isdigit() else partner.district_id.id
        districts = env["res.city.district"].sudo().search([("city_id", "=", city.id)], order="name") if city else env["res.city.district"]
        lines = order.order_line.filtered(lambda line: not line.is_delivery)
        count = int(sum(lines.mapped("product_uom_qty")))
        goods = common.money(sum(lines.mapped("price_total")), order.currency_id)
        method = self._ocd_rate_preview(order, country, city, districts.filtered(lambda d: d.id == district_id)[:1])
        phone_country = env["res.country"].sudo().browse(int(values["country_id"])).exists() if str(
            values.get("country_id") or "").isdigit() else (partner.country_id or country)
        phone = values.get("phone") if "phone" in values else common.local_digits(phone_country, partner.phone or "")
        return request.render("ocd_live_shop.delivery", common.page_values(
            "livraison",
            back="/shop/cart",
            back_label=env._("Back to the cart"),
            step=1,
            step_total=3,
            step_label=env._("Step %(step)s of %(total)s", step=1, total=3),
            order=order,
            name=values.get("name", partner.name or ""),
            phone_value=phone,
            optin=values.get("optin", "1" if (not partner or partner.ocd_whatsapp_optin) else ""),
            country=country,
            countries=self._ocd_delivery_countries(country),
            dial_rows=common.dial_rows(phone_country),
            none_line=env._("Choose your city and your district: the price of the delivery shows here."),
            cities=cities,
            city=city,
            districts=districts,
            district_id=district_id,
            landmark=values.get("delivery_landmark", partner.delivery_landmark or ""),
            method=method,
            items_line=env._("%(count)s items %(amount)s + delivery", count=count, amount=goods)
            if count != 1 else env._("1 item %s + delivery", goods),
            total=method["total"] if method else goods,
            errors=errors or {},
            error=error,
        ))

    def _ocd_carrier(self):
        """The delivery of OCD Live when it is published (one price per parcel), else False:
        the shop then offers the delivery methods of Odoo."""
        carrier = request.env.ref("ocd_live_shop.carrier_ocd", raise_if_not_found=False)
        carrier = carrier.sudo() if carrier else carrier
        return carrier if carrier and carrier.active and carrier.is_published else False

    def _ocd_parcel_rows(self, order, quotes):
        """One line per parcel for the pages Livraison and Payer."""
        env = request.env
        rows = []
        for quote in quotes:
            vendor = quote["vendor"]
            title = env._("Parcel of %s", vendor.name) if vendor else env._("Parcel of OCD Live")
            sub = " · ".join(part for part in (
                env._("from %s", quote["origin"].name) if quote["origin"] else "",
                {
                    "vendor": env._("delivered by the vendor"),
                    "courier": env._("delivered by an OCD courier"),
                    "agency": env._("through a travel agency"),
                }.get(quote["operator"], ""),
                quote["description"],
            ) if part)
            rows.append({
                "vendor_id": vendor.id or 0,
                "title": title,
                "sub": sub,
                "fee": (common.money(quote["price"], order.currency_id) if quote["price"] else env._("Free"))
                if not quote["error"] else "",
                "error": quote["error"],
            })
        return rows

    def _ocd_rate_preview(self, order, country, city, district):
        """The delivery and its price for the address being typed (the price is checked again by
        Odoo when the address is saved)."""
        partner = request.env["res.partner"].sudo().new({
            "country_id": country.id, "city_id": city.id, "district_id": district.id, "city": city.name,
        })
        goods = order._compute_amount_total_without_delivery()
        carrier_ocd = self._ocd_carrier()
        if carrier_ocd:
            quotes = order._ocd_delivery_quotes(partner=partner)
            rows = self._ocd_parcel_rows(order, quotes)
            if not city:
                return False
            ok = bool(quotes) and not any(quote["error"] for quote in quotes)
            fee = sum(quote["price"] for quote in quotes) if ok else 0.0
            return {
                "carrier": carrier_ocd,
                "name": carrier_ocd.name,
                "note": request.env._("One price per parcel: each vendor delivers from their city.")
                if len(quotes) > 1 else (rows[0]["sub"] if rows else ""),
                "fee": (common.money(fee, order.currency_id) if fee else request.env._("Free")) if ok else "",
                "total": common.money(goods + fee, order.currency_id),
                "rows": rows,
                "ok": ok,
            }
        carriers = request.env["delivery.carrier"].sudo().search([
            ("website_published", "=", True),
            *request.env["delivery.carrier"]._check_company_domain(order.company_id),
        ], order="sequence, id").available_carriers(partner, order)
        carrier = carriers[:1]
        if not carrier:
            return False
        if carrier.delivery_type == "fixed":
            fee = order.pricelist_id._get_product_price(carrier.product_id, 1.0) if order.pricelist_id else carrier.fixed_price
            if carrier.free_over and goods >= carrier.amount:
                fee = 0.0
            fee_text = common.money(fee, order.currency_id) if fee else request.env._("Free")
            total = common.money(goods + fee, order.currency_id)
        else:
            fee_text = request.env._("At the payment")
            total = common.money(goods, order.currency_id)
        return {
            "carrier": carrier, "name": carrier.name, "note": carrier.carrier_description or "",
            "fee": fee_text, "total": total, "rows": [], "ok": True,
        }

    @http.route("/ocd/livraison/tarif", type="jsonrpc", auth="public", website=True)
    def ocd_delivery_rate(self, country_id=None, city_id=None, district_id=None):
        order = request.cart
        if not order:
            return {}
        env = request.env
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or self._ocd_delivery_country(order)
        city = env["res.city"].sudo().browse(int(city_id or 0)).exists()
        district = env["res.city.district"].sudo().browse(int(district_id or 0)).exists()
        districts = env["res.city.district"].sudo().search([("city_id", "=", city.id)], order="name") if city else []
        method = self._ocd_rate_preview(order, country, city, district)
        return {
            "districts": [{"id": d.id, "name": d.name} for d in districts],
            "method": {key: method[key] for key in ("name", "note", "fee", "total", "rows", "ok")} if method else False,
            "none": env._("No delivery for this address yet: write to OCD Live on WhatsApp."),
            "remove_label": env._("Remove their products"),
        }

    @http.route("/ocd/panier/retirer", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ocd_remove_vendor(self, vendor_id=None, **post):
        """Remove from the cart the products of a vendor who cannot deliver to the address."""
        order = request.cart
        if order and str(vendor_id or "").isdigit():
            vendor_id = int(vendor_id)
            lines = order.order_line.filtered(
                lambda line: not line.is_delivery and (line.ocd_vendor_id.id or 0) == vendor_id
            )
            for line in lines:
                order._cart_update_line_quantity(line.id, 0)
            order._verify_cart_after_update()
        return request.redirect("/shop/checkout")

    @http.route("/ocd/livraison", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ocd_delivery_submit(self, **post):
        """Save the address of the customer on the cart with the address forms of Odoo (same
        checks: city, district and landmark required where the country needs them), then the
        delivery method of the address, then go to the payment."""
        env = request.env
        order = request.cart
        if not order or not order.order_line:
            return request.redirect("/shop/cart")
        country = env["res.country"].sudo().browse(int(post.get("delivery_country_id") or 0)).exists() or self._ocd_delivery_country(order)
        phone_country = env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists() or country
        errors = {}
        name = common.clean_text(post.get("name"))
        if not name:
            errors["name"] = env._("Type your name.")
        number = common.normalize_phone(phone_country, post.get("phone"))
        if not number:
            errors["phone"] = common.phone_error(phone_country)
        landmark = common.clean_text(post.get("delivery_landmark"), 200)
        if not landmark:
            errors["delivery_landmark"] = env._("Give a well-known place near your home: the courier uses it.")
        if errors:
            return self._ocd_render_delivery(order, values=post, errors=errors)
        form_data = {
            "name": name,
            "phone": number,
            "country_id": str(country.id),
            "city_id": post.get("city_id") or "",
            "district_id": post.get("district_id") or "",
            "delivery_landmark": landmark,
            "street": landmark,
        }
        partner_sudo, _address_type = self._prepare_address_update(
            order, partner_id=None if order._is_anonymous_cart() else order.partner_id.id, address_type="billing",
        )
        request.update_context(ocd_whatsapp_checkout=True)
        partner_sudo, feedback = self._create_or_update_address(
            partner_sudo,
            address_type="billing",
            use_delivery_as_billing="true",
            callback="/shop/payment",
            order_sudo=order,
            **form_data,
        )
        if feedback.get("invalid_fields"):
            fields = set(feedback["invalid_fields"])
            errors = {field: env._("Check this field.") for field in fields}
            if "district_id" in fields:
                errors["district_id"] = env._("Choose your district.")
            return self._ocd_render_delivery(order, values=post, errors=errors,
                                             error=" ".join(str(m) for m in feedback.get("messages", [])))
        partner_sudo.ocd_whatsapp_optin = bool(post.get("optin"))
        order._update_address(partner_sudo.id, {"partner_id", "partner_invoice_id", "partner_shipping_id"})
        if order.website_id.partner_id:
            order.message_unsubscribe(order.website_id.partner_id.ids)
        carriers = order._get_delivery_methods()
        carrier = order._get_preferred_delivery_method(carriers)
        if not carrier:
            errors_of_parcels = [q["error"] for q in order._ocd_delivery_quotes() if q["error"]] if self._ocd_carrier() else []
            return self._ocd_render_delivery(
                order, values=post,
                error=" ".join(errors_of_parcels) or env._("No delivery for this address yet: write to OCD Live on WhatsApp."),
            )
        rate = carrier.rate_shipment(order)
        if not rate.get("success"):
            return self._ocd_render_delivery(order, values=post, error=rate.get("error_message") or "")
        order._set_delivery_method(carrier, rate=rate)
        request.session["sale_last_order_id"] = order.id
        return request.redirect("/shop/payment")

    # === PAYMENT (design: PayerCommande) === #

    @http.route()
    def shop_payment(self, **post):
        response = super().shop_payment(**post)
        if getattr(response, "template", None) == "website_sale.payment":
            response.template = PAGE_TEMPLATES[response.template]
            response.qcontext.update(self._ocd_payment_values(response.qcontext.get("order") or request.cart, post))
        return response

    def _ocd_payment_values(self, order, post):
        env = request.env
        lines = order.order_line.filtered(lambda line: not line.is_delivery)
        count = int(sum(lines.mapped("product_uom_qty")))
        shipping = order.partner_shipping_id
        place = ", ".join(part for part in (shipping.district_id.name, shipping.city_id.name or shipping.city) if part)
        return common.page_values(
            "payer_commande",
            back="/shop/checkout",
            back_label=env._("Back to the delivery"),
            step=2,
            step_total=3,
            step_label=env._("Step %(step)s of %(total)s", step=2, total=3),
            items_label=env._("%s items", count) if count != 1 else env._("1 item"),
            items_amount=common.money(sum(lines.mapped("price_total")), order.currency_id),
            delivery_label=env._("Delivery to %s", place) if place else env._("Delivery"),
            parcel_lines=[{
                "label": env._("Delivery of the parcel of %s", line.vendor_id.name) if line.vendor_id
                else env._("Delivery of the parcel of OCD Live"),
                "sub": env._("from %s", line.origin_city_id.name) if line.origin_city_id else "",
                "amount": common.money(line.amount, order.currency_id) if line.amount else env._("Free"),
            } for line in order.ocd_delivery_line_ids],
            delivery_amount=common.money(order.amount_delivery, order.currency_id) if order.amount_delivery else env._("Free"),
            total=common.money(order.amount_total, order.currency_id),
            country=shipping.country_id,
            submit_button_label=env._("Pay %s", common.money(order.amount_total, order.currency_id)),
            payment_error=post.get("error") or False,
            display_submit_button=True,
        )

    # === CONFIRMATION AND TRACKING (design: Suivi) === #

    @http.route()
    def shop_payment_confirmation(self, **post):
        order_id = request.session.get("sale_last_order_id")
        order = request.env["sale.order"].sudo().browse(order_id).exists() if order_id else False
        if not order:
            return request.redirect("/shop")
        return request.redirect(f"/ocd/suivi/{order.id}?{urlencode({'access_token': order._portal_ensure_token()})}")

    @http.route("/ocd/suivi/<int:order_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def ocd_tracking(self, order_id, access_token=None, **kwargs):
        order = order_by_token(order_id, access_token)
        return request.render("ocd_live_shop.tracking", common.page_values(
            "suivi", **self._ocd_tracking_values(order, access_token, **kwargs)
        ))

    def _ocd_tracking_values(self, order, access_token, **kwargs):
        env = request.env
        parcels = order.picking_ids.filtered("ocd_is_parcel").sorted("id")
        open_parcels = parcels.filtered(lambda p: p.ocd_stage not in ("delivered", "returned", "cancelled"))
        first_name = (order.partner_id.name or "").split()[0] if order.partner_id.name else ""
        if order.state in ("draft", "sent"):
            title = env._("Your order is waiting for the payment")
        elif parcels and not open_parcels:
            title = env._("Delivered. Thank you %s!", first_name)
        elif parcels.filtered(lambda p: p.ocd_stage == "on_the_way"):
            title = env._("Your order is on the way")
        else:
            title = env._("Thank you %s, your order is confirmed", first_name)
        paid = order.transaction_ids.filtered(lambda tx: tx.state == "done").sorted("id")[-1:]
        if paid:
            pay_line = env._("paid with %s", paid.payment_method_id.name or paid.provider_id.name)
        elif parcels.filtered(lambda p: p.ocd_cod_state == "to_collect"):
            pay_line = env._("to pay at the delivery")
        else:
            pay_line = ""
        shipping = order.partner_shipping_id
        delivered_all = bool(parcels) and not open_parcels
        return {
            "order": order,
            "access_token": access_token,
            "header_name": env._("My order"),
            "step": 3,
            "step_total": 3,
            "step_label": env._("Step %(step)s of %(total)s", step=3, total=3),
            "title": title,
            "summary_line": " · ".join(part for part in (
                order.name, common.money(order.amount_total, order.currency_id), pay_line,
            ) if part),
            "parcels": [self._ocd_parcel_row(parcel) for parcel in parcels],
            "delivered_all": delivered_all,
            "rating": order.ocd_rating,
            "rated": bool(kwargs.get("note")),
            "can_return": delivered_all and order._ocd_can_request_return(),
            "return_label": env._("Ask for a return (%s days)", order.company_id.ocd_return_days),
            "return_requested": bool(order.ocd_return_requested_at),
            "address_name": shipping.name,
            "address_line": " · ".join(part for part in (
                ", ".join(part for part in (shipping.district_id.name, shipping.city_id.name or shipping.city) if part),
                shipping.delivery_landmark,
            ) if part),
            "bottom_cta": {"href": "/shop", "label": env._("Continue shopping")},
            "base": f"/ocd/suivi/{order.id}",
            "token_query": urlencode({"access_token": access_token}),
        }

    def _ocd_parcel_row(self, parcel):
        env = request.env
        stage = parcel.ocd_stage
        steps = [
            ("prepared", env._("Prepared"), stage in ("ready", "picked", "on_the_way", "delivered") or bool(parcel.ocd_ready_at)),
            ("route", env._("On the way"), stage in ("on_the_way", "delivered")),
            ("done", env._("Delivered"), stage == "delivered"),
        ]
        pills = {
            "to_prepare": ("prep", env._("Being prepared")),
            "ready": ("ready", env._("Ready")),
            "picked": ("ready", env._("Picked up")),
            "on_the_way": ("route", env._("On the way")),
            "delivered": ("done", env._("Delivered")),
            "problem": ("problem", env._("Delivery to set again")),
            "returned": ("problem", env._("Returned")),
            "cancelled": ("problem", env._("Cancelled")),
        }
        pill, pill_label = pills.get(stage, ("ready", ""))
        courier = parcel.ocd_courier_id
        vendor = parcel.ocd_vendor_id
        items = ", ".join(
            f"{move.product_id.name} × {int(move.product_uom_qty)}" if move.product_uom_qty != 1 else move.product_id.name
            for move in parcel.move_ids
        )
        phone = re.sub(r"\D", "", courier.phone or "") if courier else ""
        if courier and courier == vendor:
            who = env._("%s delivers your parcel", courier.name)
        elif courier:
            who = env._("%s, OCD courier, delivers your parcel", courier.name)
        else:
            who = env._("OCD Live chooses your courier")
        done_line = ""
        if stage == "delivered" and parcel.ocd_delivered_at:
            local = parcel.company_id._ocd_to_local(parcel.ocd_delivered_at)
            done_line = env._("Delivered at %s. Code checked.", local.strftime("%H:%M"))
        elif stage == "problem":
            done_line = env._("The courier could not deliver. OCD Live calls you to choose a new time.")
        return {
            "parcel": parcel,
            "title": env._("Parcel of %s", vendor.name) if vendor else env._("Parcel of OCD Live"),
            "sub": " · ".join(part for part in (items, parcel.ocd_parcel_label) if part),
            "pill": pill,
            "pill_label": pill_label,
            "steps": [{"key": key, "label": label, "on": on} for key, label, on in steps],
            "initials": common.initials(courier.name) if courier else "OCD",
            "who": who,
            "phone": phone if stage == "on_the_way" else "",
            "call_aria": env._("Call %s", courier.name) if courier else "",
            "code": parcel.sudo().ocd_delivery_code if stage == "on_the_way" else False,
            "done_line": done_line,
        }

    @http.route("/ocd/suivi/<int:order_id>/note", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ocd_tracking_rate(self, order_id, access_token=None, stars=None, **post):
        order = order_by_token(order_id, access_token)
        try:
            order._ocd_rate(int(stars or 0))
        except (UserError, ValueError):
            pass
        return request.redirect(f"/ocd/suivi/{order.id}?{urlencode({'access_token': access_token, 'note': 1})}")

    @http.route("/ocd/suivi/<int:order_id>/retour", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ocd_tracking_return(self, order_id, access_token=None, **post):
        order = order_by_token(order_id, access_token)
        try:
            order._ocd_request_return()
        except UserError:
            pass
        return request.redirect(f"/ocd/suivi/{order.id}?{urlencode({'access_token': access_token})}")


class OcdCart(Cart):
    """Cart of Odoo with the look of the validated design (Panier)."""

    @http.route()
    def cart(self, id=None, access_token=None, **post):
        response = super().cart(id=id, access_token=access_token, **post)
        if getattr(response, "template", None) == "website_sale.cart":
            response.template = PAGE_TEMPLATES[response.template]
            response.qcontext.update(self._ocd_cart_values(response.qcontext.get("website_sale_order"), post))
        return response

    def _ocd_cart_values(self, order, post):
        env = request.env
        lines = order.order_line.filtered(lambda line: not line.is_delivery and not line.combo_item_id) if order else []
        rows = []
        for line in lines:
            template = line.product_id.product_tmpl_id
            variant = ", ".join(line.product_id.product_template_attribute_value_ids.mapped("name"))
            qty = int(line.product_uom_qty)
            rows.append({
                "line": line,
                "name": template.name,
                "variant": variant,
                "price": common.money(line.price_total, order.currency_id),
                "qty": qty,
                "image": shop_common.image_url(template, "image_128"),
                "less_aria": env._("One %s less", template.name),
                "more_aria": env._("One %s more", template.name),
            })
        count = int(sum(line.product_uom_qty for line in lines))
        subtotal = common.money(sum(line.price_total for line in lines), order.currency_id) if order else ""
        return common.page_values(
            "panier",
            back="/shop",
            back_label=env._("Back to the shop"),
            header_h1=env._("My cart"),
            rows=rows,
            count_line=env._("%s items", count) if count != 1 else env._("1 item"),
            subtotal=subtotal,
            bottom_cta={"href": "/shop/checkout", "label": env._("Order · %s", subtotal)} if rows else None,
            cart_error=post.get("erreur"),
        )

    @http.route("/ocd/panier/ligne", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ocd_cart_line(self, line_id=None, quantity=None, **post):
        """Change the quantity of a line of the cart (0 removes it), with the checks of Odoo."""
        order = request.cart
        if order and str(line_id or "").isdigit():
            try:
                values = self.update_cart(line_id=int(line_id), quantity=max(0, int(quantity or 0)))
            except (UserError, ValidationError, ValueError) as exc:
                return request.redirect(f"/shop/cart?{urlencode({'erreur': exc.args[0] if exc.args else ''})}")
            if values.get("warning"):
                return request.redirect(f"/shop/cart?{urlencode({'erreur': values['warning']})}")
        return request.redirect("/shop/cart")

    def _ocd_selected_variant(self, template, post):
        """The variant of the values chosen on the product page."""
        template = template.sudo()
        chosen = request.env["product.template.attribute.value"].sudo()
        for line in template.valid_product_template_attribute_line_ids:
            value = post.get(f"attribute_{line.id}")
            if value and str(value).isdigit():
                chosen |= line.product_template_value_ids.filtered(lambda v: v.id == int(value))
        if not chosen:
            return template.product_variant_ids[:1], chosen
        variant_values = chosen.filtered(lambda v: v.attribute_id.create_variant != "no_variant")
        variant = template._get_variant_for_combination(variant_values) if variant_values else template.product_variant_ids[:1]
        if not variant and template._is_combination_possible(chosen):
            variant = template._create_product_variant(chosen)
        return variant, chosen.filtered(lambda v: v.attribute_id.create_variant == "no_variant")

    @http.route("/ocd/panier/ajouter", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ocd_add(self, product_template_id=None, quantity=1, **post):
        """Add the product chosen on the product page to the cart of Odoo, then open the cart."""
        template = request.env["product.template"].sudo().browse(int(product_template_id or 0)).exists()
        if not template:
            raise request.not_found()
        variant, no_variant_values = self._ocd_selected_variant(template, post)
        try:
            qty = max(1, int(quantity or 1))
        except ValueError:
            qty = 1
        try:
            if not variant:
                raise UserError(request.env._("This choice is not available."))
            self.add_to_cart(
                product_template_id=template.id,
                product_id=variant.id,
                quantity=qty,
                no_variant_attribute_value_ids=no_variant_values.ids or None,
            )
        except (UserError, ValidationError) as exc:
            return request.redirect(f"{template.website_url}?{urlencode({'erreur': exc.args[0]})}")
        return request.redirect("/shop/cart")


class OcdShopPaymentStatus(PaymentStatus):
    """While Odoo processes the payment of an order of the shop (Mobile Money confirmed on the
    phone...), its waiting page wears the look of OCD Live, then sends the customer to the
    confirmation, which opens the tracking of the order."""

    def get_payment_status_template_xmlid(self, tx):
        orders = tx.sudo().sale_order_ids if tx else request.env["sale.order"]
        if orders.filtered("website_id"):
            return "ocd_live.payment_status"
        return super().get_payment_status_template_xmlid(tx)
