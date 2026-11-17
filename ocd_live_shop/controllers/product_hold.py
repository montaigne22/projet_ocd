from urllib.parse import urlencode

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live.controllers import common

from . import shop_common


class OcdProductHold(http.Controller):
    """Hold a piece to try it in a store (chantier 20, A.7 of the plan of « My products », design
    MettreDeCote): the request from the page of a product, then the page of the hold (where and
    until when, « I no longer come »), opened from the WhatsApp messages without logging in."""

    def _known_partner(self):
        """The contact known on this browser (vendor, customer logged in with a number)."""
        vendor = common.current_vendor()
        if vendor:
            return vendor
        user = request.env.user
        return user.partner_id if not user._is_public() and user.partner_id.phone else False

    def _request_target(self, place_id, product_id):
        Hold = request.env["ocd.product.hold"].sudo()
        place = request.env["ocd.vendor.place"].sudo().browse(place_id).exists()
        product = request.env["product.product"].sudo().browse(int(product_id or 0)).exists()
        template = product.product_tmpl_id
        if (
            not place or not product or not Hold._ocd_offered(place) or template.ocd_vendor_id != place.vendor_id
            or not template.is_published or template.ocd_review_state != "approved"
        ):
            raise request.not_found()
        return place, product

    def _render_request(self, place, product, error=None, phone_value="", country=None):
        env = request.env
        Hold = env["ocd.product.hold"].sudo()
        preview = Hold.new({"place_id": place.id, "product_id": product.id, "company_id": place.company_id.id})
        preview.deadline = preview._ocd_deadline_from(common.now())
        template = product.product_tmpl_id
        known = self._known_partner()
        # The number of a customer who comes to the store: the country of the store first
        store_country = place.city_id.country_id or place.district_id.city_id.country_id or place.vendor_id.country_id
        amount, money_currency = shop_common.variant_price(product)
        return request.render("ocd_live_shop.hold_request", common.page_values(
            False,
            back=template.website_url,
            back_label=env._("Back to the product"),
            header_name=env._("Hold it to try"),
            place=place,
            product=product,
            photo=shop_common.image_url(template, "image_256"),
            variant_label=", ".join(product.product_template_attribute_value_ids.mapped("name")),
            price_text=common.money(amount, money_currency),
            store_line=" · ".join(part for part in (place._ocd_address_line(), place._ocd_open_state()["label"]) if part),
            promise=env._(
                "%(store)s keeps %(product)s for you until %(until)s. You try it there and you pay only if you take it.",
                store=place.name, product=product.display_name, until=preview._ocd_deadline_text(),
            ),
            known=known,
            phone_value=phone_value,
            dial_rows=common.dial_rows(country or (known.country_id if known else store_country) or common.default_country()),
            error=error,
        ))

    @http.route("/ocd/essayer/magasin/<int:place_id>", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def hold_request(self, place_id, produit=None, **kwargs):
        place, product = self._request_target(place_id, produit)
        return self._render_request(place, product)

    @http.route("/ocd/essayer/magasin/<int:place_id>", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def hold_submit(self, place_id, product_id=None, phone=None, country_id=None, **post):
        place, product = self._request_target(place_id, product_id)
        if post.get("website_url"):
            raise request.not_found()  # a robot filled the hidden field
        country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists() or (
            place.city_id.country_id or place.vendor_id.country_id or common.default_country())
        partner = self._known_partner()
        try:
            if not partner:
                number = common.normalize_phone(country, phone)
                if not number:
                    raise UserError(common.phone_error(country))
                partner = request.env["ocd.product.hold"].sudo()._ocd_contact(number)
            hold = request.env["ocd.product.hold"].sudo()._ocd_request(place, product, partner)
        except UserError as exc:
            return self._render_request(place, product, error=exc.args[0], phone_value=phone or "", country=country)
        return request.redirect(f"/{hold._ocd_page_path()}&fait=1")

    # === THE PAGE OF THE HOLD === #

    def _hold(self, hold_id, token):
        hold = request.env["ocd.product.hold"].sudo().browse(hold_id).exists()
        if not hold or not token or not consteq(str(token), hold.access_token or ""):
            raise request.not_found()
        return hold

    @http.route("/ocd/essayer/<int:hold_id>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def hold_page(self, hold_id, t=None, fait=None, **kwargs):
        hold = self._hold(hold_id, t)
        env = request.env
        place = hold.place_id
        until = hold._ocd_deadline_text()
        active = hold.state in ("requested", "accepted")
        status = {
            "requested": env._("Held at %(store)s until %(until)s. The store answers you on WhatsApp.",
                               store=place.name, until=until),
            "accepted": env._("%(store)s keeps it for you until %(until)s.", store=place.name, until=until),
            "taken": env._("Bought at %s. Enjoy it!", place.name),
            "not_taken": env._("Tried at %s. The piece is on sale again.", place.name),
            "no_show": env._("The piece was held at %s and is on sale again.", place.name),
            "refused": env._("%s cannot hold it for now. You can still order it online.", place.name),
            "cancelled": env._("Noted: you no longer come. The piece is on sale again."),
            "expired": env._("The time is over: the piece is on sale again."),
        }[hold.state]
        phone = "".join(char for char in place._ocd_phone() if char.isdigit())
        return request.render("ocd_live_shop.hold_page", common.page_values(
            False,
            back=hold.product_id.product_tmpl_id.website_url,
            back_label=env._("Back to the product"),
            header_name=env._("Held to try"),
            hold=hold,
            active=active,
            done=bool(fait),
            status=status,
            status_ok=hold.state in ("requested", "accepted", "taken"),
            store_line=place._ocd_address_line(),
            until_line=env._("Until %s", until) if active else "",
            directions=place._ocd_directions_url(),
            phone=phone if len(phone) >= 8 else "",
            product_url=hold.product_id.website_url or hold.product_id.product_tmpl_id.website_url,
            base=f"/ocd/essayer/{hold.id}",
            token_query=urlencode({"t": t}),
        ))

    @http.route("/ocd/essayer/<int:hold_id>/annuler", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def hold_cancel(self, hold_id, t=None, **post):
        """« I no longer come »: the piece is on sale again."""
        hold = self._hold(hold_id, t)
        if hold.state in ("requested", "accepted"):
            hold._ocd_cancel_by_customer()
        return request.redirect(f"/ocd/essayer/{hold.id}?{urlencode({'t': t})}")
