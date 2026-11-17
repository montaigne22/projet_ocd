from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live.controllers import common

from . import shop_common
from .vendor_products import vendor_photo_url


class OcdLivePrepare(http.Controller):
    """Prepare the next live (chantier 21, 3.2 of the plan of « My products », design
    PreparerLive): the vendor ticks the products to show and puts them in order, with a word for
    the host. Without JavaScript the page works the same: ↑ and ↓ send the form."""

    def _vendor(self):
        return common.current_vendor()

    def _next_live(self, vendor):
        return request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id), ("state", "in", ("draft", "confirmed")),
            ("end_datetime", ">", fields.Datetime.now()),
        ], order="start_datetime", limit=1)

    def _booking(self, vendor, booking_id):
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        if not booking or booking.partner_id != vendor:
            raise request.not_found()
        return booking

    @http.route("/ocd/espace/moi/live", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def next_live(self, **kwargs):
        """The next live of the vendor to prepare, else « No live booked »."""
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        booking = self._next_live(vendor)
        if booking:
            return request.redirect(f"/ocd/espace/moi/live/{booking.id}")
        return self._render(vendor, request.env["ocd.live.booking"])

    def _when(self, booking):
        local = common.to_viewer(booking.start_datetime)
        return "%s %s" % (common.short_day(local.date()), f"{local:%H:%M}")

    def _rows(self, booking, chosen):
        """The products the vendor may show, with their stock."""
        products = booking._ocd_preparable_products()
        variants = products.product_variant_ids
        free = variants._ocd_free_qties()
        rows = []
        for product in products:
            tracked = shop_common.tracked(product)
            qty = sum(free[variant.id] for variant in product.product_variant_ids) if tracked else None
            parts = [common.money(product.list_price, product.currency_id)]
            if qty:
                parts.append(request.env._("%s in stock", qty))
            rows.append({
                "product": product,
                "line": " · ".join(parts),
                "out": qty == 0,
                "image": vendor_photo_url(product, "image_128"),
                "chosen": product in chosen,
            })
        return rows

    def _render(self, vendor, booking, chosen=None, note=None, error=None):
        env = request.env
        if not booking:
            return request.render("ocd_live_shop.vendor_live_prepare", common.page_values(
                False, space_page="space", back="/ocd/espace/moi", back_label=env._("Back to my space"),
                header_title=env._("My next live"), vendor=vendor, booking=booking,
            ))
        chosen = booking._ocd_prepared_products() if chosen is None else chosen
        rows = self._rows(booking, chosen)
        by_product = {row["product"]: row for row in rows}
        return request.render("ocd_live_shop.vendor_live_prepare", common.page_values(
            False,
            space_page="space",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My next live"),
            vendor=vendor,
            booking=booking,
            title=env._("My live of %s", self._when(booking)),
            rows=rows,
            chosen=[by_product[product] for product in chosen if product in by_product],
            order=",".join(str(product.id) for product in chosen),
            note=booking.ocd_host_note or "" if note is None else note,
            can_prepare=booking._ocd_can_prepare(),
            error=error,
        ))

    @http.route("/ocd/espace/moi/live/<int:booking_id>", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def prepare_page(self, booking_id, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render(vendor, self._booking(vendor, booking_id))

    def _chosen(self, booking, post):
        """The products ticked, in the order kept by the page: the ones already in the order
        first, then the ones just ticked, in the order of the list; ↑ or ↓ moves one."""
        Product = request.env["product.template"].sudo()
        allowed = booking._ocd_preparable_products()
        ticked = {int(value) for value in request.httprequest.form.getlist("coches") if str(value).isdigit()}
        order = [int(value) for value in (post.get("ordre") or "").split(",") if value.strip().isdigit()]
        ids = [pid for pid in dict.fromkeys(order) if pid in ticked]
        ids += [product.id for product in allowed if product.id in ticked and product.id not in ids]
        for key, step in (("monter", -1), ("descendre", 1)):
            moved = int(post[key]) if str(post.get(key) or "").isdigit() else 0
            if moved in ids:
                index = ids.index(moved)
                other = index + step
                if 0 <= other < len(ids):
                    ids[index], ids[other] = ids[other], ids[index]
        return Product.browse(ids)

    @http.route("/ocd/espace/moi/live/<int:booking_id>", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def prepare_save(self, booking_id, note=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        booking = self._booking(vendor, booking_id)
        chosen = self._chosen(booking, post)
        try:
            booking._ocd_prepare(chosen, common.clean_text(note, 200))
        except UserError as exc:
            return self._render(vendor, booking, chosen=chosen, note=note, error=exc.args[0])
        if post.get("monter") or post.get("descendre"):
            # A move without JavaScript: the same page, at the list of the live
            return request.redirect(f"/ocd/espace/moi/live/{booking.id}#dans-mon-live")
        return request.redirect(f"/ocd/espace/moi?pret={booking.id}")
