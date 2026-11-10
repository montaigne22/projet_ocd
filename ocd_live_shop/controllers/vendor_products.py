import re

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live.controllers import common

from . import shop_common

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_QTY = 9999


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
        rows = []
        for product in products:
            qty = sum(shop_common.free_qty(v) for v in product.product_variant_ids) if shop_common.tracked(product) else None
            status, status_label = self._status(product, qty)
            rows.append({
                "product": product,
                "price": common.money(product.list_price, product.currency_id),
                "image": shop_common.image_url(product, "image_128"),
                "qty": qty,
                "single": len(product.product_variant_ids) == 1,
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
        digits = re.sub(r"[^\d]", "", price or "")
        if not digits or int(digits) <= 0:
            errors["price"] = env._("Write a price in francs, for example 3000.")
        try:
            qty = min(max(int(quantity or 1), 0), MAX_QTY)
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
            # sudo: the vendor has no account; the product waits for the check of the team
            product = env["product.template"].sudo().create({
                "name": name,
                "list_price": int(digits),
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

    @http.route("/ocd/espace/moi/produits/<int:product_id>/stock", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_stock(self, product_id, quantity=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor or len(product.product_variant_ids) != 1:
            raise request.not_found()
        try:
            qty = min(max(int(quantity or 0), 0), MAX_QTY)
        except ValueError:
            return request.redirect("/ocd/espace/moi/produits")
        if not shop_common.tracked(product):
            product.write({"is_storable": True, "allow_out_of_stock_order": False})
        product._ocd_set_stock(qty)
        return request.redirect(f"/ocd/espace/moi/produits#produit-{product.id}")
