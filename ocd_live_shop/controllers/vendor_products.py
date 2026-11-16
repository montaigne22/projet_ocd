import re
import uuid

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import BinaryBytes, consteq

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from ..models.product_product import MAX_STOCK
from . import shop_common

# A price this high is a typo (an extra zero), not a product
MAX_PRICE = 1_000_000_000
# The photo of a form refused for its name or its price, waiting for the next try
PENDING_PHOTO = "ocd_pending_product_photo"
# The token of a form of « My products » (uuid4().hex)
FORM_TOKEN = re.compile(r"[0-9a-f]{32}")


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
                "refusal": product._ocd_refusal_text(),
                "can_correct": product._ocd_vendor_can_correct(),
                "less_aria": request.env._("One %s less", product.name),
                "more_aria": request.env._("One %s more", product.name),
            })
        return rows

    def _form_values(self, values=None, errors=None, kept=None, form_token=None, product=None):
        """What the form of a product needs (vendor_product_form): its token (a second sending
        adds nothing), the photo kept after an error, and what the phone checks before sending
        (the server checks it again)."""
        env = request.env
        company = common.company()
        max_mb = company._ocd_vendor_photo_max_bytes() // (1024 * 1024)
        return {
            "product": product or False,
            "current_photo": shop_common.image_url(product, "image_512") if product and product.image_128 else False,
            "refusal": product._ocd_refusal_text() if product else False,
            "values": values or {},
            "errors": errors or {},
            "form_token": form_token or uuid.uuid4().hex,
            "kept_photo": self._kept_values(kept),
            "currency_symbol": company.currency_id.symbol,
            "currency_decimals": company.currency_id.decimal_places,
            "photo_gallery": company.ocd_vendor_photo_gallery,
            "photo_px": company.ocd_vendor_photo_px or 0,
            "photo_max_mb": max_mb,
            "form_messages": {
                "name": env._("Write the name of the product."),
                "price": env._("Write one price, without cents or dash, for example 3000."),
                "price_empty": env._("Write a price in francs, for example 3000."),
                "photo": env._("Add a photo of your product."),
                "photo_big": env._("The photo is too big (%s MB at most).", max_mb),
                "sending": env._("Sending…"),
            },
        }

    def _render(self, vendor, values=None, errors=None, sent=False, kept=None, form_token=None):
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
            sent=sent,
            photo_error=request.params.get("photo_erreur"),
            boutique_url=request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}"
            if vendor.ocd_vendor_state == "approved" else False,
            **self._form_values(values, errors, kept, form_token),
        ))

    def _render_correct(self, vendor, product, values=None, errors=None, kept=None):
        env = request.env
        if values is None:
            currency = product.currency_id
            price = product.list_price
            values = {
                "name": product.name,
                "price": str(int(price)) if currency.decimal_places == 0 or price == int(price)
                else f"{price:.{currency.decimal_places}f}",
            }
        return request.render("ocd_live_shop.vendor_product_edit", common.page_values(
            "mes_produits",
            back="/ocd/espace/moi/produits",
            back_label=env._("Back to my products"),
            header_title=env._("My products"),
            vendor=vendor,
            sent=False,
            **self._form_values(values, errors, kept, product=product),
        ))

    def _check_fields(self, name, price):
        """(errors, name, price) of the name and the price typed by the vendor."""
        env = request.env
        errors = {}
        name = common.clean_text(name, 120)
        if not name:
            errors["name"] = env._("Write the name of the product.")
        amount = read_price(price)
        if amount is None:
            errors["price"] = price_error(price)
        return errors, name, amount

    @http.route("/ocd/espace/moi/produits", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def products(self, envoye=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render(vendor, sent=bool(envoye))

    # === PHOTO KEPT AFTER AN ERROR === #
    # A form refused for its name or its price must not ask for the photo again (taken again on a
    # phone, sent again on a slow network): the photo received waits in an attachment of the
    # vendor, shown in the form and sent back by its token. One at a time per vendor.

    def _read_photo(self, photo):
        """(bytes, filename, error) of the photo sent in the form; (None, None, None) if none."""
        if not photo or not getattr(photo, "filename", None):
            return None, None, None
        env = request.env
        company = common.company()
        limit = company._ocd_vendor_photo_max_bytes()
        data = photo.read(limit + 1)
        if len(data) > limit:
            return None, None, env._("The photo is too big (%s MB at most).", limit // (1024 * 1024))
        if not data or not (photo.mimetype or "").startswith("image/"):
            return None, None, env._("Add a photo of your product.")
        return data, photo.filename, None

    def _pending_photos(self, vendor):
        return request.env["ir.attachment"].sudo().search([
            ("res_model", "=", "res.partner"), ("res_id", "=", vendor.id), ("description", "=", PENDING_PHOTO),
        ])

    def _keep_photo(self, vendor, data, filename):
        """Keep the photo of a refused form for the next try (it replaces the one kept before)."""
        self._pending_photos(vendor).unlink()
        attachment = request.env["ir.attachment"].sudo().create({
            "name": filename or "photo",
            "raw": data,
            "res_model": "res.partner",
            "res_id": vendor.id,
            "description": PENDING_PHOTO,
        })
        attachment.generate_access_token()
        return attachment

    def _kept_photo(self, vendor, kept):
        """The photo kept for `vendor`, from the value `<id>:<token>` sent back by the form."""
        attachment_id, _sep, token = (kept or "").partition(":")
        if not attachment_id.isdigit() or not token:
            return request.env["ir.attachment"]
        attachment = self._pending_photos(vendor).filtered(lambda a: a.id == int(attachment_id))
        if not attachment or not consteq(attachment.access_token or "", token):
            return request.env["ir.attachment"]
        return attachment

    @staticmethod
    def _kept_values(attachment):
        if not attachment:
            return False
        return {
            "value": f"{attachment.id}:{attachment.access_token}",
            "url": f"/web/image/{attachment.id}?access_token={attachment.access_token}",
        }

    # === ADD A PRODUCT === #

    @http.route("/ocd/espace/moi/produits", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def product_add(self, name=None, price=None, quantity=None, photo=None, photo_kept=None, form_token=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        Product = env["product.template"].sudo()
        sent = "/ocd/espace/moi/produits?envoye=1"
        token = form_token if form_token and FORM_TOKEN.fullmatch(form_token) else None
        if token:
            # The same form sent twice (a second tap, a request sent again by a slow network):
            # one at a time, and the second one finds the product of the first
            env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", [vendor.id, int(token[:7], 16)])
            if Product.search_count([("ocd_vendor_id", "=", vendor.id), ("ocd_form_token", "=", token)], limit=1):
                return request.redirect(sent)
        errors, name, amount = self._check_fields(name, price)
        try:
            qty = min(max(int(quantity or 1), 0), MAX_STOCK)
        except ValueError:
            qty = 1
        data, filename, photo_error = self._read_photo(photo)
        kept = self._kept_photo(vendor, photo_kept) if data is None else env["ir.attachment"]
        if photo_error:
            errors["photo"] = photo_error
        elif data is None and kept:
            data, filename = kept.raw, kept.name
        elif data is None:
            errors["photo"] = env._("Add a photo of your product.")
        values = {"name": name, "price": price, "quantity": qty}
        if errors:
            if data is not None and not kept:
                kept = self._keep_photo(vendor, data, filename)
            return self._render(vendor, values=values, errors=errors, kept=kept, form_token=token)
        try:
            # sudo: the vendor has no account; the product waits for the check of the team.
            # A refused product leaves nothing behind (savepoint).
            with env.cr.savepoint():
                product = Product.create({
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
                    "image_1920": BinaryBytes(data, filename=filename),
                    "ocd_form_token": token,
                })
                product._ocd_set_stock(qty)
        except (UserError, ValidationError) as exc:
            # Not an image Odoo can read: no photo to keep
            return self._render(vendor, values=values, errors={"photo": exc.args[0]}, form_token=token)
        self._pending_photos(vendor).unlink()
        return request.redirect(sent)

    # === CORRECT A PRODUCT (refused, or waiting for the check) === #

    @http.route("/ocd/espace/moi/produits/<int:product_id>/modifier", type="http", auth="public", website=True,
                methods=["GET", "POST"], sitemap=False)
    def product_correct(self, product_id, name=None, price=None, photo=None, photo_kept=None, **post):
        """The vendor corrects a product: a refused one goes back to the check of the team (who
        sees why it was refused); one waiting for the check is just corrected. The photo is kept
        when none is sent."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        product = env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor:
            raise request.not_found()
        back = f"/ocd/espace/moi/produits#produit-{product.id}"
        if not product._ocd_vendor_can_correct():
            return request.redirect(back)
        if request.httprequest.method != "POST":
            return self._render_correct(vendor, product)
        errors, name, amount = self._check_fields(name, price)
        data, filename, photo_error = self._read_photo(photo)
        kept = self._kept_photo(vendor, photo_kept) if data is None else env["ir.attachment"]
        if photo_error:
            errors["photo"] = photo_error
        elif data is None and kept:
            data, filename = kept.raw, kept.name
        values = {"name": name, "price": price}
        if errors:
            if data is not None and not kept:
                kept = self._keep_photo(vendor, data, filename)
            return self._render_correct(vendor, product, values, errors, kept)
        changes = {"name": name, "list_price": amount}
        if data is not None:
            changes["image_1920"] = BinaryBytes(data, filename=filename)
        resent = product.ocd_review_state == "refused"
        try:
            with env.cr.savepoint():
                product._ocd_vendor_correct(changes)
        except (UserError, ValidationError) as exc:
            return self._render_correct(vendor, product, values, {"photo": exc.args[0]})
        self._pending_photos(vendor).unlink()
        return request.redirect(f"/ocd/espace/moi/produits?envoye=1#produit-{product.id}" if resent else back)

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
        limit = common.company()._ocd_vendor_photo_max_bytes()
        data = photo.read(limit + 1)
        if len(data) > limit or not (photo.mimetype or "").startswith("image/"):
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
