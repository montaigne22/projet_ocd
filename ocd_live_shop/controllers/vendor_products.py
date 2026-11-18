import re
import uuid
from collections import defaultdict
from urllib.parse import urlencode

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
# The filters by state show from this number of products
FILTER_FROM = 5
# The ways to move a product in the boutique
MOVES = ("first", "up", "down")
# The sizes of the photos of the products a vendor sees in their space
PHOTO_SIZES = ("image_128", "image_256", "image_512", "image_1024")


def vendor_photo_url(product, size="image_128"):
    """The photo of a product of the vendor, for « My products », whether it is online or not."""
    if not product or not product.sudo().image_128:
        return False
    stamp = product._ocd_photo_stamp(product.sudo())
    return f"/ocd/espace/moi/produits/{product.id}/photo/{size}?unique={stamp}"


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


# === PHOTO SENT BY A VENDOR, KEPT AFTER AN ERROR === #
# A form refused for a field must not ask for the photo again (taken again on a phone, sent again
# on a slow network): the photo received waits in an attachment of the vendor, shown in the form
# and sent back by its token. One at a time per vendor, for « My products » and « My stores ».


def read_photo(photo, missing=None):
    """(bytes, filename, error) of the photo sent in a form; (None, None, None) if none."""
    if not photo or not getattr(photo, "filename", None):
        return None, None, None
    env = request.env
    limit = common.company()._ocd_vendor_photo_max_bytes()
    data = photo.read(limit + 1)
    if len(data) > limit:
        return None, None, env._("The photo is too big (%s MB at most).", limit // (1024 * 1024))
    if not data or not (photo.mimetype or "").startswith("image/"):
        return None, None, missing or env._("Add a photo of your product.")
    return data, photo.filename, None


def pending_photos(vendor):
    return request.env["ir.attachment"].sudo().search([
        ("res_model", "=", "res.partner"), ("res_id", "=", vendor.id), ("description", "=", PENDING_PHOTO),
    ])


def keep_photo(vendor, data, filename):
    """Keep the photo of a refused form for the next try (it replaces the one kept before)."""
    pending_photos(vendor).unlink()
    attachment = request.env["ir.attachment"].sudo().create({
        "name": filename or "photo",
        "raw": data,
        "res_model": "res.partner",
        "res_id": vendor.id,
        "description": PENDING_PHOTO,
    })
    attachment.generate_access_token()
    return attachment


def kept_photo(vendor, kept):
    """The photo kept for `vendor`, from the value `<id>:<token>` sent back by the form."""
    attachment_id, _sep, token = (kept or "").partition(":")
    if not attachment_id.isdigit() or not token:
        return request.env["ir.attachment"]
    attachment = pending_photos(vendor).filtered(lambda a: a.id == int(attachment_id))
    if not attachment or not consteq(attachment.access_token or "", token):
        return request.env["ir.attachment"]
    return attachment


def kept_values(attachment):
    if not attachment:
        return False
    return {
        "value": f"{attachment.id}:{attachment.access_token}",
        "url": f"/web/image/{attachment.id}?access_token={attachment.access_token}",
    }


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
            if product.ocd_vendor_retired:
                return "retired", env._("Taken off sale")
            return "hidden", env._("Not shown")
        if tracked_qty is not None and tracked_qty <= 0:
            return "out", env._("Sold out")
        return "on", env._("On sale")

    def _waiting_counts(self, variants):
        """{template id: customers waiting for it to be back} for `variants`, in one query."""
        counts = defaultdict(int)
        groups = request.env["ocd.stock.alert"].sudo()._read_group(
            [("product_id", "in", variants.ids), ("state", "=", "waiting")], ["product_id"], ["__count"]
        )
        for variant, count in groups:
            counts[variant.product_tmpl_id.id] += count
        return counts

    def _rows(self, vendor):
        """The products of the vendor in the order of their boutique, with what they tell: the
        stock free to sell, the customers who wrote on WhatsApp or wait for it to be back."""
        env = request.env
        products = env["product.template"]._ocd_vendor_products(vendor)
        variants = products.product_variant_ids
        # The free stock and the waiting customers of all the products: one query each
        free = variants._ocd_free_qties()
        waiting = self._waiting_counts(variants)
        # From two places on, the stock of each place (chantier 18): one query for the page
        places = vendor._ocd_stock_places() if vendor._ocd_stock_per_place() else env["ocd.vendor.place"]
        by_place = variants._ocd_free_by_location(places.location_id) if places else {}
        root = request.httprequest.url_root.rstrip("/")
        limit = vendor._ocd_low_stock_limit()
        # The note of each product from the reviews of the buyers (chantier 2): one query
        Review = env["ocd.vendor.review"]
        review_stats = Review._ocd_product_stats(products)
        # « Sold: 14 in 30 days · last sale yesterday » (3.3, for every vendor sold by OCD): the
        # calculation of « My figures »
        Figures = env["ocd.vendor.figures"]
        sales = Figures._ocd_product_sales(vendor, products) if vendor.ocd_sale_mode == "ocd" else {}
        # The promos running (3.1): one query for the page
        promos = env["ocd.product.promo"]._ocd_running(products)
        rows = []
        for index, product in enumerate(products):
            qty = sum(free[v.id] for v in product.product_variant_ids) if shop_common.tracked(product) else None
            status, status_label = self._status(product, qty)
            low_line = self._low_line(product, free, limit) if status == "on" and qty is not None else False
            online = status in ("on", "out")
            clicks, waits = product.ocd_wa_clicks, waiting[product.id]
            colours = product.attribute_line_ids.filtered(
                lambda line: line.attribute_id.display_type == "color"
            ).product_template_value_ids._only_active()
            places_line = False
            if places and qty is not None:
                parts = [
                    f"{place.name} {sum(by_place.get((place.location_id.id, v.id), 0) for v in product.product_variant_ids)}"
                    for place in places
                ]
                places_line = env._("%(count)s in stock · %(places)s", count=qty, places=" · ".join(parts))
            promo = promos.get(product.id)
            rows.append({
                "product": product,
                "price": common.money(promo.price if promo else product.list_price, product.currency_id),
                "was": common.money(promo.reference_price, product.currency_id) if promo else False,
                "promo_line": env._("In promo: %(off)s %(until)s", off=promo._ocd_off_text(),
                                    until=promo._ocd_until_text(vendor._ocd_tz_name())) if promo else False,
                "promo_url": f"/ocd/espace/moi/produits/{product.id}/promo"
                if status in ("on", "out") else False,
                "promo_label": env._("My promo") if promo else env._("Put in promo"),
                # « My stock »: the sizes and the colours, or the stock of each place
                "stock_url": f"/ocd/espace/moi/produits/{product.id}/mon-stock"
                if places or len(product.product_variant_ids) > 1 else False,
                "per_place": bool(places),
                "places_line": places_line,
                "image": vendor_photo_url(product, "image_128"),
                "qty": qty,
                "single": len(product.product_variant_ids) == 1,
                "colours": [
                    {
                        "value": value,
                        "image": f"/ocd/espace/moi/produits/{product.id}/couleur/{value.id}/nouvelle"
                        f"?unique={product._ocd_photo_stamp(value)}" if value.ocd_image_pending
                        else product._ocd_photo(value, "ocd_image")["src"] if value.ocd_image else False,
                        "checking": value.ocd_image_state == "to_check" and bool(value.ocd_image_pending),
                        "refused": value.ocd_image_state == "refused" and bool(value.ocd_image_pending),
                        "swatch": value.html_color or "#FFFFFF",
                    }
                    for value in colours
                ],
                "colours_done": len(colours.filtered("ocd_image")),
                "status": status,
                "status_label": status_label,
                # Low on stock (chantier 21): the pieces left of the colours and sizes concerned
                "low": bool(low_line),
                "low_line": low_line,
                "sold_line": Figures._ocd_sold_line(vendor, *sales[product.id]) if product.id in sales else False,
                "review_line": (env._("★ %(note)s · 1 review", note=Review._ocd_note(review_stats[product.id][0]))
                                if review_stats[product.id][1] == 1 else
                                env._("★ %(note)s · %(count)s reviews", note=Review._ocd_note(review_stats[product.id][0]),
                                      count=review_stats[product.id][1])) if product.id in review_stats else False,
                # « M, L · Blue, Red »: its sizes and colours (chantier 21)
                "variants_line": " · ".join(
                    ", ".join(line.value_ids.sorted(lambda value: (value.sequence, value.id)).mapped("name"))
                    for line in product.attribute_line_ids if line.attribute_id.create_variant == "always"
                ) if len(product.product_variant_ids) > 1 else False,
                "refusal": product._ocd_refusal_text(),
                "can_correct": product._ocd_vendor_can_correct(),
                "can_change": product._ocd_vendor_can_change(),
                "can_retire": product._ocd_vendor_can_retire(),
                # A change waiting for the check, or refused (the product stays on sale as it was)
                "change_line": self._change_line(product),
                "change_refused": product.ocd_change_state == "refused",
                "less_aria": env._("One %s less", product.name),
                "more_aria": env._("One %s more", product.name),
                "more_label": env._("More for %s", product.name),
                # What the product already brought, counted by OCD (1.1 of the plan)
                "contacts_line": (env._("1 person wrote to you on WhatsApp") if clicks == 1
                                  else env._("%s people wrote to you on WhatsApp", clicks)) if clicks else False,
                "waiting_line": (env._("1 customer waits for it to be back") if waits == 1
                                 else env._("%s customers wait for it to be back", waits)) if waits else False,
                # Seen by the customers (1.2), shared (1.3), placed in the boutique (1.6)
                "public_url": product.website_url if online else False,
                "share": {
                    "url": root + product.website_url,
                    "text": f"{product.name} · {common.money(product.list_price, product.currency_id)}",
                    "image": f"/ocd/produit/{product.id}/partage.jpg?unique={product._ocd_photo_stamp(product)}",
                } if online and product.ocd_review_state == "approved" else False,
                "first": index == 0,
                "last": index == len(products) - 1,
            })
        return rows

    def _low_line(self, product, free, limit):
        """« Low stock · only 2 left », or the colours and sizes concerned: « Low stock: Blue, M ·
        only 2 left », « Low stock: Blue, M (2) · Red, L (1) »; False when the stock is fine."""
        if not limit:
            return False
        env = request.env
        low = product.product_variant_ids.filtered(lambda variant: 1 <= free.get(variant.id, 0) <= limit)
        if not low:
            return False
        if len(product.product_variant_ids) == 1:
            return env._("Low stock · only %s left", free[low.id])
        if len(low) == 1:
            return env._("Low stock: %(choice)s · only %(count)s left", choice=self._choice(low), count=free[low.id])
        return env._("Low stock: %s", " · ".join(f"{self._choice(variant)} ({free[variant.id]})" for variant in low))

    def _choice(self, variant):
        """« Blue, M »: the colour and the size of a variant."""
        return ", ".join(variant.product_template_attribute_value_ids.mapped("name")) or variant.name

    def _change_line(self, product):
        env = request.env
        if not product._ocd_vendor_can_change():
            return False
        if product.ocd_change_state == "to_check":
            return env._("Change being checked: %s. The version of today stays on sale.",
                         ", ".join(self._waiting_labels(product)) or env._("new name"))
        if product.ocd_change_state == "refused":
            return env._("Change refused: « %s ». The version before stays on sale.", product._ocd_change_refusal_text())
        return False

    def _waiting_labels(self, product):
        env = request.env
        labels = {"name": env._("new name"), "photos": env._("new photos"), "colours": env._("photos of the colours")}
        return [labels[part] for part in product._ocd_change_waiting() if part in labels]

    def _filters(self, rows, current):
        """The filters by state (1.4 of the plan), when the catalogue grows: [(key, label,
        count)], or [] for a short list or a list in one state."""
        env = request.env
        counts = defaultdict(int)
        for row in rows:
            counts[row["status"]] += 1
        low = sum(1 for row in rows if row["low"])
        if len(rows) < FILTER_FROM or (len(counts) < 2 and not low):
            return []
        counts["low"] = low  # not a state: the products on sale low on stock (chantier 21)
        labels = [("on", env._("On sale")), ("low", env._("Low stock")), ("out", env._("Sold out")),
                  ("check", env._("To check")), ("refused", env._("Refused")), ("retired", env._("Off sale")),
                  ("hidden", env._("Not shown"))]
        return [("all", env._("All"), len(rows))] + [
            (key, label, counts[key]) for key, label in labels if counts[key] or key == current
        ]

    def _form_values(self, values=None, errors=None, kept=None, form_token=None, product=None):
        """What the form of a product needs (vendor_product_form): its token (a second sending
        adds nothing), the photo kept after an error, and what the phone checks before sending
        (the server checks it again)."""
        env = request.env
        company = common.company()
        max_mb = company._ocd_vendor_photo_max_bytes() // (1024 * 1024)
        return {
            "product": product or False,
            "current_photo": vendor_photo_url(product, "image_512"),
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
            # Sizes and colours from the creation (chantier 21)
            **(self._variant_values(values or {}) if not product else {}),
            "form_messages": {
                "name": env._("Write the name of the product."),
                "price": env._("Write one price, without cents or dash, for example 3000."),
                "price_empty": env._("Write a price in francs, for example 3000."),
                "photo": env._("Add a photo of your product."),
                "photo_big": env._("The photo is too big (%s MB at most).", max_mb),
                "sending": env._("Sending…"),
            },
        }

    # === SIZES AND COLOURS (chantier 21, design TaillesCouleurs) === #

    def _variant_values(self, values):
        """The attributes offered to the vendors, the values ticked and the grid of the stock of
        each choice (a size and a colour) for the form of a new product."""
        env = request.env
        attributes = env["product.attribute"]._ocd_vendor_attributes()
        if not attributes:
            return {"vendor_attributes": [], "variant_grid": False, "team_url": False, "variant_total": ""}
        ticked = set(values.get("valeurs") or [])
        rows = [{
            "id": attribute.id,
            "name": attribute.name,
            "colour": attribute.display_type == "color",
            "values": [{
                "id": value.id,
                "name": value.name,
                "swatch": value.html_color or "#FFFFFF",
                "checked": value.id in ticked,
            } for value in attribute.value_ids.sorted(lambda value: (value.sequence, value.id))],
        } for attribute in attributes]
        grid = False
        Product = env["product.template"]
        chosen = Product._ocd_read_chosen_values(list(ticked)) if ticked else {}
        if chosen:
            try:
                combos = Product._ocd_combinations(chosen)
            except UserError:
                combos = []
            stock = values.get("stock") or {}
            cells = {key: {"key": key, "value": stock.get(key, ""), "label": ", ".join(v.name for v in combo)}
                     for combo, key in combos}
            if len(chosen) == 2:
                # Two attributes: the colours in rows (else the first), the other in columns
                first, second = list(chosen)
                rows_attr, cols_attr = (second, first) if second.display_type == "color" else (first, second)
                grid = {
                    "table": True,
                    "cols": [value.name for value in chosen[cols_attr]],
                    "rows": [{
                        "name": row.name,
                        "swatch": row.html_color if rows_attr.display_type == "color" else False,
                        "cells": [cells["-".join(str(i) for i in sorted((row.id, col.id)))] for col in chosen[cols_attr]],
                    } for row in chosen[rows_attr]],
                }
            else:
                grid = {"table": False, "cells": list(cells.values())}
        digits = re.sub(r"\D", "", common.company().phone or "")
        return {
            "vendor_attributes": rows,
            "variant_grid": grid,
            "variant_total": env._("%(pieces)s pieces · %(choices)s choices (a size and a colour each)"),
            "team_url": f"https://wa.me/{digits}?{urlencode({'text': env._('Hello, a size or a colour is missing for my products: ')})}"
            if len(digits) >= 8 else False,
        }

    def _read_variants(self, post):
        """The sizes and colours ticked ({attribute: values}), the stock of each choice and the
        error to show, for a new product."""
        env = request.env
        form = request.httprequest.form
        ticked = [int(value) for value in form.getlist("valeurs") if str(value).isdigit()]
        stock = {}
        for key, value in post.items():
            if key.startswith("stock_") and re.fullmatch(r"[0-9-]+", key[6:]):
                try:
                    stock[key[6:]] = min(max(int(value or 0), 0), MAX_STOCK)
                except ValueError:
                    stock[key[6:]] = 0
        if not post.get("variantes"):
            return {}, {}, ticked, stock, None
        chosen = env["product.template"]._ocd_read_chosen_values(ticked)
        if not chosen:
            return chosen, {}, ticked, stock, env._("Tick at least one size or one colour.")
        try:
            combos = env["product.template"]._ocd_combinations(chosen)
        except UserError as exc:
            return chosen, {}, ticked, stock, exc.args[0]
        if not any(key in stock for _combo, key in combos):
            # Sent without the grid (no JavaScript): the grid shows now, to fill in
            return chosen, {}, ticked, stock, env._("Write how many you have of each choice.")
        return chosen, stock, ticked, stock, None

    def _render(self, vendor, values=None, errors=None, sent=False, kept=None, form_token=None, state=None):
        env = request.env
        rows = self._rows(vendor)
        on_sale = [row for row in rows if row["status"] in ("on", "out")]
        filters = self._filters(rows, state)
        state = state if filters and state in {key for key, _label, _count in filters} else "all"
        return request.render("ocd_live_shop.vendor_products", common.page_values(
            "mes_produits",
            space_page="products",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My products"),
            vendor=vendor,
            rows=rows,
            count_line=env._("%s on sale", len(on_sale)),
            filters=filters,
            state=state,
            # The menu « More » of a product stays open after a move
            opened=int(request.params["ouvert"]) if str(request.params.get("ouvert", "")).isdigit() else False,
            sent=sent,
            photo_error=request.params.get("photo_erreur"),
            draft_hint=env._("Leaves by itself when the network is back, or at your next visit of My products."),
            draft_failed=env._("Not added: the photo could not be read. Add it again."),
            boutique_url=request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}"
            if vendor.ocd_vendor_state == "approved" else False,
            **self._form_values(values, errors, kept, form_token),
        ))

    def _price_text(self, product, price):
        """The price as the vendor types it: 3000, or 3000.50 for a currency with cents."""
        currency = product.currency_id
        return str(int(price)) if currency.decimal_places == 0 or price == int(price) \
            else f"{price:.{currency.decimal_places}f}"

    def _price_question(self, product, amount):
        """« You go from 15,000 F to 1,500 F, is that right? »: a big change of the price is
        confirmed by the vendor (2.1 of the plan)."""
        env = request.env
        currency = product.currency_id
        return {
            "text": env._("You go from %(before)s to %(after)s, is that right?",
                          before=common.money(product.list_price, currency), after=common.money(amount, currency)),
            "yes": env._("Yes, %s", common.money(amount, currency)),
            "value": self._price_text(product, amount),
        }

    def _render_correct(self, vendor, product, values=None, errors=None, kept=None, price_question=None):
        env = request.env
        if values is None:
            values = {
                # A change waiting for the check, or refused: the vendor sees it to correct it
                "name": product.ocd_change_name or product.name,
                "price": self._price_text(product, product.list_price),
            }
        on_sale = product._ocd_vendor_can_change()
        return request.render("ocd_live_shop.vendor_product_edit", common.page_values(
            "mes_produits",
            space_page="products",
            back="/ocd/espace/moi/produits",
            back_label=env._("Back to my products"),
            header_title=env._("My products"),
            vendor=vendor,
            sent=False,
            on_sale=on_sale,
            change_refusal=product._ocd_change_refusal_text() if on_sale else False,
            price_question=price_question,
            can_retire=product._ocd_vendor_can_retire(),
            photos=self._photos(product) if on_sale else [],
            photos_max=product._ocd_photos_max(),
            photos_error=request.params.get("photo_erreur"),
            stock_url=f"/ocd/espace/moi/produits/{product.id}/mon-stock" if on_sale and (
                vendor._ocd_stock_per_place() or len(product.product_variant_ids) > 1) else False,
            # Its sizes and colours, and the ones the vendor may add (chantier 21)
            variant_lines=[{
                "name": line.attribute_id.name,
                "values": line.value_ids.sorted(lambda value: (value.sequence, value.id)).mapped("name"),
            } for line in product.sudo().attribute_line_ids] if on_sale else [],
            addable=[{
                "name": attribute.name,
                "colour": attribute.display_type == "color",
                "values": values_to_add,
            } for attribute, values_to_add in product._ocd_vendor_addable_values().items()] if on_sale else [],
            added=request.params.get("ajoute"),
            variants_error=request.params.get("tailles_erreur"),
            **self._form_values(values, errors, kept, product=product),
        ))

    @http.route("/ocd/espace/moi/produits/<int:product_id>/tailles", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_add_values(self, product_id, **post):
        """Add sizes or colours to a product on sale (chantier 21): new choices without stock."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        if not product._ocd_vendor_can_change():
            raise request.not_found()
        ticked = [int(value) for value in request.httprequest.form.getlist("valeurs") if str(value).isdigit()]
        base = f"/ocd/espace/moi/produits/{product.id}/modifier"
        try:
            added = product._ocd_vendor_add_values(request.env["product.attribute.value"].sudo().browse(ticked).exists())
        except UserError as exc:
            return request.redirect(f"{base}?{urlencode({'tailles_erreur': exc.args[0]})}#tailles")
        return request.redirect(f"{base}?{urlencode({'ajoute': ', '.join(added.mapped('name'))})}#tailles")

    def _photos(self, product):
        """The photos of a product on sale for its page of change (design GererProduits): the
        main one first, the new ones checked by the team."""
        photos = product._ocd_vendor_photos()
        checked = [photo for photo in photos if photo["state"] == "approved"]
        rows = []
        for photo in photos:
            image = photo["image"]
            rows.append({
                **photo,
                "src": vendor_photo_url(product, "image_512") if photo["main"] or not image
                else f"/ocd/espace/moi/produits/{product.id}/photos/{image.id}?unique={product._ocd_photo_stamp(image)}",
                # A product keeps one checked photo: the main one is replaced by the next one
                "can_remove": photo["state"] != "approved" or len(checked) > 1,
                "can_move": not photo["main"] and photo["state"] == "approved",
            })
        return rows

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

    @http.route("/ocd/espace/moi/produits/<int:product_id>/photo/<string:size>", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def product_photo(self, product_id, size, **kwargs):
        """The photo of a product of the vendor, also while it waits for the check or is refused:
        its public address gives the default image until the product is put online, so the
        vendor would not see the photo the team refused."""
        vendor = self._vendor()
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not vendor or not product or product.ocd_vendor_id != vendor or size not in PHOTO_SIZES:
            raise request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(product, size)
        # Private to the vendor; the address changes with the photo (?unique=)
        response = stream.get_response(immutable=bool(kwargs.get("unique")))
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "").replace("public", "private")
        return response

    @http.route("/ocd/espace/<string:token>/produits", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def products_link(self, token, **kwargs):
        """The button of a WhatsApp message to the vendor: their personal link opens their
        space on the phone, then « My products ». (« moi » takes the route below.)"""
        vendor = common.current_vendor(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        return request.redirect("/ocd/espace/moi/produits")

    @http.route("/ocd/espace/moi/produits", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def products(self, envoye=None, etat=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render(vendor, sent=bool(envoye), state=etat)

    # === PHOTO KEPT AFTER AN ERROR (see the functions above) === #

    def _read_photo(self, photo):
        return read_photo(photo)

    def _pending_photos(self, vendor):
        return pending_photos(vendor)

    def _keep_photo(self, vendor, data, filename):
        return keep_photo(vendor, data, filename)

    def _kept_photo(self, vendor, kept):
        return kept_photo(vendor, kept)

    @staticmethod
    def _kept_values(attachment):
        return kept_values(attachment)

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
        chosen, quantities, ticked, stock, variant_error = self._read_variants(post)
        if variant_error:
            errors["variants"] = variant_error
        values = {"name": name, "price": price, "quantity": qty, "variantes": bool(post.get("variantes")),
                  "valeurs": ticked, "stock": {key: str(value) for key, value in stock.items()}}
        if errors:
            if data is not None and not kept:
                kept = self._keep_photo(vendor, data, filename)
            return self._render(vendor, values=values, errors=errors, kept=kept, form_token=token)
        # A new product goes first in the boutique (and in « My products »)
        first = Product._ocd_first_sequence(vendor)
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
                    **({"website_sequence": first} if first is not None else {}),
                })
                if chosen:
                    product._ocd_vendor_set_variants(chosen, quantities)
                else:
                    product._ocd_set_stock(qty)
        except (UserError, ValidationError) as exc:
            # Not an image Odoo can read: no photo to keep
            return self._render(vendor, values=values, errors={"photo": exc.args[0]}, form_token=token)
        self._pending_photos(vendor).unlink()
        if any(attribute.display_type == "color" for attribute in chosen):
            # Its colours: their photos come next (the row opens on them)
            return request.redirect(f"{sent}&couleurs={product.id}#produit-{product.id}")
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
        if product._ocd_vendor_can_change():
            return self._change_on_sale(vendor, product, name, price, post)
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
        # A big change of the price is confirmed first (2.1 of the plan)
        question = None
        if not errors and product._ocd_price_needs_confirm(amount) \
                and post.get("prix_confirme") != self._price_text(product, amount):
            question = self._price_question(product, amount)
        if errors or question:
            if data is not None and not kept:
                kept = self._keep_photo(vendor, data, filename)
            return self._render_correct(vendor, product, values, errors, kept, price_question=question)
        changes = {"name": name, "list_price": amount}
        if data is not None:
            changes["image_1920"] = BinaryBytes(data, filename=filename)
        resent = product.ocd_review_state == "refused"
        try:
            with env.cr.savepoint():
                product.with_context(
                    ocd_price_source="vendor", ocd_price_confirmed=bool(post.get("prix_confirme"))
                )._ocd_vendor_correct(changes)
        except (UserError, ValidationError) as exc:
            return self._render_correct(vendor, product, values, {"photo": exc.args[0]})
        self._pending_photos(vendor).unlink()
        return request.redirect(f"/ocd/espace/moi/produits?envoye=1#produit-{product.id}" if resent else back)

    # === THE PHOTOS OF A PRODUCT ON SALE (2.6 of the plan) === #

    def _photos_back(self, product, error=None):
        """Back to the photos of the product; `error`: « taille » (photo too big or not an
        image), « nombre » (too many photos), « garder » (the last photo)."""
        url = f"/ocd/espace/moi/produits/{product.id}/modifier"
        return request.redirect(f"{url}?photo_erreur={error}#photos" if error else f"{url}#photos")

    @http.route("/ocd/espace/moi/produits/<int:product_id>/photos", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_photo_add(self, product_id, photo=None, **post):
        """Add a photo: checked by the team before it shows; the product stays on sale."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        data, filename, error = self._read_photo(photo)
        if data is None:
            return self._photos_back(product, "taille" if error else None)
        try:
            with request.env.cr.savepoint():
                product._ocd_vendor_add_photo(data, filename)
        except ValidationError:
            return self._photos_back(product, "taille")
        except UserError:
            return self._photos_back(product, "nombre")
        return self._photos_back(product)

    @http.route("/ocd/espace/moi/produits/<int:product_id>/photos/<string:key>/<string:what>", type="http",
                auth="public", website=True, methods=["POST"], sitemap=False)
    def product_photo_change(self, product_id, key, what, **post):
        """Remove a photo (« retirer »), or move it one place earlier (« avant »)."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        try:
            with request.env.cr.savepoint():
                if what == "retirer":
                    product._ocd_vendor_remove_photo(key)
                elif what == "avant":
                    product._ocd_vendor_move_photo(key)
                else:
                    raise request.not_found()
        except UserError:
            return self._photos_back(product, "garder")
        return self._photos_back(product)

    @http.route("/ocd/espace/moi/produits/<int:product_id>/photos/<int:image_id>", type="http", auth="public",
                website=True, methods=["GET"], sitemap=False)
    def product_photo_image(self, product_id, image_id, **kwargs):
        """A photo of a product of the vendor, also while the team checks it."""
        vendor = self._vendor()
        product = request.env["product.template"].sudo().browse(product_id).exists()
        image = product.product_template_image_ids.filtered(lambda i: i.id == image_id) if product else False
        if not vendor or not product or product.ocd_vendor_id != vendor or not image:
            raise request.not_found()
        return self._private_image(image, "image_512", kwargs)

    @http.route("/ocd/espace/moi/produits/<int:product_id>/couleur/<int:value_id>/nouvelle", type="http",
                auth="public", website=True, methods=["GET"], sitemap=False)
    def product_colour_pending(self, product_id, value_id, **kwargs):
        """The new photo of a colour, while the team checks it."""
        vendor = self._vendor()
        product = request.env["product.template"].sudo().browse(product_id).exists()
        value = request.env["product.template.attribute.value"].sudo().browse(value_id).exists()
        if not vendor or not product or product.ocd_vendor_id != vendor or not value \
                or value.product_tmpl_id != product or not value.ocd_image_pending:
            raise request.not_found()
        return self._private_image(value, "ocd_image_pending", kwargs)

    def _private_image(self, record, field, kwargs):
        stream = request.env["ir.binary"]._get_image_stream_from(record, field, width=512, height=512)
        response = stream.get_response(immutable=bool(kwargs.get("unique")))
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "").replace("public", "private")
        return response

    def _change_on_sale(self, vendor, product, name, price, post):
        """Change a product on sale (2.1 of the plan, design GererProduits): the price at once
        (a big change confirmed first), the name checked by the team while the product stays
        on sale as it was."""
        if request.httprequest.method != "POST":
            return self._render_correct(vendor, product)
        errors, name, amount = self._check_fields(name, price)
        values = {"name": name, "price": price}
        if errors:
            return self._render_correct(vendor, product, values, errors)
        confirmed = post.get("prix_confirme") == self._price_text(product, amount)
        if product._ocd_price_needs_confirm(amount) and not confirmed:
            return self._render_correct(vendor, product, values, price_question=self._price_question(product, amount))
        price_changed = bool(product.currency_id.compare_amounts(amount, product.list_price))
        waiting = product._ocd_vendor_change(name, amount, confirmed=confirmed)
        done = ("verification" if waiting else "1") + ("&prix=1" if price_changed else "")
        return request.redirect(f"/ocd/espace/moi/produits?modifie={done}#produit-{product.id}")

    # === ORDER OF THE BOUTIQUE, COPY === #

    def _own_product(self, vendor, product_id):
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor:
            raise request.not_found()
        return product

    @http.route("/ocd/espace/moi/produits/<int:product_id>/ordre", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_move(self, product_id, ou=None, **post):
        """Put a product first, or one place up or down, in the boutique (1.6 of the plan)."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        if ou in MOVES:
            product._ocd_move_in_boutique(ou)
        return request.redirect(f"/ocd/espace/moi/produits?ouvert={product.id}#produit-{product.id}")

    @http.route("/ocd/espace/moi/produits/<int:product_id>/retirer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_retire(self, product_id, **post):
        """Take a product off sale (2.2 of the plan): never deleted, put back with one tap."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        if product._ocd_vendor_can_retire():
            product._ocd_vendor_retire()
        return request.redirect(f"/ocd/espace/moi/produits?retire=1#produit-{product.id}")

    @http.route("/ocd/espace/moi/produits/<int:product_id>/remettre", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_put_back(self, product_id, **post):
        """Put back on sale a product the vendor took off."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        if product.ocd_vendor_retired and product.ocd_review_state == "approved":
            product._ocd_vendor_put_back()
        return request.redirect(f"/ocd/espace/moi/produits?remis=1#produit-{product.id}")

    @http.route("/ocd/espace/moi/produits/<int:product_id>/dupliquer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def product_duplicate(self, product_id, **post):
        """A copy of a product (the same model in another fabric), then its form to change the
        name or the photo; the team checks it like a new product (1.5 of the plan)."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        copy = self._own_product(vendor, product_id)._ocd_vendor_duplicate()
        return request.redirect(f"/ocd/espace/moi/produits/{copy.id}/modifier")

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
                # A product on sale: the new photo is checked by the team (chantier 19)
                product._ocd_vendor_colour_photo(value, data, photo.filename)
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
