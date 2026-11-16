from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from ..models.product_product import MAX_STOCK
from . import shop_common

MAX_PHOTO_BYTES = 10 * 1024 * 1024
# A price this high is a typo (an extra zero), not a product
MAX_PRICE = 1_000_000_000


def read_price(text):
    """The price typed by the vendor in the currency of the shop, or None when it is not one
    price (see `tools.parse_amount`), not above 0 or absurdly high."""
    currency = common.company().currency_id
    price = tools.parse_amount(text, currency.decimal_places, currency.symbol)
    return price if price and 0 < price < MAX_PRICE else None


def price_error(text):
    """The message for a price that `read_price` refused: nothing written, or not one price."""
    env = request.env
    if not (text or "").strip():
        return env._("Write a price in francs, for example 3000.")
    return env._("Write one price, without cents or dash, for example 3000.")


class OcdVendorProducts(http.Controller):
    """My products (design MesProduits): the vendor adds a product from the phone (photo, name,
    price, quantity), checked by the team before it shows in the boutique, and changes the
    quantity of the products. At 0 the product stays visible with "Sold out"."""

    def _vendor(self):
        return common.current_vendor()

    def _status(self, product, tracked_qty):
        env = request.env
        if product.ocd_review_state == "to_check":
            return "check", env._("To check")
        if product.ocd_review_state == "refused":
            return "refused", env._("Refused")
        if not product.is_published:
            return "hidden", env._("Not shown")
        if tracked_qty is not None and tracked_qty <= 0:
            return "out", env._("Sold out")
        return "on", env._("On sale")

    def _rows(self, vendor):
        products = request.env["product.template"].sudo().search(
            [("ocd_vendor_id", "=", vendor.id)], order="create_date desc, id desc"
        )
        # The free stock of all the products in one query
        free = products.product_variant_ids._ocd_free_qties()
        rows = []
        for product in products:
            qty = sum(free[v.id] for v in product.product_variant_ids) if shop_common.tracked(product) else None
            status, status_label = self._status(product, qty)
            colours = product.attribute_line_ids.filtered(
                lambda line: line.attribute_id.display_type == "color"
            ).product_template_value_ids._only_active()
            rows.append({
                "product": product,
                "price": common.money(product.list_price, product.currency_id),
                "image": shop_common.image_url(product, "image_128"),
                "qty": qty,
                "single": len(product.product_variant_ids) == 1,
                "colours": [
                    {
                        "value": value,
                        "image": product._ocd_photo(value, "ocd_image")["src"] if value.ocd_image else False,
                        "swatch": value.html_color or "#FFFFFF",
                    }
                    for value in colours
                ],
                "colours_done": len(colours.filtered("ocd_image")),
                "status": status,
                "status_label": status_label,
                "less_aria": request.env._("One %s less", product.name),
                "more_aria": request.env._("One %s more", product.name),
            })
        return rows

    def _render(self, vendor, values=None, errors=None, sent=False):
        env = request.env
        rows = self._rows(vendor)
        on_sale = [row for row in rows if row["status"] in ("on", "out")]
        return request.render("ocd_live_shop.vendor_products", common.page_values(
            "mes_produits",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My products"),
            vendor=vendor,
            rows=rows,
            count_line=env._("%s on sale", len(on_sale)),
            values=values or {},
            errors=errors or {},
            sent=sent,
            photo_error=request.params.get("photo_erreur"),
            currency_symbol=common.company().currency_id.symbol,
            boutique_url=request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}"
            if vendor.ocd_vendor_state == "approved" else False,
        ))

    @http.route("/ocd/espace/moi/produits", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def products(self, envoye=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render(vendor, sent=bool(envoye))

    @http.route("/ocd/espace/moi/produits", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def product_add(self, name=None, price=None, quantity=None, photo=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        errors = {}
        name = common.clean_text(name, 120)
        if not name:
            errors["name"] = env._("Write the name of the product.")
        amount = read_price(price)
        if amount is None:
            errors["price"] = price_error(price)
        try:
            qty = min(max(int(quantity or 1), 0), MAX_STOCK)
        except ValueError:
            qty = 1
        image = False
        if photo and getattr(photo, "filename", None):
            data = photo.read(MAX_PHOTO_BYTES + 1)
            if len(data) > MAX_PHOTO_BYTES:
                errors["photo"] = env._("The photo is too big (10 MB at most).")
            elif not (photo.mimetype or "").startswith("image/"):
                errors["photo"] = env._("Add a photo of your product.")
            else:
                image = BinaryBytes(data, filename=photo.filename)
        else:
            errors["photo"] = env._("Add a photo of your product.")
        if errors:
            return self._render(vendor, values={"name": name, "price": price, "quantity": qty}, errors=errors)
        try:
            # sudo: the vendor has no account; the product waits for the check of the team.
            # A refused product leaves nothing behind (savepoint).
            with env.cr.savepoint():
                product = env["product.template"].sudo().create({
                    "name": name,
                    "list_price": amount,
                    "type": "consu",
                    "is_storable": True,
                    "allow_out_of_stock_order": False,
                    "sale_ok": True,
                    "purchase_ok": False,
                    "ocd_vendor_id": vendor.id,
                    "ocd_review_state": "to_check",
                    "is_published": False,
                    "image_1920": image,
                })
                product._ocd_set_stock(qty)
        except (UserError, ValidationError) as exc:
            return self._render(vendor, values={"name": name, "price": price, "quantity": qty},
                                errors={"photo": exc.args[0]})
        return request.redirect("/ocd/espace/moi/produits?envoye=1")

    @http.route("/ocd/espace/moi/produits/<int:product_id>/couleur/<int:value_id>", type="http", auth="public",
                website=True, methods=["POST"], sitemap=False)
    def product_colour_photo(self, product_id, value_id, photo=None, **post):
        """The photo of the product in a colour: shown on the page as soon as the colour is
        chosen. The team sees it in the history of the product and can change it."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = request.env["product.template"].sudo().browse(product_id).exists()
        value = request.env["product.template.attribute.value"].sudo().browse(value_id).exists()
        if not product or product.ocd_vendor_id != vendor or not value or value.product_tmpl_id != product:
            raise request.not_found()
        anchor = f"/ocd/espace/moi/produits#produit-{product.id}"
        if not photo or not getattr(photo, "filename", None):
            return request.redirect(anchor)
        data = photo.read(MAX_PHOTO_BYTES + 1)
        if len(data) > MAX_PHOTO_BYTES or not (photo.mimetype or "").startswith("image/"):
            return request.redirect(f"/ocd/espace/moi/produits?photo_erreur={product.id}#produit-{product.id}")
        try:
            with request.env.cr.savepoint():
                value.ocd_image = BinaryBytes(data, filename=photo.filename)
        except (UserError, ValidationError):
            return request.redirect(f"/ocd/espace/moi/produits?photo_erreur={product.id}#produit-{product.id}")
        product.message_post(body=request.env._(
            "%(vendor)s added the photo of the colour %(colour)s.", vendor=vendor.name, colour=value.name,
        ))
        return request.redirect(anchor)

    @http.route("/ocd/espace/moi/produits/<int:product_id>/stock", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_stock(self, product_id, delta=None, quantity=None, **post):
        """− and + of a product: `delta` (-1, +1) is added to the stock of the moment, so a sale
        made since the page was shown is kept, and two quick taps count twice. `quantity` (the
        stock to have) is still read for a page shown before this change."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor or len(product.product_variant_ids) != 1:
            raise request.not_found()
        anchor = f"/ocd/espace/moi/produits#produit-{product.id}"
        try:
            delta = int(delta) if delta not in (None, "") else None
            quantity = int(quantity) if delta is None and quantity not in (None, "") else None
        except ValueError:
            return request.redirect(anchor)
        if delta is None and quantity is None:
            return request.redirect(anchor)
        if not shop_common.tracked(product):
            product.write({"is_storable": True, "allow_out_of_stock_order": False})
        if delta is not None:
            product._ocd_change_stock(max(min(delta, MAX_STOCK), -MAX_STOCK))
        else:
            product._ocd_set_stock(min(max(quantity, 0), MAX_STOCK))
        return request.redirect(anchor)
