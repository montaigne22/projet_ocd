from odoo import fields, http
from odoo.http import request

from odoo.addons.ocd_live.controllers import common


class OcdBoutique(http.Controller):
    """Boutique of a vendor: the products, the live of the moment with the product shown on
    screen, and the replay of the last live with its moments."""

    def _vendor(self, vendor_id):
        vendor = request.env["res.partner"].sudo().browse(vendor_id).exists()
        if not vendor or not vendor.ocd_is_vendor or vendor.ocd_vendor_state != "approved":
            raise request.not_found()
        return vendor

    def _current_live(self, vendor):
        now = fields.Datetime.now()
        return request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id),
            ("state", "=", "confirmed"),
            ("start_datetime", "<=", now),
            ("end_datetime", ">", now),
        ], limit=1)

    @http.route("/ocd/boutique/<int:vendor_id>", type="http", auth="public", website=True, sitemap=False)
    def boutique(self, vendor_id, **kwargs):
        vendor = self._vendor(vendor_id)
        products = request.env["product.template"].sudo().search([
            ("ocd_vendor_id", "=", vendor.id),
            ("ocd_review_state", "=", "approved"),
            ("is_published", "=", True),
            ("sale_ok", "=", True),
        ], order="website_sequence, id")
        replay = request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id),
            ("replay_published", "=", True),
        ], order="start_datetime desc", limit=1)
        live = self._current_live(vendor)
        if live:
            # One visit per browser and per live, shown in the control room
            seen = request.session.get("ocd_live_visits", [])
            if live.id not in seen:
                live._ocd_count_visit()
                request.session["ocd_live_visits"] = (seen + [live.id])[-20:]
        return request.render("ocd_live_shop.boutique", common.page_values(
            "boutique",
            vendor=vendor,
            products=products,
            live=live,
            replay=replay,
        ))

    @http.route("/ocd/boutique/<int:vendor_id>/live", type="jsonrpc", auth="public", website=True)
    def boutique_live(self, vendor_id):
        """Product shown now during the live, read by the boutique every 20 seconds."""
        vendor = self._vendor(vendor_id)
        product = self._current_live(vendor).current_product_tmpl_id
        if not product:
            return {"id": False}
        return {"id": product.id, "name": product.name, "url": product.website_url}

    @http.route("/ocd/wa/<int:product_id>", type="http", auth="public", website=True, sitemap=False)
    def whatsapp(self, product_id, **kwargs):
        """Count the contact, then open WhatsApp with the vendor."""
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or not product.ocd_vendor_id or product.ocd_review_state != "approved":
            raise request.not_found()
        url = product._ocd_whatsapp_url()
        if not url:
            raise request.not_found()
        product.ocd_wa_clicks += 1
        return request.redirect(url, local=False)
