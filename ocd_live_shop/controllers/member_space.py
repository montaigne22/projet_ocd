"""The space of a person of the team of a vendor (chantier 22, design EquipeDuVendeur): « My
store », with the stock of her store (without the prices) and the parcels of her store in the
app of the parcels (without the payouts).

She logs in like the vendors, with her WhatsApp number: her personal link in the link mode, a
code otherwise. Her phone remembers her (session of Odoo and a cookie of its own), until « Log
out », a new personal link, or her removal from the team."""
from collections import defaultdict

from odoo import http
from odoo.http import request

from odoo.addons.ocd_live.controllers import common

from ..models.product_product import MAX_STOCK
from . import shop_common
from .delivery_app import OPEN_STAGES
from .delivery_login import OcdDeliveryLogin, current_courier, forget_courier
from .member_session import (
    HOME, LOGIN, current_member, forget_member, member_header_link, member_login_mode, remember_member,
)

# The lines shown on the home page of a tablet and a computer, beside the counts
PREVIEW = 3
# Image sizes of a product in her stock
PHOTO_SIZES = ("image_128", "image_256")
# Where her personal link leads (?vers=, the buttons of her WhatsApp messages)
LINK_PAGES = {"colis": "/ocd/livrer/moi", "essayer": "/ocd/livrer/moi?vue=essayer", "stock": "/ocd/mon-magasin/stock"}


def stock_counts(variants, location):
    """({variant id: free}, {variant id: kept for an order}) at `location`, in one query."""
    free, kept = defaultdict(int), defaultdict(int)
    groups = request.env["stock.quant"].sudo()._read_group(
        [("product_id", "in", variants.ids), ("location_id", "child_of", location.id)],
        ["product_id"], ["quantity:sum", "reserved_quantity:sum"],
    )
    for product, quantity, reserved in groups:
        free[product.id] = max(int(quantity - reserved), 0)
        kept[product.id] = int(reserved)
    return free, kept


