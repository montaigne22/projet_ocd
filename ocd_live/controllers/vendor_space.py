from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from . import common
from .booking import OcdLiveBooking

SESSION_LOGIN = "ocd_login_vendor_id"


class OcdVendorSpace(http.Controller):
    """Space of the vendor: next lives, lives left to place, directory pass and WhatsApp
    messages. The vendor reaches it with the method chosen by the team: personal link sent on
    WhatsApp, WhatsApp number and a code, or number and password."""

    # === LOGIN === #

    @http.route("/ocd/connexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def login(self, **kwargs):
        if common.current_vendor():
            # Already known on this browser or by the Odoo account logged in: no number to give
            return request.redirect("/ocd/espace/moi")
        if common.company().ocd_vendor_login == "password":
            return request.redirect("/web/login?redirect=/ocd/espace/moi")
        return self._render_login()

    def _render_login(self, sent=False, error=None, phone=None, country=None):
        return request.render("ocd_live.space_login", common.page_values(
            False,
            back="/ocd",
            header_brand=True,
            login=common.company().ocd_vendor_login,
            sent=sent,
            error=error,
            phone_value=phone or "",
            dial_rows=common.dial_rows(country or common.default_country()),
        ))

    @http.route("/ocd/connexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def login_phone(self, phone=None, country_id=None, **kwargs):
        login = common.company().ocd_vendor_login
        if login == "password":
            return request.redirect("/web/login?redirect=/ocd/espace/moi")
        country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return self._render_login(error=common.phone_error(country), phone=phone, country=country)
        vendor = request.env["res.partner"].sudo()._ocd_find_vendor_by_phone(number)
        if vendor and login == "whatsapp_code":
            vendor._ocd_send_login_code()
            request.session[SESSION_LOGIN] = vendor.id
        elif vendor and login == "link":
            vendor._ocd_send_space_link()
        # Same answer whether the number is known or not
        if login == "whatsapp_code":
            return self._render_code()
        return self._render_login(sent=True, phone=phone, country=country)

    def _render_code(self, error=None):
        return request.render("ocd_live.space_login_code", common.page_values(
            False, back="/ocd/connexion", header_brand=True, error=error,
        ))

    @http.route("/ocd/connexion/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def login_code(self, code=None, **kwargs):
        if common.company().ocd_vendor_login != "whatsapp_code":
            raise request.not_found()
        vendor_id = request.session.get(SESSION_LOGIN)
        vendor = request.env["res.partner"].sudo().browse(vendor_id).exists() if vendor_id else None
        if vendor and vendor._ocd_check_login_code(code):
            request.session.pop(SESSION_LOGIN, None)
            request.session[common.SESSION_VENDOR] = vendor.id
            return request.redirect("/ocd/espace/moi")
        return self._render_code(error=request.env._("Wrong or expired code. Ask for a new code."))

    @http.route("/ocd/deconnexion", type="http", auth="public", website=True, sitemap=False)
    def logout(self, **kwargs):
        request.session.pop(common.SESSION_VENDOR, None)
        return request.redirect("/ocd/connexion")

    # === SPACE === #

    def _vendor_or_login(self, token):
        vendor, source = common.current_vendor_and_source(token)
        if not vendor:
            if token and token != "moi":
                raise request.not_found()
            return None, False
        return vendor, source

    @http.route("/ocd/espace/<string:token>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def space(self, token, **kwargs):
        vendor, source = self._vendor_or_login(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        company = common.company()
        now = common.now()
        bookings = env["ocd.live.booking"].sudo().search(
            [("partner_id", "=", vendor.id), ("state", "in", ("draft", "confirmed")), ("end_datetime", ">", now)],
            order="start_datetime",
        )
        credits = env["ocd.live.credit"].sudo().search(
            [("partner_id", "=", vendor.id), ("state", "=", "active"), ("remaining", ">", 0)]
        )
        listing = env["ocd.directory.listing"].sudo().search(
            [("partner_id", "=", vendor.id), ("state", "in", ("queued", "to_check", "published"))],
            order="id desc",
            limit=1,
        )
        login = company.ocd_vendor_login
        return request.render("ocd_live.space", common.page_values(
            False,
            nav="me",
            header_link=self._header_link(source),
            vendor=vendor,
            flag=(vendor.country_id.code or "").lower(),
            vendor_line=" · ".join(filter(None, [vendor.ocd_category_id.name, vendor.city, vendor.phone])),
            lives=[self._live_card(booking) for booking in bookings],
            move_limit=company.ocd_move_limit_hours,
            credits=[self._credit_card(credit) for credit in credits],
            pass_end=common.day_text(vendor.ocd_pass_end_date, "d MMMM") if vendor.ocd_pass_active else False,
            reminder_days=company.ocd_pass_reminder_days,
            listing=listing,
            login=company.ocd_vendor_login,
        ))

    def _live_card(self, booking):
        env = request.env
        company = booking.company_id
        local = company._ocd_to_local(booking.start_datetime)
        end = company._ocd_to_local(booking.end_datetime)
        needs = {
            "shelf": env._("shelf ready"),
            "rack": env._("clothes rack ready"),
            "table": env._("table ready"),
        }
        place = env._("Studio of %s", common.studio_city()) if booking.mode == "studio" else env._("Remote")
        order = booking.sale_order_id
        token = order._portal_ensure_token() if order else False
        return {
            "booking": booking,
            "when": "%s · %s – %s" % (common.short_day(local.date(), capital=True), f"{local:%H:%M}", f"{end:%H:%M}"),
            "line": " · ".join(filter(None, [
                place, booking.product_id.name, needs.get(booking.studio_need) if booking.mode == "studio" else False,
            ])),
            "paid": booking.state == "confirmed",
            "ticket_url": f"/ocd/ticket/{booking.id}",
            "move_url": f"/ocd/deplacer/{booking.id}" if booking.state == "confirmed" and (
                booking.start_datetime - common.now()
            ).total_seconds() > company.ocd_move_limit_hours * 3600 else False,
            "receipt_url": order.get_portal_url(report_type="pdf", download=True) if order and booking.state == "confirmed" else False,
            "pay_url": f"/ocd/payer/{order.id}?access_token={token}" if order and booking.state == "draft" else False,
        }

    def _credit_card(self, credit):
        env = request.env
        return {
            "credit": credit,
            "name": credit.product_id.name,
            "line": env._("%s lives to place", credit.remaining) if credit.remaining > 1 else env._("1 live to place"),
            "expiry": env._("before %s", common.day_text(credit.date_expiry)) if credit.date_expiry else False,
            "place_url": f"/ocd/espace/moi/placer/{credit.id}",
        }

    def _header_link(self, source):
        """Link of the header of the space: an Odoo account logs out of Odoo (the space would
        open again by itself otherwise), a browser forgets the vendor and asks for a number."""
        if source == "account":
            return {"href": "/web/session/logout?redirect=/ocd/connexion", "label": request.env._("Log out")}
        return {"href": "/ocd/deconnexion", "label": request.env._("Change number")}

    @http.route("/ocd/espace/moi/whatsapp", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def space_whatsapp(self, **post):
        """The vendor starts or stops the tickets and reminders on WhatsApp."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        vendor.ocd_whatsapp_optin = not vendor._ocd_whatsapp_consent()
        return request.redirect("/ocd/espace/moi")

    # === PLACE A LIVE OF A PACKAGE === #

    def _vendor_credit(self, credit_id):
        vendor = common.current_vendor()
        if not vendor:
            raise request.not_found()
        credit = request.env["ocd.live.credit"].sudo().browse(credit_id).exists()
        if not credit or credit.partner_id != vendor:
            raise request.not_found()
        return credit

    def _mode_links(self, credit, mode, day=None):
        booking = OcdLiveBooking()
        base = f"/ocd/espace/moi/placer/{credit.id}" + (f"/{day}" if day else "")
        return [
            {"label": booking._mode_texts(code)["where"], "href": f"{base}?mode={code}", "on": code == mode}
            for code in common.MODES
        ]

    @http.route(
        "/ocd/espace/moi/placer/<int:credit_id>", type="http", auth="public", website=True,
        methods=["GET"], sitemap=False,
    )
    def space_place(self, credit_id, mode="studio", mois=None, **kwargs):
        credit = self._vendor_credit(credit_id)
        mode = mode if mode in common.MODES else "studio"
        booking = OcdLiveBooking()
        month = booking._month(
            mode,
            credit.product_id.ocd_slot_count,
            mois,
            lambda day: f"/ocd/espace/moi/placer/{credit.id}/{day.isoformat()}?mode={mode}",
            lambda month: f"/ocd/espace/moi/placer/{credit.id}?mode={mode}&mois={month:%Y-%m}",
        )
        return booking._render(
            "ocd_live.booking_day",
            "day",
            mode=mode,
            back="/ocd/espace/moi",
            step=False,
            title=request.env._("Place your live"),
            mode_links=self._mode_links(credit, mode),
            month=month,
            summary=self._credit_line(credit),
            aside=self._credit_aside(credit, mode),
        )

    @http.route(
        "/ocd/espace/moi/placer/<int:credit_id>/<string:day>", type="http", auth="public", website=True,
        methods=["GET"], sitemap=False,
    )
    def space_place_hour(self, credit_id, day, mode="studio", error=None, **kwargs):
        credit = self._vendor_credit(credit_id)
        mode = mode if mode in common.MODES else "studio"
        booking = OcdLiveBooking()
        day_value = booking._check_day(day)
        return booking._render(
            "ocd_live.booking_hour",
            "hour",
            mode=mode,
            back=f"/ocd/espace/moi/placer/{credit.id}?mode={mode}&mois={day_value:%Y-%m}",
            step=False,
            title=request.env._("Which hour?"),
            lead=request.env._(
                "%(day)s · time of %(city)s", day=common.day_label(day_value), city=common.studio_city()
            ),
            mode_links=self._mode_links(credit, mode, day),
            slots=booking._slots(mode, day_value, credit.product_id, None),
            move_action=f"/ocd/espace/moi/placer/{credit.id}/{day}",
            post_values={"mode": mode},
            hour_info=request.env._(
                "A live lasts %s. It is paid by your package.",
                booking._hours_text(credit.product_id.ocd_live_hours),
            ),
            ask_wait=False,
            error=error,
            summary=self._credit_line(credit),
            aside=self._credit_aside(credit, mode),
        )

    @http.route(
        "/ocd/espace/moi/placer/<int:credit_id>/<string:day>", type="http", auth="public", website=True,
        methods=["POST"], sitemap=False,
    )
    def space_place_confirm(self, credit_id, day, hour=None, mode="studio", **kwargs):
        credit = self._vendor_credit(credit_id)
        if mode not in common.MODES:
            raise request.not_found()
        booking_controller = OcdLiveBooking()
        start = booking_controller._check_start(booking_controller._check_day(day), hour)
        try:
            booking = request.env["ocd.live.booking"].sudo()._ocd_book_with_credit(credit, start, mode)
        except (UserError, ValidationError) as error:
            return self.space_place_hour(credit_id, day, mode=mode, error=error.args[0])
        if booking.state == "draft" and booking.sale_order_id:
            # An hour that costs more: the difference is paid first
            order = booking.sale_order_id
            return request.redirect(f"/ocd/payer/{order.id}?access_token={order._portal_ensure_token()}")
        return request.redirect(f"/ocd/ticket/{booking.id}")

    def _credit_line(self, credit):
        return " · ".join(filter(None, [credit.product_id.name, self._credit_card(credit)["line"]]))

    def _credit_aside(self, credit, mode):
        card = self._credit_card(credit)
        rows = [
            (request.env._("Package"), credit.product_id.name),
            (request.env._("Left"), card["line"]),
            (request.env._("Where"), OcdLiveBooking()._mode_texts(mode)["where"]),
        ]
        if card["expiry"]:
            rows.append((request.env._("To place"), card["expiry"]))
        return {"title": request.env._("Your package"), "rows": rows}
