from datetime import timedelta

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import BinaryBytes, consteq

from .. import media
from . import common, feed
from .booking import OcdLiveBooking

SESSION_LOGIN = "ocd_login_vendor_id"
CARD_IMAGE_MAX_BYTES = 10 * 1024 * 1024


class OcdVendorSpace(http.Controller):
    """Space of the vendor: next lives, lives left to place, directory pass and WhatsApp
    messages. The vendor reaches it with the method chosen by the team: personal link sent on
    WhatsApp, WhatsApp number and a code, or number and password."""

    # === LOGIN === #
    # The same pages serve the space of the vendors (/ocd/connexion) and, with ocd_live_shop, the
    # delivery app of the couriers and of the vendors who deliver (/ocd/livrer): the number,
    # then the personal link or a code on WhatsApp, as set for the vendors.

    LOGIN_PAGES = {
        "space": {"form": "/ocd/connexion", "code": "/ocd/connexion/code", "home": "/ocd/espace/moi"},
    }

    def _login_page_mode(self, target):
        """What the login page asks after the number: "link" (a link arrives), "whatsapp_code"
        (a code to type) or "password" (the login of Odoo). The same for every number, known
        or not."""
        return common.company().ocd_vendor_login

    def _ocd_login_partner(self, number, target):
        """Contact who logs in with `number` on the page `target` (empty when unknown)."""
        return request.env["res.partner"].sudo()._ocd_find_vendor_by_phone(number)

    def _ocd_send_link(self, partner, target):
        """Send the personal link asked on the page `target`; return whether it left."""
        return partner._ocd_send_space_link()

    def _ocd_open_session(self, partner, target):
        """This browser now opens the pages of `partner`; return the page to show."""
        common.remember_vendor(partner)
        return self.LOGIN_PAGES[target]["home"]

    @http.route("/ocd/connexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def login(self, **kwargs):
        if common.current_vendor():
            # Already known on this browser or by the Odoo account logged in: no number to give
            return request.redirect("/ocd/espace/moi")
        user = request.env.user
        if user._is_internal():
            return self._render_team()
        if common.company().ocd_vendor_login == "password":
            if not user._is_public():
                # Logged in with an account that is not a vendor: say it, instead of sending to
                # the login page that would send back here
                return self._render_account_not_vendor()
            return request.redirect("/web/login?redirect=/ocd/espace/moi")
        return self._render_login()

    def _customer(self):
        """Partner of the Odoo account logged in that is not a vendor (a customer of the shop)."""
        user = request.env.user
        return request.env["res.partner"] if user._is_public() else user.partner_id.sudo()

    def _render_login(self, sent=False, error=None, phone=None, country=None, target="space"):
        customer = self._customer()
        if customer and phone is None:
            # A customer logged in: the number of the account is filled in, it can be changed
            countries = common.directory_countries()
            country = customer.country_id if customer.country_id in countries else common.default_country()
            phone = common.local_digits(country, customer.phone) if common.normalize_phone(country, customer.phone) else ""
        page = self.LOGIN_PAGES[target]
        return request.render("ocd_live.space_login", common.page_values(
            False,
            back="/ocd",
            header_brand=True,
            login=self._login_page_mode(target),
            target=target,
            form_action=page["form"],
            password_url=f"/web/login?redirect={page['home']}" if common.company().ocd_vendor_login == "password" else False,
            sent=sent,
            error=error,
            phone_value=phone or "",
            dial_rows=common.dial_rows(country or common.default_country()),
            account_name=customer.name if customer else False,
        ))

    def _render_account_not_vendor(self):
        return request.render("ocd_live.space_account", common.page_values(
            False,
            back="/ocd",
            header_brand=True,
            nav="me",
            account_name=self._customer().name,
            # Odoo logs out by POST only: the button sends a form, then the login page
            logout_redirect="/web/login?redirect=/ocd/espace/moi",
        ))

    @http.route("/ocd/connexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def login_phone(self, phone=None, country_id=None, **kwargs):
        if common.company().ocd_vendor_login == "password" and not request.env.user._is_internal():
            return request.redirect("/web/login?redirect=/ocd/espace/moi")
        return self._login_phone(phone, country_id, "space")

    def _login_phone(self, phone, country_id, target):
        if request.env.user._is_internal():
            # The team has no space: a number typed here would send the link to the contact
            return self._render_team()
        mode = self._login_page_mode(target)
        country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return self._render_login(error=common.phone_error(country), phone=phone, country=country, target=target)
        partner = self._ocd_login_partner(number, target)
        request.session.pop(SESSION_LOGIN, None)
        if partner and mode == "whatsapp_code":
            partner._ocd_send_login_code()
            request.session[SESSION_LOGIN] = partner.id
        elif partner and mode == "link" and partner._ocd_may_send_link():
            self._ocd_send_link(partner, target)
        # Same answer whether the number is known or not
        if mode == "whatsapp_code":
            return self._render_code(target=target)
        return self._render_login(sent=True, phone=phone, country=country, target=target)

    def _render_team(self):
        """Page of a person of the team logged in to Odoo: the space is for the vendors, it does
        not open with an account of the team."""
        user = request.env.user
        team = user.has_group("ocd_live.group_ocd_live_user")
        return request.render("ocd_live.space_team", common.page_values(
            False,
            back="/ocd",
            header_brand=True,
            nav="me",
            team_name=user.name,
            back_office_url="/odoo/action-ocd_live.res_partner_action_ocd_vendor" if team else "/odoo",
            back_office_label=request.env._("Open the vendors") if team else request.env._("Open the back office"),
        ))

    def _render_code(self, error=None, target="space"):
        page = self.LOGIN_PAGES[target]
        return request.render("ocd_live.space_login_code", common.page_values(
            False, back=page["form"], header_brand=True, error=error,
            target=target, form_action=page["form"], code_action=page["code"],
        ))

    @http.route("/ocd/connexion/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def login_code(self, code=None, **kwargs):
        return self._login_code(code, "space")

    def _login_code(self, code, target):
        if self._login_page_mode(target) != "whatsapp_code":
            raise request.not_found()
        partner_id = request.session.get(SESSION_LOGIN)
        partner = request.env["res.partner"].sudo().browse(partner_id).exists() if partner_id else None
        if partner and partner._ocd_check_login_code(code):
            request.session.pop(SESSION_LOGIN, None)
            return request.redirect(self._ocd_open_session(partner, target))
        return self._render_code(error=request.env._("Wrong or expired code. Ask for a new code."), target=target)

    @http.route("/ocd/deconnexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def logout_page(self, **kwargs):
        """An old link, or a link that the browser or a proxy loads in advance: it logs nobody
        out (« Change number » is a button that sends a form)."""
        return request.redirect("/ocd/espace/moi")

    @http.route("/ocd/deconnexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def logout(self, redirect=None, **kwargs):
        """« Change number », « This is not me »: this browser forgets the vendor, then the page
        asked (the step of the booking) or the page of the number."""
        common.forget_vendor()
        return request.redirect(common.local_path(redirect, "/ocd/connexion"))

    # === THE TEAM SEES THE SPACE OF A VENDOR === #

    @http.route("/ocd/espace/equipe/<int:vendor_id>", type="http", auth="user", website=True, methods=["GET"], sitemap=False)
    def team_view(self, vendor_id, signature=None, **kwargs):
        """« See the space » of the back office: the link is signed for the person of the team
        who touched it, it opens nothing for anyone else."""
        user = request.env.user
        vendor = request.env["res.partner"].sudo().browse(vendor_id).exists()
        if (
            not user.has_group("ocd_live.group_ocd_live_user")
            or not vendor.ocd_is_vendor
            or not signature
            or not consteq(vendor._ocd_team_view_signature(user.id), signature)
        ):
            raise request.not_found()
        request.session[common.SESSION_TEAM_VIEW] = vendor.id
        return request.redirect("/ocd/espace/moi")

    @http.route("/ocd/espace/equipe/quitter", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def team_view_leave_page(self, **kwargs):
        """A link loaded in advance ends nothing: « Leave » is a button that sends a form."""
        return request.redirect("/ocd/espace/moi")

    @http.route("/ocd/espace/equipe/quitter", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def team_view_leave(self, **kwargs):
        """End of the view of the team: back to the vendor in the back office."""
        vendor_id = request.session.pop(common.SESSION_TEAM_VIEW, None)
        if vendor_id and request.env.user._is_internal():
            return request.redirect(f"/odoo/action-ocd_live.res_partner_action_ocd_vendor/{int(vendor_id)}")
        return request.redirect("/ocd")

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
            header_link=common.vendor_header_link(source),
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
            card_shown=vendor._ocd_card_shown_label(),
        ))

    def _live_card(self, booking):
        env = request.env
        local = common.to_viewer(booking.start_datetime)
        end = common.to_viewer(booking.end_datetime)
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
            ).total_seconds() > booking.company_id.ocd_move_limit_hours * 3600 else False,
            "announce_url": f"/ocd/ticket/{booking.id}#annonce" if booking.state == "confirmed" else False,
            "receipt_url": order.get_portal_url(report_type="pdf", download=True) if order and booking.state == "confirmed" else False,
            "pay_url": f"/ocd/payer/{order.id}?access_token={token}" if order and booking.state == "draft" else False,
            # Remote live of the next 2 hours: the page to join it
            "join_url": booking._ocd_join_path() if (
                booking.mode == "remote" and booking.state == "confirmed"
                and booking.start_datetime - common.now() <= timedelta(hours=2)
            ) else False,
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

    @http.route("/ocd/espace/moi/whatsapp", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def space_whatsapp(self, **post):
        """The vendor starts or stops the tickets and reminders on WhatsApp."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        vendor.ocd_whatsapp_optin = not vendor._ocd_whatsapp_consent()
        return request.redirect("/ocd/espace/moi")

    # === MY CARD IN THE LIVES === #
    # What the card of the vendor shows in the feed of the lives: a short video, its products,
    # an image (res.partner._ocd_card_media). The page shows the card as the feed does.

    def _render_card(self, vendor, errors=None, saved=False):
        env = request.env
        choices = vendor._ocd_card_choices()
        chosen = vendor.ocd_card_media or "auto"
        shown = vendor._ocd_card_media()["kind"]
        fallback = False
        if chosen != "auto" and shown != chosen:
            missing = next((choice for choice in choices if choice["value"] == chosen), None)
            if missing:
                fallback = " ".join(part for part in (
                    env._("Until then, your card shows %s.", vendor._ocd_card_shown_label().lower()),
                    missing.get("missing"),
                ) if part)
        return request.render("ocd_live.space_card", common.page_values(
            False,
            nav="me",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My card in the lives"),
            vendor=vendor,
            choices=choices,
            chosen=chosen,
            preview=feed.preview_card(vendor),
            fallback=fallback,
            errors=errors or {},
            saved=saved,
            video_url=f"/lives/video/{vendor.id}?v={vendor._ocd_card_version()}" if vendor.ocd_card_video else False,
            poster_url=f"/lives/video/{vendor.id}/image?v={vendor._ocd_card_version()}"
            if vendor.ocd_card_video and vendor.ocd_card_video_poster else False,
            image_url=f"/lives/carte/{vendor.id}?v={vendor._ocd_card_version()}" if vendor.ocd_card_image else False,
            max_video_mb=media.MAX_UPLOAD_MB if media.can_convert() else media.MAX_KEPT_MB,
            max_seconds=media.MAX_SECONDS,
        ))

    @http.route("/ocd/espace/moi/carte", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def space_card(self, enregistre=None, **kwargs):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render_card(vendor, saved=bool(enregistre))

    @http.route("/ocd/espace/moi/carte", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def space_card_save(self, choice=None, video=None, image=None, **post):
        """Save the choice of the vendor, its video (made readable by every phone) and its image.
        Each one is saved apart: a refused video does not lose the new image."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        errors = {}
        changes = []
        if choice in {row["value"] for row in vendor._ocd_card_choices()} and choice != vendor.ocd_card_media:
            vendor.ocd_card_media = choice
            changes.append(env._("the choice"))
        if post.get("remove_image"):
            if vendor.ocd_card_image:
                vendor.ocd_card_image = False
                changes.append(env._("the image"))
        elif image and getattr(image, "filename", None):
            data = image.read(CARD_IMAGE_MAX_BYTES + 1)
            if len(data) > CARD_IMAGE_MAX_BYTES:
                errors["image"] = env._("The image is too heavy: 10 MB at most.")
            elif not (image.mimetype or "").startswith("image/"):
                errors["image"] = env._("This file is not an image.")
            else:
                try:
                    with env.cr.savepoint():
                        vendor.ocd_card_image = BinaryBytes(data, filename=image.filename)
                    changes.append(env._("the image"))
                except (UserError, ValidationError):
                    errors["image"] = env._("This image cannot be read: send a photo in JPEG or PNG.")
        if post.get("remove_video"):
            if vendor.ocd_card_video:
                vendor.write({"ocd_card_video": False, "ocd_card_video_name": False})
                changes.append(env._("the video"))
        elif video and getattr(video, "filename", None):
            limit = media.MAX_UPLOAD_MB * 1024 * 1024
            data = video.read(limit + 1)
            if len(data) > limit:
                errors["video"] = vendor._ocd_video_error(media.VideoError("too_big", size=media.MAX_UPLOAD_MB))
            else:
                try:
                    with env.cr.savepoint():
                        vendor.write({
                            "ocd_card_video": BinaryBytes(data, filename=video.filename),
                            "ocd_card_video_name": video.filename,
                        })
                    changes.append(env._("the video"))
                except (UserError, ValidationError) as error:
                    errors["video"] = error.args[0]
        if changes:
            # The team sees it in the history of the vendor
            vendor.message_post(body=env._(
                "%(vendor)s changed their card in the lives: %(changes)s.", vendor=vendor.name, changes=", ".join(changes),
            ))
        if errors:
            return self._render_card(vendor, errors=errors)
        return request.redirect("/ocd/espace/moi/carte?enregistre=1")

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
                "%(day)s · %(zone)s", day=common.day_label(day_value), zone=common.viewer_zone()
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
