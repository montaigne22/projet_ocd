import re
from datetime import date, timedelta

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import consteq, format_date

from odoo.addons.ocd_live.models.ocd_live_price_rule import percent_text

from . import common

STUDIO_NEEDS = ("shelf", "rack", "table")
MAX_HELD = 3
# A day with this number of free hours or less is shown as almost full
ALMOST_FULL = 2
MONTHS_AHEAD = 3


def _add_months(day, months):
    month = day.month - 1 + months
    return date(day.year + month // 12, month % 12 + 1, 1)


class OcdLiveBooking(http.Controller):
    """Booking of a live, one question per page, as in the validated design. The order of the
    steps is a setting: day, hour, then package (default), or package, then day and hour."""

    # === HOME === #

    @http.route(["/ocd", "/reserver"], type="http", auth="public", website=True, sitemap=True, methods=["GET"])
    def home(self, **kwargs):
        listings, counts = common.live_counts()
        return request.render("ocd_live.home", common.page_values(
            "home",
            nav="home",
            live_total=len(listings),
            chips=common.country_chips(counts),
            studio_place=", ".join(filter(None, [common.studio_city(), common.company().country_id.name])),
        ))

    # === STEPS === #

    @http.route("/reserver/<string:mode>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def booking_start(self, mode, mois=None, **kwargs):
        self._check_mode(mode)
        if self._flow() == "package_first":
            return self._render_packages(mode)
        return self._render_day(mode, None, mois)

    @http.route(
        "/reserver/<string:mode>/paquet/<int:product_id>",
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def booking_package_day(self, mode, product_id, mois=None, **kwargs):
        self._check_mode(mode)
        return self._render_day(mode, self._check_package(product_id), mois)

    @http.route(
        ["/reserver/<string:mode>/<string:day>", "/reserver/<string:mode>/paquet/<int:product_id>/<string:day>"],
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def booking_hour(self, mode, day, product_id=None, attente=None, error=None, occupe=None, **kwargs):
        self._check_mode(mode)
        day_value = self._check_day(day)
        if occupe and not error:
            error = request.env._("This hour can no longer be booked: choose another one.")
        product = self._check_package(product_id) if product_id else None
        if product:
            next_url = lambda slot: f"/reserver/{mode}/{day}/{slot['code']}/{product.id}"  # noqa: E731
            back = f"/reserver/{mode}/paquet/{product.id}?mois={day_value:%Y-%m}"
        else:
            next_url = lambda slot: f"/reserver/{mode}/{day}/{slot['code']}"  # noqa: E731
            back = f"/reserver/{mode}?mois={day_value:%Y-%m}"
        slots = self._slots(mode, day_value, product, next_url)
        vendor = common.current_vendor()
        return self._render(
            "ocd_live.booking_hour",
            "hour",
            page_url=f"/reserver/{mode}/paquet/{product.id}/{day}" if product else f"/reserver/{mode}/{day}",
            mode=mode,
            back=back,
            step=common.steps(self._flow(), "hour"),
            lead=request.env._(
                "%(day)s · time of %(city)s", day=common.day_label(day_value), city=common.studio_city()
            ),
            slots=slots,
            hour_info=request.env._(
                "A live lasts %(hours)s. We hold your hour %(minutes)s minutes while you pay.",
                hours=self._hours_text(product.ocd_live_hours if product else common.company().ocd_slot_hours),
                minutes=common.company().ocd_hold_minutes,
            ),
            ask_wait=sum(1 for slot in slots if slot["available"]) <= ALMOST_FULL,
            waiting=bool(attente),
            wait_values={"mode": mode, "day": day, "product_id": product.id if product else ""},
            vendor=vendor,
            dial_rows=common.dial_rows(vendor.country_id if vendor else common.default_country()),
            error=error,
            summary=self._summary(mode, day_value, product=product),
            aside=self._aside(mode, day_value, product=product),
        )

    @http.route(
        "/reserver/<string:mode>/<string:day>/<string:hour>",
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def booking_package(self, mode, day, hour, **kwargs):
        self._check_mode(mode)
        day_value = self._check_day(day)
        start = self._check_start(day_value, hour)
        return self._render(
            "ocd_live.booking_package",
            "package",
            mode=mode,
            back=f"/reserver/{mode}/{day}",
            step=common.steps(self._flow(), "package"),
            lead=request.env._(
                "%(day)s at %(hour)s", day=common.day_label(day_value), hour=self._hour_label(hour)
            ),
            cards=self._package_cards(
                mode, lambda product: f"/reserver/{mode}/{day}/{hour}/{product.id}", day_value, start
            ),
            summary=self._summary(mode, day_value, hour),
            aside=self._aside(mode, day_value, hour),
        )

    def _render_packages(self, mode):
        """First step of the flow "package, then day and hour"."""
        return self._render(
            "ocd_live.booking_package",
            "package",
            mode=mode,
            back="/ocd",
            step=common.steps(self._flow(), "package"),
            lead=self._mode_texts(mode)["tag"],
            cards=self._package_cards(mode, lambda product: f"/reserver/{mode}/paquet/{product.id}"),
            summary=self._mode_texts(mode)["short"],
            aside=self._aside(mode),
        )

    @http.route(
        "/reserver/<string:mode>/<string:day>/<string:hour>/<int:product_id>",
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def booking_infos(self, mode, day, hour, product_id, error=None, errors=None, **kwargs):
        self._check_mode(mode)
        product = self._check_package(product_id)
        day_value = self._check_day(day)
        self._check_start(day_value, hour)
        vendor = common.current_vendor()
        categories = request.env["ocd.live.category"].sudo().search([])
        values = dict(kwargs)
        country = request.env["res.country"].sudo().browse(int(values.get("country_id") or 0)).exists()
        if not country:
            country = (vendor.country_id if vendor else None) or common.default_country()
        values.setdefault("category_id", str(categories[:1].id))
        values.setdefault("studio_need", "table")
        values.setdefault("optin", "1" if not errors else "")
        if self._flow() == "package_first":
            back = f"/reserver/{mode}/paquet/{product.id}/{day}"
        else:
            back = f"/reserver/{mode}/{day}/{hour}"
        return self._render(
            "ocd_live.booking_infos",
            "infos",
            page_url=f"/reserver/{mode}/{day}/{hour}/{product.id}",
            mode=mode,
            back=back,
            step=common.steps(self._flow(), "infos"),
            hidden={"mode": mode, "day": day, "hour": hour, "product_id": product.id},
            vendor=vendor,
            categories=categories,
            dial_rows=common.dial_rows(country),
            needs=[
                ("shelf", request.env._("Shelf")),
                ("rack", request.env._("Clothes rack")),
                ("table", request.env._("Table")),
            ],
            values=values,
            errors=errors or {},
            error=error,
            summary=False,
            aside=self._aside(mode, day_value, hour, product),
        )

    # === ACTIONS === #

    @http.route("/reserver/attente", type="http", auth="public", website=True, methods=["GET", "POST"], sitemap=False)
    def booking_wait(self, mode=None, day=None, product_id=None, phone=None, country_id=None, **post):
        """Put the vendor on the waiting list of a full day."""
        if request.httprequest.method != "POST" or not (mode and day):
            return request.redirect("/reserver")
        self._check_mode(mode)
        day_value = self._check_day(day)
        product = self._check_package(int(product_id)) if product_id else None
        url = f"/reserver/{mode}/paquet/{product.id}/{day}" if product else f"/reserver/{mode}/{day}"
        if post.get("website_url"):
            raise request.not_found()
        vendor = common.current_vendor()
        Waitlist = request.env["ocd.live.waitlist"].sudo()
        if vendor:
            Waitlist.with_company(common.company())._ocd_register(None, day_value, mode, partner=vendor)
        else:
            country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists()
            number = common.normalize_phone(country, phone)
            if not number:
                return self.booking_hour(
                    mode, day, product_id=product.id if product else None,
                    error=self._phone_error(country),
                )
            Waitlist.with_company(common.company())._ocd_register(number, day_value, mode)
        return request.redirect(f"{url}?attente=1")

    @http.route("/reserver/confirmer", type="http", auth="public", website=True, methods=["GET", "POST"], sitemap=False)
    def booking_confirm(self, mode=None, day=None, hour=None, product_id=None, **post):
        if request.httprequest.method != "POST" or not (mode and day and hour and product_id):
            # Opened again without the form (page reloaded by the phone, back button, link): no
            # empty page, the booking starts again
            return request.redirect("/reserver")
        self._check_mode(mode)
        product = self._check_package(int(product_id))
        day_value = common.parse_day(day)
        if not day_value or day_value < common.first_bookable_day():
            return request.redirect(self._day_url(mode, product))
        start = common.find_start(day_value, hour)
        if not start:
            # The hour was taken or is too close now: choose another one, with a message
            return request.redirect(f"{self._hour_url(mode, day, product)}?occupe=1")
        if post.get("website_url"):
            # Honeypot field, hidden to the humans
            raise request.not_found()
        retry = {"mode": mode, "day": day, "hour": hour, "product_id": product.id}
        vendor = common.current_vendor()
        Booking = request.env["ocd.live.booking"].sudo()
        try:
            if not vendor:
                vendor = self._find_or_create_vendor(post)
            elif "optin" in post or post.get("optin_shown"):
                vendor.ocd_whatsapp_optin = bool(post.get("optin"))
            held = Booking.search([("partner_id", "=", vendor.id), ("state", "=", "draft")])
            same = held.filtered(lambda b: b.start_datetime == start and b.mode == mode)
            if same and same[:1].product_id == product and same[:1].sale_order_id.state in ("draft", "sent"):
                # The vendor came back from the payment page: keep the slot already held
                return request.redirect(self._pay_url(same[:1].sale_order_id))
            if same:
                same.action_cancel()
                held -= same
            if len(held) >= MAX_HELD:
                raise UserError(request.env._("You already hold lives that are not paid: pay them first."))
            need = post.get("studio_need") if post.get("studio_need") in STUDIO_NEEDS else "none"
            booking = Booking.with_company(common.company())._ocd_book_from_website(
                vendor, product, start, mode, need if mode == "studio" else "none"
            )
        except common.FormErrors as error:
            return self.booking_infos(errors=error.errors, **retry, **post)
        except (UserError, ValidationError) as error:
            return self.booking_infos(error=error.args[0], **retry, **post)
        return request.redirect(self._pay_url(booking.sale_order_id))

    def _day_url(self, mode, product):
        if self._flow() == "package_first":
            return f"/reserver/{mode}/paquet/{product.id}"
        return f"/reserver/{mode}"

    def _hour_url(self, mode, day, product):
        if self._flow() == "package_first":
            return f"/reserver/{mode}/paquet/{product.id}/{day}"
        return f"/reserver/{mode}/{day}"

    def _pay_url(self, order):
        return f"/ocd/payer/{order.id}?access_token={order._portal_ensure_token()}"

    def _find_or_create_vendor(self, post):
        return common.find_or_create_vendor(post)

    # === MOVE A LIVE === #

    def _movable_booking(self, booking_id, access_token=None):
        """Return the confirmed live of the vendor, reached from the ticket (token of the
        order) or from the space of the vendor."""
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        if not booking or booking.state != "confirmed":
            raise request.not_found()
        vendor = common.current_vendor()
        order = booking.sale_order_id
        allowed = (vendor and booking.partner_id == vendor) or (
            access_token and order and order.access_token and consteq(order.access_token, access_token)
        )
        if not allowed:
            raise request.not_found()
        return booking

    @http.route("/ocd/deplacer/<int:booking_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def move_day(self, booking_id, access_token=None, mois=None, **kwargs):
        booking = self._movable_booking(booking_id, access_token)
        token = f"?access_token={access_token}" if access_token else ""
        month = self._month(
            booking.mode,
            booking.slot_count,
            mois,
            lambda day: f"/ocd/deplacer/{booking.id}/{day.isoformat()}{token}",
            lambda month: f"/ocd/deplacer/{booking.id}?mois={month:%Y-%m}" + (f"&access_token={access_token}" if access_token else ""),
        )
        return self._render(
            "ocd_live.booking_day",
            "day",
            mode=booking.mode,
            back=self._ticket_url(booking, access_token),
            step=False,
            title=request.env._("New day?"),
            month=month,
            summary=self._booking_line(booking),
            aside=self._aside_booking(booking),
            move_limit=booking.company_id.ocd_move_limit_hours,
        )

    @http.route(
        "/ocd/deplacer/<int:booking_id>/<string:day>",
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def move_hour(self, booking_id, day, access_token=None, error=None, **kwargs):
        booking = self._movable_booking(booking_id, access_token)
        day_value = self._check_day(day)
        slots = self._slots(
            booking.mode, day_value, booking.product_id, None,
            slot_count=booking.slot_count, max_percent=booking.price_percent or 0.0,
        )
        token = f"?access_token={access_token}" if access_token else ""
        return self._render(
            "ocd_live.booking_hour",
            "hour",
            mode=booking.mode,
            back=f"/ocd/deplacer/{booking.id}?mois={day_value:%Y-%m}" + (f"&access_token={access_token}" if access_token else ""),
            step=False,
            title=request.env._("New hour?"),
            lead=request.env._(
                "%(day)s · time of %(city)s", day=common.day_label(day_value), city=common.studio_city()
            ),
            slots=slots,
            move_action=f"/ocd/deplacer/{booking.id}/{day}{token}",
            hour_info=request.env._(
                "Your live lasts %s. Choose its new hour.",
                self._hours_text(booking.slot_count * booking.company_id.ocd_slot_hours),
            ),
            ask_wait=False,
            error=error,
            summary=self._booking_line(booking),
            aside=self._aside_booking(booking),
        )

    @http.route(
        "/ocd/deplacer/<int:booking_id>/<string:day>",
        type="http", auth="public", website=True, sitemap=False, methods=["POST"],
    )
    def move_confirm(self, booking_id, day, hour=None, access_token=None, **kwargs):
        booking = self._movable_booking(booking_id, access_token)
        day_value = self._check_day(day)
        start = self._check_start(day_value, hour)
        try:
            booking._ocd_move(start)
        except (UserError, ValidationError) as error:
            return self.move_hour(booking_id, day, access_token=access_token, error=error.args[0])
        return request.redirect(self._ticket_url(booking, access_token) + ("&" if access_token else "?") + "deplace=1")

    def _ticket_url(self, booking, access_token=None):
        if access_token:
            return f"/ocd/ticket/{booking.id}?access_token={access_token}"
        return f"/ocd/ticket/{booking.id}"

    # === HELPERS === #

    def _flow(self):
        return common.company().ocd_booking_flow

    def _render(self, template, voice_key, page_url=None, **values):
        values.setdefault("step_label", request.env._("Step %(step)s of %(total)s", step=values.get("step"), total=5))
        if page_url and request.httprequest.method == "POST":
            # Shown again after a form sent with an error (/reserver/confirmer, /reserver/attente):
            # the page takes the address of its step, so that reloading it (or the phone
            # reopening the tab) shows the step again
            values["replace_url"] = page_url
            values["page_languages"] = common.page_languages(page_url)
        return request.render(template, common.page_values(voice_key, flow=self._flow(), **values))

    def _check_mode(self, mode):
        if mode not in common.MODES:
            raise request.not_found()

    def _check_day(self, day):
        day_value = common.parse_day(day)
        if not day_value or day_value < common.first_bookable_day():
            raise request.not_found()
        return day_value

    def _check_start(self, day_value, hour):
        start = common.find_start(day_value, hour or "")
        if not start:
            raise request.not_found()
        return start

    def _check_package(self, product_id):
        product = request.env["product.product"].sudo().browse(product_id).exists()
        if not product or product.ocd_product_kind != "live_package" or not product.sale_ok:
            raise request.not_found()
        return product

    def _phone_error(self, country):
        return common.phone_error(country)

    def _hour_label(self, hour):
        return f"{hour[:2]}:{hour[2:]}"

    def _hours_text(self, hours):
        """Return a duration as in the design: "1 h 30", "4 h"."""
        minutes = round(hours * 60)
        return f"{minutes // 60} h {minutes % 60:02d}" if minutes % 60 else f"{minutes // 60} h"

    def _mode_texts(self, mode):
        city = common.studio_city()
        if mode == "studio":
            return {
                "tag": request.env._("At the studio · %s", city),
                "short": request.env._("Studio"),
                "where": request.env._("At the studio · %s", city),
            }
        return {
            "tag": request.env._("From home · remote"),
            "short": request.env._("Remote"),
            "where": request.env._("From home, remote"),
        }

    def _summary(self, mode, day=None, hour=None, product=None):
        """Line at the bottom of the phone: what is chosen so far."""
        parts = [self._mode_texts(mode)["short"]]
        if day:
            parts.append(common.short_day(day))
        if hour:
            parts.append(self._hour_label(hour))
        if product:
            parts.append(product.name)
        return " · ".join(parts)

    def _aside(self, mode, day=None, hour=None, product=None):
        """What is chosen so far, shown beside the page on a computer."""
        rows = [(request.env._("Where"), self._mode_texts(mode)["where"])]
        if day:
            rows.append((request.env._("Day"), common.day_label(day)))
        if hour:
            start = common.find_start(day, hour)
            hours = product.ocd_live_hours if product else common.company().ocd_slot_hours
            end = common.company()._ocd_to_local(start) + timedelta(hours=hours)
            rows.append((request.env._("Hour"), f"{self._hour_label(hour)} – {end:%H:%M}"))
        if product:
            amount, currency = common.package_price(product, self._prices())
            if hour:
                percent = request.env["ocd.live.price.rule"]._ocd_percent(
                    common.company(), common.find_start(day, hour), mode, product
                )
                amount += currency.round(amount / max(product.ocd_live_count, 1) * percent / 100)
            rows.append((request.env._("Package"), product.name))
            rows.append((request.env._("Price"), common.money(amount, currency)))
        return {"title": request.env._("Your booking"), "rows": rows}

    def _prices(self):
        """Pricelist of the visitor: the one of the vendor when known, else the one Odoo gives
        to the country of the visitor."""
        return common.pricelist(vendor=common.current_vendor())

    def _booking_line(self, booking):
        local = booking.company_id._ocd_to_local(booking.start_datetime)
        return " · ".join([
            self._mode_texts(booking.mode)["short"], common.short_day(local.date()), f"{local:%H:%M}"
        ])

    def _aside_booking(self, booking):
        local = booking.company_id._ocd_to_local(booking.start_datetime)
        end = booking.company_id._ocd_to_local(booking.end_datetime)
        return {
            "title": request.env._("Your live now"),
            "rows": [
                (request.env._("Where"), self._mode_texts(booking.mode)["where"]),
                (request.env._("Day"), common.day_label(local.date())),
                (request.env._("Hour"), f"{local:%H:%M} – {end:%H:%M}"),
                (request.env._("Package"), booking.product_id.name),
            ],
        }

    def _render_day(self, mode, product, month_param):
        if product:
            day_url = lambda day: f"/reserver/{mode}/paquet/{product.id}/{day.isoformat()}"  # noqa: E731
            month_url = lambda month: f"/reserver/{mode}/paquet/{product.id}?mois={month:%Y-%m}"  # noqa: E731
            back = f"/reserver/{mode}"
        else:
            day_url = lambda day: f"/reserver/{mode}/{day.isoformat()}"  # noqa: E731
            month_url = lambda month: f"/reserver/{mode}?mois={month:%Y-%m}"  # noqa: E731
            back = "/ocd"
        return self._render(
            "ocd_live.booking_day",
            "day",
            mode=mode,
            back=back,
            step=common.steps(self._flow(), "day"),
            title=request.env._("Which day?"),
            tag=self._mode_texts(mode)["tag"],
            month=self._month(mode, product.ocd_slot_count if product else 1, month_param, day_url, month_url),
            summary=self._summary(mode, product=product),
            aside=self._aside(mode, product=product),
        )

    def _month(self, mode, slot_count, month_param, day_url, month_url):
        """Return the month of the calendar: each day free, almost full, full or closed."""
        current = common.company()
        first = common.first_bookable_day()
        first_month = first.replace(day=1)
        last_month = _add_months(first_month, MONTHS_AHEAD - 1)
        month = first_month
        if month_param and re.fullmatch(r"\d{4}-\d{2}", month_param):
            try:
                month = min(max(date(int(month_param[:4]), int(month_param[5:]), 1), first_month), last_month)
            except ValueError:
                month = first_month
        next_month = _add_months(month, 1)
        days = [month + timedelta(days=offset) for offset in range((next_month - month).days)]
        counts = request.env["ocd.live.booking"].sudo()._ocd_get_free_counts(
            [day for day in days if day >= first], slot_count=slot_count, company=current, mode=mode
        )
        env = request.env
        texts = {
            "free": env._("free"),
            "almost": env._("almost full"),
            "full": env._("full"),
            "off": env._("closed"),
        }
        cells = []
        for day in days:
            free = counts.get(day, 0)
            if day < first or not current._ocd_is_open_day(day):
                state = "off"
            elif free:
                state = "almost" if free <= ALMOST_FULL else "free"
            else:
                state = "full"
            cells.append({
                "number": day.day,
                "state": state,
                "href": day_url(day) if state in ("free", "almost") else False,
                "label": f"{common.day_text(day)}, {texts[state]}",
            })
        monday = first - timedelta(days=first.weekday())
        return {
            "title": format_date(env, month, date_format="MMMM yyyy"),
            "weekdays": [
                format_date(env, monday + timedelta(days=offset), date_format="EEEEE") for offset in range(7)
            ],
            "offset": range(month.weekday()),
            "cells": cells,
            "prev": month_url(_add_months(month, -1)) if month > first_month else False,
            "next": month_url(next_month) if next_month <= last_month else False,
        }

    def _slots(self, mode, day, product, next_url, slot_count=None, max_percent=None):
        """Return the hours of `day`: free ones lead to `next_url`, the others are taken."""
        count = slot_count or (product.ocd_slot_count if product else 1)
        slots = request.env["ocd.live.booking"].sudo()._ocd_get_day_slots(
            day, slot_count=count, company=common.company(), mode=mode
        )
        env = request.env
        company = common.company()
        rules = env["ocd.live.price.rule"]._ocd_rules(company)
        for slot in slots:
            slot["code"] = slot["label"].replace(":", "")
            slot["percent"] = rules._ocd_match(company, slot["start"], mode, product).percent or 0.0
            if max_percent is not None and slot["percent"] > max_percent:
                # Moving a live: not to an hour that costs more
                slot["available"] = False
            slot["percent_text"] = percent_text(slot["percent"]) if slot["percent"] and slot["available"] else False
            slot["href"] = next_url(slot) if next_url and slot["available"] else False
            slot["aria"] = "%s, %s" % (slot["label"], env._("free") if slot["available"] else env._("taken"))
            if slot["percent_text"]:
                slot["aria"] += ", %s" % slot["percent_text"]
        return slots

    def _package_cards(self, mode, next_url, day=None, start=None):
        """Return the packages as in the design: badge, name, line, price and saving."""
        env = request.env
        products = common.packages()
        prices = self._prices()
        amounts = {product: common.package_price(product, prices) for product in products}
        base = products.filtered(lambda p: p.ocd_live_count == 1 and not p.ocd_with_announce)[:1] or products[:1]
        base_live = amounts[base][0] / max(base.ocd_live_count, 1) if base else 0
        base_hour = base_live / base.ocd_live_hours if base and base.ocd_live_hours else 0
        Booking = env["ocd.live.booking"].sudo()
        day_slots = {}
        cards = []
        for product in products:
            available = True
            line = product.description_sale or ""
            if start:
                count = product.ocd_slot_count
                if count not in day_slots:
                    day_slots[count] = Booking._ocd_get_day_slots(day, slot_count=count, company=common.company(), mode=mode)
                slot = next((s for s in day_slots[count] if s["start"] == start), None)
                available = bool(slot and slot["available"])
                if product.ocd_live_count == 1 and count > 1 and slot:
                    line = env._("1 long live, from %(start)s to %(end)s", start=slot["label"], end=slot["end_label"])
            amount, currency = amounts[product]
            per_live = amount / max(product.ocd_live_count, 1)
            per_hour = per_live / product.ocd_live_hours if product.ocd_live_hours else 0
            hour_percent = 0.0
            if start:
                hour_percent = env["ocd.live.price.rule"]._ocd_percent(common.company(), start, mode, product)
                amount += currency.round(per_live * hour_percent / 100)
            save = False
            if product.ocd_save_tag == "per_live" and base_live and per_live < base_live:
                save = env._("cheaper per live")
            elif product.ocd_save_tag == "per_hour" and base_hour and per_hour < base_hour:
                save = env._("cheaper per hour")
            badge = product.ocd_badge or ""
            if re.fullmatch(r"x\d+", badge):
                badge = "×" + badge[1:]
            cards.append({
                "product": product,
                "badge": badge if badge not in ("", "+") else False,
                "line": line,
                "price": common.money(amount, currency),
                "save": save,
                "hour_tag": env._("%s this hour", percent_text(hour_percent)) if hour_percent else False,
                "hour_up": hour_percent > 0,
                "available": available,
                "href": next_url(product) if available else False,
            })
        return cards
