"""« Mon stock » (design MonStock, chantier 18): the stock of a product in each place of the vendor,
with its sizes and its colours (2.5 and S.2 of the plan).

One page for every screen: a column per place. The phone shows the place chosen (?magasin=),
the computer all of them side by side. Each − / + is a small form (the page works without
JavaScript) whose change is added to the stock of the moment, as in « My products »."""
from collections import defaultdict

from markupsafe import escape

from odoo import fields, http
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from ..models.product_product import MAX_STOCK
from . import shop_common
from .vendor_products import vendor_photo_url

# The last changes of the stock shown under the table
LAST_CHANGES = 6


class OcdVendorStock(http.Controller):

    def _vendor(self):
        return common.current_vendor()

    def _own_product(self, vendor, product_id):
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor:
            raise request.not_found()
        return product

    def _columns(self, vendor):
        """[{"place", "location", "name"}]: a column per place of the vendor; one column « Stock »
        without a place (the stock of the shop)."""
        places = vendor._ocd_stock_places()
        if places:
            return [{"place": place, "location": place._ocd_location(), "name": place.name} for place in places]
        root = request.env["product.product"]._ocd_stock_root()
        return [{"place": request.env["ocd.vendor.place"], "location": root, "name": request.env._("Stock")}]

    def _counts(self, variants, location):
        """({variant id: free}, {variant id: kept for an order}) at `location`."""
        free, kept = defaultdict(int), defaultdict(int)
        groups = request.env["stock.quant"].sudo()._read_group(
            [("product_id", "in", variants.ids), ("location_id", "child_of", location.id)],
            ["product_id"], ["quantity:sum", "reserved_quantity:sum"],
        )
        for product, quantity, reserved in groups:
            free[product.id] = max(int(quantity - reserved), 0)
            kept[product.id] = int(reserved)
        return free, kept

    @staticmethod
    def _values_of(variant):
        """(colour value, the other values) of a variant, in the order of the attributes."""
        values = variant.product_template_attribute_value_ids.sorted(
            lambda v: (v.attribute_id.sequence, v.product_attribute_value_id.sequence, v.id)
        )
        colour = values.filtered(lambda v: v.attribute_id.display_type == "color")[:1]
        return colour, values - colour

    def _groups(self, product, columns):
        """The variants by colour: [{"colour", "swatch", "count_line", "rows": [{"variant",
        "label", "cells": [{"free", "kept", "elsewhere"}]}]}]."""
        env = request.env
        variants = product.product_variant_ids
        counts = [self._counts(variants, column["location"]) for column in columns]
        groups, by_colour = [], {}
        for variant in variants.sorted(lambda v: [
            (value.attribute_id.sequence, value.product_attribute_value_id.sequence)
            for value in v.product_template_attribute_value_ids
        ]):
            colour, others = self._values_of(variant)
            key = colour.id or 0
            if key not in by_colour:
                by_colour[key] = {
                    "colour": colour.name if colour else "",
                    "swatch": colour.html_color if colour else False,
                    "rows": [],
                }
                groups.append(by_colour[key])
            cells = []
            for index, (free, kept) in enumerate(counts):
                elsewhere = [
                    (columns[other]["name"], counts[other][0][variant.id])
                    for other in range(len(columns)) if other != index and counts[other][0][variant.id]
                ]
                cells.append({
                    "free": free[variant.id],
                    "kept": kept[variant.id],
                    "elsewhere": ", ".join(env._("%(count)s at %(place)s", count=count, place=name) for name, count in elsewhere),
                })
            by_colour[key]["rows"].append({
                "variant": variant,
                "label": " · ".join(others.mapped("name")) or (colour.name if colour else env._("Stock")),
                "cells": cells,
                "total": sum(cell["free"] for cell in cells),
            })
        for group in groups:
            group["totals"] = [sum(row["cells"][index]["free"] for row in group["rows"]) for index in range(len(columns))]
        return groups

    def _last_changes(self, product, columns):
        """The last changes of the stock of the product in the places of the vendor: added or
        removed by the vendor, sent from a place to another, sold."""
        env = request.env
        locations = request.env["stock.location"].browse([column["location"].id for column in columns])
        names = {column["location"].id: column["name"] for column in columns}
        lines = env["stock.move.line"].sudo().search([
            ("product_id", "in", product.product_variant_ids.ids), ("state", "=", "done"),
            "|", ("location_id", "in", locations.ids), ("location_dest_id", "in", locations.ids),
        ], order="date desc, id desc", limit=LAST_CHANGES)
        today = fields.Date.context_today(env["res.partner"])
        rows = []
        for line in lines:
            colour, others = self._values_of(line.product_id)
            label = " ".join(part for part in (colour.name if colour else "", " · ".join(others.mapped("name"))) if part) or product.name
            qty = int(line.quantity)
            source, destination = names.get(line.location_id.id), names.get(line.location_dest_id.id)
            one = qty == 1
            if source and destination:
                text = (env._("1 %(label)s sent: %(start)s → %(end)s", label=label, start=source, end=destination) if one
                        else env._("%(qty)s %(label)s sent: %(start)s → %(end)s",
                                   qty=qty, label=label, start=source, end=destination))
            elif destination and line.location_id.usage == "inventory":
                text = env._("%(label)s: +%(qty)s at %(place)s", label=label, qty=qty, place=destination)
            elif source and line.location_dest_id.usage == "inventory":
                text = env._("%(label)s: -%(qty)s at %(place)s", label=label, qty=qty, place=source)
            elif source and line.location_dest_id.usage == "customer":
                order = line.move_id.sale_line_id.order_id.name or line.picking_id.origin or line.reference
                text = (env._("1 %(label)s sold (%(order)s)", label=label, order=order) if one
                        else env._("%(qty)s %(label)s sold (%(order)s)", qty=qty, label=label, order=order))
            elif destination:
                text = (env._("1 %(label)s received at %(place)s", label=label, place=destination) if one
                        else env._("%(qty)s %(label)s received at %(place)s", qty=qty, label=label, place=destination))
            else:
                text = (env._("1 %(label)s left %(place)s", label=label, place=source) if one
                        else env._("%(qty)s %(label)s left %(place)s", qty=qty, label=label, place=source))
            if line.move_id.ocd_member_id:
                # Changed by a person of the team at her store (chantier 22)
                text = env._("%(change)s, by %(person)s", change=text, person=line.move_id.ocd_member_id.name)
            when = common.to_viewer(line.date)
            day = env._("Today %s", tools.hour_text(when.hour + when.minute / 60)) if when.date() == today \
                else tools.day_text(env, when.date(), "d MMM")
            rows.append({"when": day, "text": text})
        return rows

    @http.route("/ocd/espace/moi/produits/<int:product_id>/mon-stock", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def stock(self, product_id, magasin=None, envoye=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        product = self._own_product(vendor, product_id)
        columns = self._columns(vendor)
        chosen = next((index for index, column in enumerate(columns)
                       if column["place"] and str(column["place"].id) == str(magasin)), None)
        if chosen is None:
            main = vendor._ocd_main_stock_place()
            chosen = next((index for index, column in enumerate(columns) if column["place"] == main), 0)
        groups = self._groups(product, columns)
        totals = [sum(group["totals"][index] for group in groups) for index in range(len(columns))]
        colours = len([group for group in groups if group["colour"]])
        sizes = len({row["label"] for group in groups for row in group["rows"]})
        return request.render("ocd_live_shop.vendor_stock", common.page_values(
            False,
            space_page="products",
            back="/ocd/espace/moi/produits",
            back_label=env._("Back to my products"),
            header_title=env._("My products"),
            vendor=vendor,
            product=product,
            image=vendor_photo_url(product, "image_128"),
            price=common.money(product.list_price, product.currency_id),
            facts=" · ".join(part for part in (
                env._("%s colours", colours) if colours > 1 else "",
                env._("%s sizes", sizes) if sizes > 1 and colours else "",
                env._("1 piece") if sum(totals) == 1 else env._("%s pieces", sum(totals)),
            ) if part),
            columns=columns,
            chosen=chosen,
            totals=totals,
            groups=groups,
            several=len(columns) > 1,
            total_line=env._("%(count)s pieces in your %(places)s stores. The − and + count at once.",
                             count=sum(totals), places=len(columns)) if len(columns) > 1 else env._("The − and + count at once."),
            changes=self._last_changes(product, columns),
            send_url=f"/ocd/espace/moi/produits/{product.id}/envoyer" if len(columns) > 1 else False,
            sent_line=(env._("1 piece sent: the stock changed in both stores.") if str(envoye) == "1"
                       else env._("%s pieces sent: the stock changed in both stores.", envoye))
            if str(envoye or "").isdigit() and int(envoye) > 0 else False,
        ))

    @http.route("/ocd/espace/moi/produits/<int:product_id>/mon-stock", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def stock_change(self, product_id, variante=None, lieu=None, delta=None, **post):
        """A − or a + of a size and a colour in a place: added to the stock of the moment."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        variant = product.product_variant_ids.filtered(lambda v: str(v.id) == str(variante))[:1]
        try:
            delta = max(min(int(delta), MAX_STOCK), -MAX_STOCK)
        except (TypeError, ValueError):
            delta = 0
        place = vendor._ocd_stock_places().filtered(lambda p: str(p.id) == str(lieu))[:1]
        back = f"/ocd/espace/moi/produits/{product.id}/mon-stock" + (f"?magasin={place.id}" if place else "")
        if not variant or not delta:
            return request.redirect(back)
        if not shop_common.tracked(product):
            product.write({"is_storable": True, "allow_out_of_stock_order": False})
        location = place._ocd_location() if place else variant._ocd_stock_location()
        variant._ocd_change_stock(delta, location)
        return request.redirect(f"{back}#v-{variant.id}")

    # === SEND PIECES FROM A PLACE TO ANOTHER (design EnvoyerStock) === #

    def _send_values(self, vendor, product, source_id, destination_id, error=None, kept=None):
        env = request.env
        places = vendor._ocd_stock_places()
        source = places.filtered(lambda p: str(p.id) == str(source_id))[:1] or vendor._ocd_main_stock_place()
        destination = places.filtered(lambda p: str(p.id) == str(destination_id) and p != source)[:1] or (places - source)[:1]
        free = product.product_variant_ids._ocd_free_qties(source._ocd_location())
        rows = []
        for variant in product.product_variant_ids:
            if not free[variant.id]:
                continue
            colour, others = self._values_of(variant)
            rows.append({
                "variant": variant,
                "label": " · ".join(part for part in (colour.name if colour else "", " · ".join(others.mapped("name"))) if part)
                or product.name,
                "swatch": colour.html_color if colour else False,
                "free": free[variant.id],
                "value": min(int((kept or {}).get(variant.id, 0)), free[variant.id]),
            })
        return {
            "space_page": "products",
            "back": f"/ocd/espace/moi/produits/{product.id}/mon-stock?magasin={source.id}",
            "back_label": env._("Back to my stock"),
            "header_title": product.name,
            "vendor": vendor,
            "product": product,
            "places": places,
            "source": source,
            "destination": destination,
            "rows": rows,
            "error": error,
            "note": (kept or {}).get("note", ""),
            "label_none": env._("Choose the pieces to send"),
            "label_one": env._("Send 1 piece to %s", destination.name),
            "label_many": env._("Send __COUNT__ pieces to %s", destination.name),
        }

    @http.route("/ocd/espace/moi/produits/<int:product_id>/envoyer", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def send(self, product_id, de=None, a=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = self._own_product(vendor, product_id)
        if not vendor._ocd_stock_per_place():
            return request.redirect(f"/ocd/espace/moi/produits/{product.id}/mon-stock")
        return request.render("ocd_live_shop.vendor_stock_send",
                              common.page_values(False, **self._send_values(vendor, product, de, a)))

    @http.route("/ocd/espace/moi/produits/<int:product_id>/envoyer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def send_post(self, product_id, de=None, a=None, note=None, **post):
        """Send pieces from a place to another: an internal transfer of the stock, done at once
        (the stock changes in both places), traced with its note. Only the free pieces leave."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        product = self._own_product(vendor, product_id)
        places = vendor._ocd_stock_places()
        source = places.filtered(lambda p: str(p.id) == str(de))[:1]
        destination = places.filtered(lambda p: str(p.id) == str(a))[:1]
        wanted = {}
        for variant in product.product_variant_ids:
            text = str(post.get(f"qty_{variant.id}") or "").strip()
            if text.isdigit() and int(text) > 0:
                wanted[variant] = min(int(text), MAX_STOCK)
        note = common.clean_text(note, 200)
        kept = {variant.id: qty for variant, qty in wanted.items()} | {"note": note}
        if not source or not destination or source == destination:
            values = self._send_values(vendor, product, de, a, env._("Choose two different stores."), kept)
            return request.render("ocd_live_shop.vendor_stock_send", common.page_values(False, **values))
        free = product.product_variant_ids._ocd_free_qties(source._ocd_location())
        quantities = {variant: min(qty, free[variant.id]) for variant, qty in wanted.items() if free[variant.id]}
        if not any(quantities.values()):
            values = self._send_values(vendor, product, de, a, env._("Choose how many pieces to send."), kept)
            return request.render("ocd_live_shop.vendor_stock_send", common.page_values(False, **values))
        env["stock.picking"]._ocd_transfer(
            quantities, source._ocd_location(), destination._ocd_location(),
            note=escape(note) if note else False,
            origin=env._("Sent by %(vendor)s from %(start)s", vendor=vendor.name, start=source.name),
        )
        return request.redirect(f"/ocd/espace/moi/produits/{product.id}/mon-stock?magasin={destination.id}&envoye={sum(quantities.values())}")