class OcdMemberLogin(OcdDeliveryLogin):
    """Her login: the number, then her link or a code on WhatsApp, as set for the vendors. The
    pages of the vendors and of the parcels also answer her number."""

    LOGIN_PAGES = dict(
        OcdDeliveryLogin.LOGIN_PAGES,
        magasin={"form": LOGIN, "code": "/ocd/mon-magasin/code", "home": HOME},
    )

    def _login_page_mode(self, target):
        if target == "magasin":
            return member_login_mode()
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        member = request.env["ocd.vendor.member"].sudo()._ocd_find_by_phone(number)
        if target == "magasin" and member:
            return member.partner_id
        return super()._ocd_login_partner(number, target) or member.partner_id

    def _ocd_send_link(self, partner, target):
        member = request.env["ocd.vendor.member"].sudo()._ocd_of_partner(partner)
        if member:
            return member._ocd_send_link()
        return super()._ocd_send_link(partner, target)

    def _ocd_open_session(self, partner, target):
        member = request.env["ocd.vendor.member"].sudo()._ocd_of_partner(partner)
        if member:
            # One person per phone: the vendor or the courier opened before are forgotten
            common.forget_vendor()
            forget_courier()
            remember_member(member)
            return HOME
        forget_member()
        return super()._ocd_open_session(partner, target)

    @http.route()
    def login(self, **kwargs):
        # « Me » of the menu leads her to her store
        if not common.current_vendor() and current_member():
            return request.redirect(HOME)
        return super().login(**kwargs)

    @http.route()
    def delivery_login(self, **kwargs):
        if not (current_courier() or common.current_vendor()) and current_member():
            return request.redirect("/ocd/livrer/moi")
        return super().delivery_login(**kwargs)

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def member_login(self, **kwargs):
        if current_member():
            return request.redirect(HOME)
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="magasin")

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def member_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "magasin")

    @http.route("/ocd/mon-magasin/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def member_login_code(self, code=None, **kwargs):
        return self._login_code(code, "magasin")

    @http.route("/ocd/mon-magasin/deconnexion", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def member_logout_page(self, **kwargs):
        """A link loaded in advance by the browser logs nobody out (« Log out » is a form)."""
        return request.redirect(HOME)

    @http.route("/ocd/mon-magasin/deconnexion", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def member_logout(self, **kwargs):
        forget_member()
        return request.redirect(LOGIN)


class OcdMemberSpace(http.Controller):
    """« My store »: her home, the stock of her store."""

    def _member(self):
        """Her place in the team, or the answer to give (login, paused team)."""
        member = current_member()
        if not member:
            return None, request.redirect(LOGIN)
        request._ocd_viewer_tz = common.viewer_tz(member.partner_id)
        member._ocd_visit()
        if member._ocd_paused():
            return member, self._render_paused(member)
        return member, None

    def _page(self, member, **values):
        return common.page_values(
            False,
            nav="me",
            header_link=member_header_link(),
            member=member,
            vendor=member.vendor_id,
            place=member.place_id,
            **values,
        )

    def _render_paused(self, member):
        env = request.env
        vendor = member.vendor_id
        return request.render("ocd_live_shop.member_paused", self._page(
            member,
            header_name=env._("My store"),
            hello=env._("Hello %s", member._ocd_first_name()),
            paused_line=env._("The team of %s is paused.", vendor.name) if member.place_id.active
            else env._("This store of %s is closed for now.", vendor.name),
            ask_line=env._("Ask %s to start it again: nothing is deleted.", vendor.name),
        ))

    # === HOME === #

    def _parcels(self, member):
        """The open parcels prepared in her store, and its pieces held to try."""
        env = request.env
        vendor, place = member.vendor_id, member.place_id
        parcels = env["stock.picking"].sudo()
        if vendor.ocd_sale_mode == "ocd":
            parcels = parcels.search([
                ("ocd_is_parcel", "=", True), ("ocd_stage", "in", OPEN_STAGES),
                ("ocd_vendor_id", "=", vendor.id), ("ocd_pickup_place_id", "=", place.id),
            ], order="create_date, id")
        holds = env["ocd.product.hold"].sudo().search(
            [("vendor_id", "=", vendor.id), ("place_id", "=", place.id), ("state", "in", ("requested", "accepted"))],
            order="deadline, id",
        )
        return parcels, holds

    def _low_rows(self, member):
        """The colours and sizes of her store with few pieces left (the threshold of the vendor)."""
        limit = member.vendor_id._ocd_low_stock_limit()
        if not limit:
            return []
        products = member._ocd_products().filtered(shop_common.tracked)
        variants = products.product_variant_ids
        free, _kept = stock_counts(variants, member._ocd_location())
        return [
            {"variant": variant, "free": free[variant.id]}
            for variant in variants if 0 < free[variant.id] <= limit
        ]

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def home(self, **kwargs):
        member, answer = self._member()
        if answer:
            return answer
        env = request.env
        vendor = member.vendor_id
        parcels, holds = self._parcels(member)
        to_prepare = parcels.filtered(lambda p: p.ocd_stage == "to_prepare")
        pickups = parcels.filtered(lambda p: p.ocd_collect and p.ocd_stage == "ready")
        counts = [
            env._("1 to prepare") if len(to_prepare) == 1 else env._("%s to prepare", len(to_prepare)) if to_prepare else "",
            env._("1 pickup") if len(pickups) == 1 else env._("%s pickups", len(pickups)) if pickups else "",
            env._("1 to try") if len(holds) == 1 else env._("%s to try", len(holds)) if holds else "",
        ]
        products = member._ocd_products()
        low = self._low_rows(member)
        preview = []
        for parcel in to_prepare[:PREVIEW]:
            customer = (parcel.partner_id.name or "").split()[0] if parcel.partner_id.name else ""
            preview.append({
                "title": env._("%s comes to pick it up", customer) if parcel.ocd_collect else env._("For %s", customer),
                "line": ", ".join(parcel.move_ids.product_id.mapped("name")),
                "pill": env._("To prepare"),
            })
        for hold in holds.filtered(lambda h: h.state == "requested")[:max(PREVIEW - len(preview), 0)]:
            customer = (hold.partner_id.name or "").split()[0]
            preview.append({
                "title": env._("%s wants to try it", customer),
                "line": hold.product_id.display_name,
                "pill": env._("New"),
            })
        return request.render("ocd_live_shop.member_home", self._page(
            member,
            header_name=env._("My store"),
            hello=env._("Hello %s", member._ocd_first_name()),
            intro=env._("You hold the store of %s: its stock and its parcels.", vendor.name),
            sells=vendor.ocd_sale_mode == "ocd" or bool(holds),
            parcels_line=" · ".join(part for part in counts if part) or env._("Nothing to do for now"),
            stock_line=" · ".join(part for part in (
                env._("1 product") if len(products) == 1 else env._("%s products", len(products)),
                (env._("1 low on stock") if len(low) == 1 else env._("%s low on stock", len(low))) if low else "",
            ) if part),
            preview=preview,
            low_preview=[{
                "label": row["variant"].display_name,
                "left": env._("1 left") if row["free"] == 1 else env._("%s left", row["free"]),
            } for row in low[:PREVIEW + 1]],
            rest_line=env._("The prices, the new products and the payouts stay with %s.", vendor.name),
            told=member.partner_id._ocd_whatsapp_consent(),
        ))

    @http.route("/ocd/mon-magasin/<string:token>", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def link(self, token, vers=None, **kwargs):
        """Her personal link (her WhatsApp): it opens her space on this phone in the link mode,
        on the page of the message (?vers=); otherwise her number does."""
        if common.company().ocd_vendor_login != "link":
            if current_member():
                return request.redirect(LINK_PAGES.get(vers, HOME))
            return request.redirect(LOGIN)
        partner = request.env["res.partner"].sudo()._ocd_find_by_space_token(token)
        member = request.env["ocd.vendor.member"].sudo()._ocd_of_partner(partner) if partner else None
        if not member:
            raise request.not_found()
        common.forget_vendor()
        forget_courier()
        remember_member(member)
        return request.redirect(LINK_PAGES.get(vers, HOME))

    @http.route("/ocd/mon-magasin/whatsapp", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def whatsapp(self, oui=None, **post):
        """She agrees (or no longer) to receive the news of her store on WhatsApp: her consent,
        the same as everywhere on OCD Live (STOP on WhatsApp stops them too)."""
        member, answer = self._member()
        if answer:
            return answer
        member.partner_id.sudo().ocd_whatsapp_optin = oui == "1"
        return request.redirect(HOME)

    # === THE STOCK OF HER STORE === #

    def _stock_rows(self, member):
        env = request.env
        products = member._ocd_products()
        location = member._ocd_location()
        free, kept = stock_counts(products.product_variant_ids, location)
        limit = member.vendor_id._ocd_low_stock_limit()
        rows = []
        for product in products:
            tracked = shop_common.tracked(product)
            variants = []
            for variant in product.product_variant_ids.sorted(lambda v: [
                (value.attribute_id.sequence, value.product_attribute_value_id.sequence)
                for value in v.product_template_attribute_value_ids
            ]):
                pieces = free[variant.id]
                variants.append({
                    "variant": variant,
                    "label": ", ".join(variant.product_template_attribute_value_ids.mapped("name")),
                    "free": pieces,
                    "kept": kept[variant.id],
                    "low": tracked and limit and 0 < pieces <= limit,
                })
            rows.append({
                "product": product,
                "photo": f"/ocd/mon-magasin/photo/{product.id}?unique={product._ocd_photo_stamp(product)}"
                if product.image_128 else False,
                "tracked": tracked,
                "variants": variants,
                "pieces": sum(row["free"] for row in variants),
                "low": [row for row in variants if row["low"]],
            })
        return rows

    @http.route("/ocd/mon-magasin/stock", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def stock(self, **kwargs):
        member, answer = self._member()
        if answer:
            return answer
        env = request.env
        rows = self._stock_rows(member)
        return request.render("ocd_live_shop.member_stock", self._page(
            member,
            back=HOME,
            back_label=env._("Back to my store"),
            header_name=env._("My store"),
            title=env._("The stock · %s", member.place_id.name),
            rows=rows,
            low_label=env._("Low stock"),
        ))

    @http.route("/ocd/mon-magasin/stock", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def stock_change(self, variante=None, delta=None, **post):
        """A − or a + in her store: added to the stock of the moment, the vendor sees who did it."""
        member, answer = self._member()
        if answer:
            return answer
        variant = request.env["product.product"].sudo().browse(int(variante or 0)).exists()
        if not variant or variant.product_tmpl_id not in member._ocd_products():
            raise request.not_found()
        try:
            delta = max(min(int(delta), MAX_STOCK), -MAX_STOCK)
        except (TypeError, ValueError):
            delta = 0
        # A product whose stock is not counted stays so: the vendor decides it
        if delta and shop_common.tracked(variant.product_tmpl_id):
            variant.with_context(ocd_member_id=member.id)._ocd_change_stock(delta, member._ocd_location())
        return request.redirect(f"/ocd/mon-magasin/stock#v-{variant.id}")

    @http.route("/ocd/mon-magasin/photo/<int:product_id>", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def photo(self, product_id, size="image_128", **kwargs):
        """The photo of a product of the vendor, online or not: for the people of the team only."""
        member = current_member()
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not member or not product or product.ocd_vendor_id != member.vendor_id or size not in PHOTO_SIZES:
            raise request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(product, size)
        response = stream.get_response(immutable=bool(kwargs.get("unique")))
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "").replace("public", "private")
        return response
