from datetime import timedelta

from odoo import Command, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from . import common


class OcdVendorSpace(http.Controller):
    """Space of the vendor: lives, lives to place, directory pass and live links. The vendor
    reaches it with the method chosen by the team: personal link, WhatsApp code or password."""

    # === LOGIN === #

    @http.route("/ocd/connexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def login(self, **kwargs):
        login = common.company().ocd_vendor_login
        if login == "password":
            return request.redirect("/web/login?redirect=/ocd/espace/moi")
        if common.current_vendor():
            return request.redirect("/ocd/espace/moi")
        return request.render("ocd_live.space_login", common.page_values("login", login=login, sent=False))

    @http.route("/ocd/connexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def login_phone(self, phone=None, **kwargs):
        login = common.company().ocd_vendor_login
        vendor = request.env["res.partner"].sudo()._ocd_find_vendor_by_phone(phone)
        if vendor and login == "whatsapp_code":
            vendor._ocd_send_login_code()
            request.session["ocd_login_vendor_id"] = vendor.id
        elif vendor and login == "link":
            vendor._ocd_send_space_link()
        # Same answer whether the number is known or not
        if login == "whatsapp_code":
            return request.render("ocd_live.space_login_code", common.page_values("login", error=None))
        return request.render("ocd_live.space_login", common.page_values("login", login=login, sent=True))

    @http.route("/ocd/connexion/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def login_code(self, code=None, **kwargs):
        if common.company().ocd_vendor_login != "whatsapp_code":
            raise request.not_found()
        vendor_id = request.session.get("ocd_login_vendor_id")
        vendor = request.env["res.partner"].sudo().browse(vendor_id).exists() if vendor_id else None
        if vendor and vendor._ocd_check_login_code(code):
            request.session.pop("ocd_login_vendor_id", None)
            request.session[common.SESSION_VENDOR] = vendor.id
            return request.redirect("/ocd/espace/moi")
        return request.render("ocd_live.space_login_code", common.page_values(
            "login", error=request.env._("Wrong or expired code. Ask for a new code.")
        ))

    @http.route("/ocd/deconnexion", type="http", auth="public", website=True, sitemap=False)
    def logout(self, **kwargs):
        request.session.pop(common.SESSION_VENDOR, None)
        return request.redirect("/")

    # === SPACE === #

    def _vendor_or_login(self, token):
        vendor = common.current_vendor(token)
        if not vendor:
            if token and token != "moi":
                raise request.not_found()
            return None
        return vendor

    @http.route("/ocd/espace/<string:token>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def space(self, token, message=None, error=None, **kwargs):
        vendor = self._vendor_or_login(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        now = common.now()
        bookings = request.env["ocd.live.booking"].sudo().search(
            [("partner_id", "=", vendor.id), ("state", "in", ("draft", "confirmed")), ("end_datetime", ">", now)],
            order="start_datetime",
        )
        credits = request.env["ocd.live.credit"].sudo().search(
            [("partner_id", "=", vendor.id), ("state", "=", "active")]
        )
        listing = request.env["ocd.directory.listing"].sudo().search(
            [("partner_id", "=", vendor.id)], order="id desc", limit=1
        )
        return request.render("ocd_live.space", common.page_values(
            "space",
            vendor=vendor,
            prefix=common.space_prefix(vendor, token),
            bookings=bookings,
            credits=credits,
            listing=listing,
            categories=request.env["ocd.live.category"].sudo().search([]),
            login=common.company().ocd_vendor_login,
            message=message,
            error=error,
        ))

    @http.route("/ocd/espace/<string:token>/lien", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def space_send_link(self, token, url=None, category_id=None, **kwargs):
        vendor = self._vendor_or_login(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        category = request.env["ocd.live.category"].sudo().browse(int(category_id or 0)).exists()
        try:
            request.env["ocd.directory.listing"].sudo()._ocd_submit(vendor, url, category or None)
        except (UserError, ValidationError) as error:
            return self.space(token, error=error.args[0])
        return self.space(token, message=request.env._("Thank you: the team checks your link during the window."))

    @http.route("/ocd/espace/<string:token>/pass", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def space_buy_pass(self, token, **kwargs):
        vendor = self._vendor_or_login(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = request.env.ref("ocd_live.product_directory_pass").sudo().product_variant_id
        order = request.env["sale.order"].sudo().create({
            "partner_id": vendor.id,
            "company_id": common.company().id,
            "require_signature": False,
            "prepayment_percent": 1.0,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
        })
        return request.redirect(order.get_portal_url())

    @http.route(
        "/ocd/espace/<string:token>/placer/<int:credit_id>", type="http", auth="public", website=True,
        methods=["GET"], sitemap=False,
    )
    def space_place(self, token, credit_id, mode="studio", **kwargs):
        vendor = self._vendor_or_login(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        credit = request.env["ocd.live.credit"].sudo().browse(credit_id).exists()
        if not credit or credit.partner_id != vendor:
            raise request.not_found()
        mode = mode if mode in common.MODES else "studio"
        Booking = request.env["ocd.live.booking"].sudo()
        first = common.first_bookable_day()
        days = []
        for offset in range(14):
            day = first + timedelta(days=offset)
            slots = [s for s in Booking._ocd_get_day_slots(day, credit.product_id.ocd_slot_count, common.company(), mode) if s["available"]]
            if slots:
                days.append({"label": common.day_label(day), "slots": slots})
        return request.render("ocd_live.space_place", common.page_values(
            "hour", vendor=vendor, prefix=common.space_prefix(vendor, token), credit=credit, mode=mode, days=days,
        ))

    @http.route(
        "/ocd/espace/<string:token>/placer/<int:credit_id>", type="http", auth="public", website=True,
        methods=["POST"], sitemap=False,
    )
    def space_place_confirm(self, token, credit_id, start=None, mode="studio", **kwargs):
        vendor = self._vendor_or_login(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        credit = request.env["ocd.live.credit"].sudo().browse(credit_id).exists()
        if not credit or credit.partner_id != vendor or mode not in common.MODES:
            raise request.not_found()
        try:
            start_value = request.env["ocd.live.booking"]._fields["start_datetime"].to_datetime(start)
            request.env["ocd.live.booking"].sudo()._ocd_book_with_credit(credit, start_value, mode)
        except (UserError, ValidationError, ValueError) as error:
            return self.space(token, error=error.args[0] if error.args else str(error))
        return self.space(token, message=request.env._("Your live is placed. See you soon!"))
