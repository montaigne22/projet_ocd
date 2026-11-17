"""The trust of the customers (chantier 2, design GarantieAvis): the page of the guarantee of OCD
Live, the page to report a product or a vendor, and « My reviews » of the vendor (they may report a
review to the team)."""
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.misc import hmac

from odoo.addons.ocd_live.controllers import common

from .boutique import review_rows
from .vendor_follow import visitor_partner


def visitor_key():
    """The device that reports without a number: never kept as it is (a signature)."""
    remote = request.httprequest.remote_addr or ""
    agent = request.httprequest.headers.get("User-Agent", "")[:200]
    return hmac(request.env(su=True), "ocd_live-report", f"{remote}|{agent}")


class OcdTrust(http.Controller):

    @http.route("/ocd/garantie", type="http", auth="public", website=True, sitemap=True, ocd_cache=300)
    def guarantee(self, **kwargs):
        return request.render("ocd_live_shop.guarantee_page", common.page_values(
            False,
            back="/shop",
            header_title=request.env._("OCD Live guarantee"),
            return_line=request.env._(
                "For %s days after the delivery, from the page of your order.", common.company().ocd_return_days,
            ) if common.company().ocd_return_days else "",
        ))

    # === REPORT === #

    def _target(self, produit=None, vendeur=None):
        env = request.env
        product = env["product.template"].sudo().browse(int(produit)).exists() if str(produit or "").isdigit() else None
        if product and product.is_published and product.ocd_vendor_id:
            return product, product.ocd_vendor_id
        vendor = env["res.partner"].sudo().browse(int(vendeur)).exists() if str(vendeur or "").isdigit() else None
        if vendor and vendor.ocd_is_vendor and vendor.ocd_vendor_state == "approved":
            return env["product.template"], vendor
        raise request.not_found()

    def _render_report(self, product, vendor, error=None, values=None, sent=False):
        env = request.env
        values = values or {}
        known = visitor_partner()
        reasons = env["ocd.report"]._fields["reason"]._description_selection(env)
        return request.render("ocd_live_shop.report_page", common.page_values(
            False,
            back=product.website_url if product else f"/ocd/boutique/{vendor.id}",
            header_title=env._("Report"),
            product=product,
            vendor=vendor,
            title=env._("Report %s", product.name if product else vendor.name),
            reasons=reasons,
            reason=values.get("reason") or "",
            note=values.get("note") or "",
            known=known,
            phone_value=values.get("phone") or "",
            dial_rows=common.dial_rows(known.country_id if known else (vendor.country_id or common.default_country())),
            error=error,
            sent=sent,
        ))

    @http.route("/ocd/signaler", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def report_page(self, produit=None, vendeur=None, **kwargs):
        product, vendor = self._target(produit, vendeur)
        return self._render_report(product, vendor)

    @http.route("/ocd/signaler", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def report(self, produit=None, vendeur=None, reason=None, note=None, phone=None, country_id=None, **post):
        product, vendor = self._target(produit, vendeur)
        if post.get("website_url"):
            raise request.not_found()  # a robot filled the hidden field
        env = request.env
        values = {"reason": reason, "note": note, "phone": phone}
        partner = visitor_partner()
        try:
            if not partner and (phone or "").strip():
                country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
                number = common.normalize_phone(country, phone)
                if not number:
                    raise UserError(common.phone_error(country))
                partner = env["ocd.vendor.follower"].sudo()._ocd_contact(number)
            env["ocd.report"].sudo()._ocd_create(
                reason, note, product=product, vendor=vendor, partner=partner or None, visitor_key=visitor_key(),
            )
        except UserError as exc:
            return self._render_report(product, vendor, error=exc.args[0], values=values)
        return self._render_report(product, vendor, sent=True)

    # === MY REVIEWS (the vendor) === #

    @http.route("/ocd/espace/moi/avis", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def my_reviews(self, signale=None, **kwargs):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        Review = env["ocd.vendor.review"].sudo()
        reviews = Review.search([("vendor_id", "=", vendor.id)], limit=200)
        rows = review_rows(reviews)
        for row, review in zip(rows, reviews):
            row.update({"review": review, "state": review.state})
        return request.render("ocd_live_shop.vendor_reviews", common.page_values(
            False,
            space_page="space",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My reviews"),
            vendor=vendor,
            reviews=Review._ocd_summary(vendor),
            rows=rows,
            message=env._("Reported: the team looks at it. The review stays shown until then.") if signale else None,
        ))

    @http.route("/ocd/espace/moi/avis/<int:review_id>/signaler", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def my_review_report(self, review_id, note=None, **post):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        review = request.env["ocd.vendor.review"].sudo().browse(review_id).exists()
        if not review or review.vendor_id != vendor:
            raise request.not_found()
        try:
            review._ocd_report(note)
        except UserError:
            return request.redirect(f"/ocd/espace/moi/avis#avis-{review.id}")
        return request.redirect("/ocd/espace/moi/avis?signale=1")
