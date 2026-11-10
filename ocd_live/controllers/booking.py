import re

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from . import common

STUDIO_NEEDS = ("none", "shelf", "rack", "table")
DIRECTORY_COUNTRIES = ("cm", "tg", "bj", "ci", "sn")
MAX_HELD = 3


class OcdLiveBooking(http.Controller):
    """Booking of a live, one question per page. The order of the steps is a setting:
    day, hour, then package (default), or package, then day and hour."""

    def _render(self, template, voice_key, **values):
        return request.render(template, common.page_values(voice_key, flow=common.company().ocd_booking_flow, **values))

    def _check_mode(self, mode):
        if mode not in common.MODES:
            raise request.not_found()

    def _check_package(self, product_id):
        product = request.env["product.product"].sudo().browse(product_id).exists()
        if not product or product.ocd_product_kind != "live_package" or not product.sale_ok:
            raise request.not_found()
        return product

    @http.route("/reserver", type="http", auth="public", website=True, sitemap=True)
    def booking_mode(self, **kwargs):
        return self._render("ocd_live.booking_mode", "mode")

    @http.route("/reserver/<string:mode>", type="http", auth="public", website=True, sitemap=False)
    def booking_first_step(self, mode, **kwargs):
        self._check_mode(mode)
        if common.company().ocd_booking_flow == "package_first":
            return self._render("ocd_live.booking_package", "package", mode=mode, packages=common.packages())
        return self._booking_day(mode)

    def _booking_day(self, mode, product=None):
        slot_count = product.ocd_slot_count if product else 1
        return self._render(
            "ocd_live.booking_day",
            "day",
            mode=mode,
            product=product,
            weeks=common.calendar_weeks(slot_count, mode),
        )

    @http.route("/reserver/<string:mode>/paquet/<int:product_id>", type="http", auth="public", website=True, sitemap=False)
    def booking_day_of_package(self, mode, product_id, **kwargs):
        self._check_mode(mode)
        return self._booking_day(mode, self._check_package(product_id))

    @http.route(
        ["/reserver/<string:mode>/<string:day>", "/reserver/<string:mode>/paquet/<int:product_id>/<string:day>"],
        type="http", auth="public", website=True, sitemap=False,
    )
    def booking_hour(self, mode, day, product_id=None, error=None, **kwargs):
        self._check_mode(mode)
        day_value = common.parse_day(day)
        if not day_value or day_value < common.first_bookable_day():
            raise request.not_found()
        product = self._check_package(product_id) if product_id else None
        slots = request.env["ocd.live.booking"].sudo()._ocd_get_day_slots(
            day_value,
            slot_count=product.ocd_slot_count if product else 1,
            company=common.company(),
            mode=mode,
        )
        for slot in slots:
            slot["code"] = slot["label"].replace(":", "")
        return self._render(
            "ocd_live.booking_hour",
            "hour",
            mode=mode,
            day=day,
            day_label=common.day_label(day_value),
            product=product,
            slots=slots,
            error=error,
        )

    @http.route("/reserver/<string:mode>/<string:day>/<string:hour>", type="http", auth="public", website=True, sitemap=False)
    def booking_package(self, mode, day, hour, **kwargs):
        self._check_mode(mode)
        day_value = common.parse_day(day)
        start = common.find_start(day_value, hour) if day_value else None
        if not start:
            raise request.not_found()
        Booking = request.env["ocd.live.booking"].sudo()
        choices = []
        for product in common.packages():
            slots = Booking._ocd_get_day_slots(day_value, slot_count=product.ocd_slot_count, company=common.company(), mode=mode)
            slot = next((s for s in slots if s["start"] == start), None)
            choices.append({"product": product, "available": bool(slot and slot["available"])})
        return self._render(
            "ocd_live.booking_package_at",
            "package",
            mode=mode,
            day=day,
            hour=hour,
            day_label=common.day_label(day_value),
            hour_label=f"{hour[:2]}:{hour[2:]}",
            choices=choices,
        )

    @http.route(
        "/reserver/<string:mode>/<string:day>/<string:hour>/<int:product_id>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def booking_infos(self, mode, day, hour, product_id, error=None, **kwargs):
        self._check_mode(mode)
        product = self._check_package(product_id)
        day_value = common.parse_day(day)
        start = common.find_start(day_value, hour) if day_value else None
        if not start:
            raise request.not_found()
        vendor = common.current_vendor()
        countries = request.env["res.country"].sudo().search([("code", "in", [c.upper() for c in DIRECTORY_COUNTRIES])])
        if not kwargs.get("country_id"):
            geoip_code = request.geoip.country_code
            default = countries.filtered(lambda c: c.code == geoip_code) or (
                common.company().country_id & countries
            ) or countries.filtered(lambda c: c.code == "TG")
            kwargs["country_id"] = str(default[:1].id)
        return self._render(
            "ocd_live.booking_infos",
            "infos",
            mode=mode,
            day=day,
            hour=hour,
            day_label=common.day_label(day_value),
            hour_label=f"{hour[:2]}:{hour[2:]}",
            product=product,
            vendor=vendor,
            countries=countries,
            categories=request.env["ocd.live.category"].sudo().search([]),
            values=kwargs,
            error=error,
        )

    @http.route("/reserver/confirmer", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def booking_confirm(self, mode, day, hour, product_id, **post):
        self._check_mode(mode)
        product = self._check_package(int(product_id))
        day_value = common.parse_day(day)
        start = common.find_start(day_value, hour) if day_value else None
        if not start:
            raise request.not_found()
        if post.get("website_url"):
            # Honeypot field, hidden to the humans
            raise request.not_found()
        retry = {"mode": mode, "day": day, "hour": hour, "product_id": product.id}
        vendor = common.current_vendor()
        try:
            if not vendor:
                vendor = self._find_or_create_vendor(post)
            held = request.env["ocd.live.booking"].sudo().search_count(
                [("partner_id", "=", vendor.id), ("state", "=", "draft")]
            )
            if held >= MAX_HELD:
                raise UserError(request.env._("You already hold lives that are not paid: pay them first."))
            need = post.get("studio_need") if post.get("studio_need") in STUDIO_NEEDS else "none"
            booking = request.env["ocd.live.booking"].sudo()._ocd_book_from_website(
                vendor, product, start, mode, need if mode == "studio" else "none"
            )
        except (UserError, ValidationError) as error:
            return self.booking_infos(error=error.args[0], **retry, **post)
        return request.redirect(booking.sale_order_id.get_portal_url())

    def _find_or_create_vendor(self, post):
        name = common.clean_text(post.get("name"))
        business = common.clean_text(post.get("business"))
        phone = common.clean_text(post.get("phone"), 30)
        if not name or not business or len(re.sub(r"\D", "", phone)) < 8:
            raise UserError(request.env._("Fill in your name, what you sell and your WhatsApp number."))
        Partner = request.env["res.partner"].sudo()
        vendor = Partner._ocd_find_vendor_by_phone(phone)
        if vendor and vendor.name.casefold() == name.casefold():
            return vendor
        country = request.env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists()
        category = request.env["ocd.live.category"].sudo().browse(int(post.get("category_id") or 0)).exists()
        return Partner.create({
            "name": name,
            "ocd_business": business,
            "phone": phone,
            "city": common.clean_text(post.get("city")),
            "country_id": country.id,
            "ocd_category_id": category.id,
            "ocd_is_vendor": True,
            "is_company": True,
        })
