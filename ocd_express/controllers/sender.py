"""The space of a sender of OCD Express (design OcdExpress): the page /express, the request, the
login with the number and a code on WhatsApp, « New parcel », « My parcels », « My money ».

A vendor of OCD Live keeps their space: once their account of OCD Express is open, the vendor
logged in on this phone opens these pages too."""
import logging
from datetime import datetime, time, timedelta

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live import page_cache, tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live.controllers.vendor_space import SESSION_LOGIN
from odoo.addons.ocd_live_shop.controllers.member_space import OcdMemberLogin
from odoo.addons.payment.controllers.portal import PaymentPortal

_logger = logging.getLogger(__name__)

SESSION_SENDER = "ocd_express_sender_id"
SESSION_SENDER_TOKEN = "ocd_express_sender_token"
SESSION_MOMO = "ocd_express_new_momo"
SENDER_COOKIE = "ocd_express"
HOME = "/express/envois"
LOGIN = "/express/connexion"
TABS = {"en_cours": "open", "livres": "done", "problemes": "problem", "retournes": "returned"}
OPEN = ("to_prepare", "ready", "picked", "on_the_way")

page_cache.PERSONAL_COOKIES.add(SENDER_COOKIE)


def _is_sender(partner):
    return bool(partner) and partner.ocd_express_state in ("active", "suspended")


def current_sender():
    """The sender opened on this browser (a code checked), or the vendor of OCD Live logged in
    on it whose account of OCD Express is open."""
    Partner = request.env["res.partner"].sudo()
    partner_id = request.session.get(SESSION_SENDER)
    if partner_id:
        partner = Partner.browse(partner_id).exists()
        token = request.session.get(SESSION_SENDER_TOKEN) or ""
        if _is_sender(partner) and partner.ocd_space_token and consteq(partner.ocd_space_token, token):
            return partner
        forget_sender()
    else:
        partner = common.browser_partner(SENDER_COOKIE, "express")
        if _is_sender(partner):
            remember_sender(partner)
            return partner
    vendor = common.current_vendor()
    return vendor if _is_sender(vendor) else Partner


def remember_sender(partner):
    request.session[SESSION_SENDER] = partner.id
    request.session[SESSION_SENDER_TOKEN] = partner._ocd_get_space_token()
    common.remember_browser(SENDER_COOKIE, partner, "express")


def forget_sender():
    request.session.pop(SESSION_SENDER, None)
    request.session.pop(SESSION_SENDER_TOKEN, None)
    common.forget_browser(SENDER_COOKIE)


def money(amount):
    return common.money(amount, common.company().currency_id)


def rate_text(rate):
    """« 1,5 » in French, « 1.5 » in English."""
    point = request.env["res.lang"]._get_data(code=request.env.lang or "en_US").decimal_point or "."
    return f"{rate:g}".replace(".", point)


def today_start():
    """The start of the day of the studio, in UTC as stored."""
    company = common.company()
    local = company._ocd_tz().localize(datetime.combine(company._ocd_local_today(), time()))
    return company._ocd_to_utc(local)


class OcdExpressLogin(OcdMemberLogin):
    """The login of the senders: their number, then a code on WhatsApp."""

    LOGIN_PAGES = dict(OcdMemberLogin.LOGIN_PAGES, express={"form": LOGIN, "code": "/express/code", "home": HOME})

    def _login_page_mode(self, target):
        if target == "express":
            return "whatsapp_code"
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        if target == "express":
            return request.env["res.partner"].sudo()._ocd_find_by_phone(
                number, [("ocd_express_state", "in", ("active", "suspended"))])
        return super()._ocd_login_partner(number, target)

    def _ocd_open_session(self, partner, target):
        if target == "express":
            remember_sender(partner)
            return HOME
        return super()._ocd_open_session(partner, target)

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def express_login(self, **kwargs):
        if current_sender():
            return request.redirect(HOME)
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="express")

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def express_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "express")

    @http.route("/express/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def express_login_code(self, code=None, **kwargs):
        return self._login_code(code, "express")

    @http.route("/express/deconnexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def express_logout_page(self, **kwargs):
        return request.redirect(HOME)

    @http.route("/express/deconnexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def express_logout(self, **kwargs):
        forget_sender()
        return request.redirect(LOGIN)

    # === THE REQUEST === #

    @http.route("/express/demande", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def express_request(self, **kwargs):
        sender = current_sender()
        if sender and sender.ocd_express_state == "active":
            return request.redirect(HOME)
        return self._render_request()

    def _render_request(self, values=None, error=None):
        vendor = common.current_vendor()
        values = values or {}
        country = common.default_country()
        return request.render("ocd_express.request_page", common.page_values(
            False,
            back="/express",
            values=values,
            error=error,
            vendor=vendor,
            districts=OcdExpressSender._districts(),
            dial_rows=common.dial_rows(values.get("country") or country),
            phone_value=values.get("phone_typed") or "",
            open_to_all=common.company().ocd_express_open_to == "all",
        ))

    @http.route("/express/demande", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def express_request_post(self, **post):
        env = request.env
        vendor = common.current_vendor()
        country = env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists() or common.default_country()
        name = common.clean_text(post.get("name"), 60) or (vendor.name if vendor else "")
        values = {
            "name": name, "phone_typed": post.get("phone") or "", "country": country,
            "district_id": int(post.get("district_id") or 0), "landmark": common.clean_text(post.get("landmark"), 120),
            "social": common.clean_text(post.get("social"), 80),
        }
        phone = vendor.phone if vendor and not post.get("phone") else common.normalize_phone(country, post.get("phone"))
        district = env["res.city.district"].sudo().browse(values["district_id"]).exists()
        if not name:
            return self._render_request(values, env._("Write your name or the name of your shop."))
        if not phone:
            return self._render_request(values, common.phone_error(country))
        if not district:
            return self._render_request(values, env._("Choose the district where the courier picks your parcels up."))
        sender = env["res.partner"].sudo()._ocd_express_request(
            name, phone, country, district, values["landmark"], values["social"], vendor=vendor or None)
        if sender.ocd_express_state == "active" and not vendor:
            # Open to all: the number is checked by the code, then the space opens
            sender._ocd_send_login_code()
            request.session[SESSION_LOGIN] = sender.id
            return self._render_code(target="express")
        if sender.ocd_express_state == "active":
            return request.redirect(HOME)
        return request.render("ocd_express.request_done", common.page_values(False, back="/express", sender=sender))


class OcdExpressSender(http.Controller):

    # === HELPERS === #

    @staticmethod
    def _districts():
        """The districts of the cities open to OCD Express, by city."""
        cities = common.company().ocd_express_city_ids
        return request.env["res.city.district"].sudo().search([("city_id", "in", cities.ids)], order="city_id, name")

    @staticmethod
    def _other_cities():
        """The other cities of the country, by travel agency."""
        company = common.company()
        return request.env["res.city"].sudo().search([
            ("country_id", "=", company.country_id.id), ("id", "not in", company.ocd_express_city_ids.ids),
        ], order="name")

    def _sender(self):
        sender = current_sender()
        if not sender:
            return None, request.redirect(LOGIN)
        request._ocd_viewer_tz = common.viewer_tz(sender)
        return sender, None

    def _page(self, template, sender, **values):
        return request.render(template, common.page_values(
            False,
            nav="me",
            sender=sender,
            header_link={"href": "/express/deconnexion", "post": True, "label": request.env._("Log out")}
            if not common.current_vendor() else common.vendor_header_link(common.current_vendor_and_source()[1]),
            **values,
        ))

    def _parcel(self, sender, picking_id):
        parcel = request.env["stock.picking"].sudo().browse(picking_id).exists()
        if not parcel or not parcel.ocd_express or parcel.ocd_express_sender_id != sender:
            raise request.not_found()
        return parcel

    def _part_text(self, day, part):
        """« this afternoon », « tomorrow morning », « Thursday 26 Nov., in the morning »."""
        env = request.env
        today = common.company()._ocd_local_today()
        if day == today:
            return {"morning": env._("this morning"), "afternoon": env._("this afternoon"),
                    "evening": env._("this evening")}.get(part, "")
        if day == today + timedelta(days=1):
            return {"morning": env._("tomorrow morning"), "afternoon": env._("tomorrow afternoon"),
                    "evening": env._("tomorrow evening")}.get(part, "")
        parts = {"morning": env._("in the morning"), "afternoon": env._("in the afternoon"),
                 "evening": env._("in the evening")}
        return env._("%(day)s, %(part)s", day=common.day_text(day, "EEEE d MMM"), part=parts.get(part, ""))

    def _pickup_line(self, parcel):
        """When the courier takes the parcel."""
        env = request.env
        if parcel.ocd_express_check == "to_check":
            return env._("The team checks it before it leaves: %s", parcel.ocd_express_check_reason or "")
        if parcel.ocd_express_dropoff:
            return env._("To drop at the OCD point: %s", common.company().ocd_express_point or env._("the studio"))
        pickup = parcel.ocd_express_pickup_id
        if not pickup:
            return ""
        courier = (pickup.courier_id.name or "").split(" ")[0]
        when = self._part_text(pickup.date, pickup.part)
        if courier:
            return env._("%(courier)s picks it up %(when)s", courier=courier, when=when)
        return env._("A courier picks it up %s", when)

    def _status(self, parcel):
        """(css, label) of the step of the parcel."""
        env = request.env
        if parcel.ocd_express_return_state == "to_return":
            return "bad", env._("Comes back to you")
        if parcel.ocd_express_return_state == "handed_back":
            return "grey", env._("Given back")
        if parcel.ocd_express_claim_state == "open":
            return "bad", env._("Problem reported")
        if parcel.ocd_express_check == "to_check":
            return "wait", env._("Checked by the team")
        reasons = dict(parcel._fields["ocd_problem_reason"]._description_selection(env))
        return {
            "to_prepare": ("wait", env._("To check")),
            "ready": ("wait", env._("To pick up")),
            "picked": ("route", env._("Picked up")),
            "on_the_way": ("route", env._("On the way")),
            "delivered": ("done", env._("Delivered · code checked")),
            "problem": ("bad", reasons.get(parcel.ocd_problem_reason) or env._("Problem")),
            "returned": ("bad", env._("Returned")),
            "cancelled": ("grey", env._("Cancelled")),
        }.get(parcel.ocd_stage, ("grey", ""))

    def _row(self, parcel):
        env = request.env
        css, label = self._status(parcel)
        customer = parcel.partner_id
        place = customer.district_id.name or customer.city_id.name or ""
        if parcel.ocd_cod_state == "none":
            amount = env._("already paid")
        elif parcel.ocd_stage == "delivered" and parcel.ocd_cod_collected_amount:
            amount = env._("%(amount)s collected at %(hour)s", amount=money(parcel.ocd_cod_collected_amount),
                           hour=common.to_viewer(parcel.ocd_delivered_at).strftime("%H:%M") if parcel.ocd_delivered_at else "")
        else:
            amount = env._("to collect %s", money(parcel.ocd_cod_amount))
        detail = ""
        if parcel.ocd_stage in ("ready", "to_prepare"):
            detail = self._pickup_line(parcel)
        elif parcel.ocd_stage == "problem":
            detail = env._(
                "After %(count)s passages, the parcel comes back to you.",
                count=parcel.company_id.ocd_max_failed_attempts or 2)
            if parcel.ocd_express_confirm == "moved" and parcel.ocd_express_deliver_on:
                detail = env._("%(customer)s chose %(when)s for the second passage (free).",
                               customer=(customer.name or "").split(" ")[0],
                               when=self._part_text(parcel.ocd_express_deliver_on, parcel.ocd_express_deliver_part))
        elif parcel.ocd_express_return_state == "to_return":
            detail = env._("Give the courier your return code: %s", parcel._ocd_express_return_code())
        elif parcel.ocd_express_not_taken and parcel.ocd_stage == "ready":
            detail = env._("Not taken: %s", parcel.ocd_express_not_taken)
        steps = []
        order = ["created", "picked", "on_the_way", "delivered"]
        reached = {"to_prepare": 0, "ready": 0, "picked": 1, "on_the_way": 2, "problem": 2, "delivered": 3}.get(
            parcel.ocd_stage, -1)
        labels = [env._("Created"), env._("Picked up"), env._("On the way"), env._("Delivered")]
        for index, _key in enumerate(order):
            steps.append({"label": labels[index], "state": "on" if index < reached or (index == reached == 3)
                          else "now" if index == reached else ""})
        return {
            "parcel": parcel,
            "title": f"{parcel.name} · {customer.name}",
            "css": css,
            "label": label,
            "line": " · ".join(part for part in (place, amount, (parcel.ocd_courier_id.name or "").split(" ")[0]
                                                  if parcel.ocd_stage in ("picked", "on_the_way") else "") if part),
            "detail": detail,
            "steps": steps if parcel.ocd_stage in ("ready", "picked", "on_the_way") else [],
            "editable": parcel._ocd_express_editable(),
        }

    # === THE PAGE /express === #

    @http.route("/express", type="http", auth="public", website=True, methods=["GET"], sitemap=True)
    def landing(self, **kwargs):
        company = common.company()
        Rate = request.env["ocd.delivery.rate"].sudo()
        cities = company.ocd_express_city_ids
        rates = Rate._ocd_rates(company).filtered(lambda r: not r.vendor_id)
        city = cities[:1]
        local = rates.filtered(lambda r: r.operator == "courier" and (not r.city_ids or city in r.city_ids))[:1]
        agency = rates.filtered(lambda r: r.operator == "agency").sorted("price")[:1]
        env = request.env
        prices = []
        if local:
            prices.append((env._("Delivery in %s", city.name), money(local.price)))
        prices.append((env._("Collecting at the door"), env._(
            "%(rate)s %% · %(min)s at least", rate=rate_text(company.ocd_express_cod_rate),
            min=money(company.ocd_express_cod_min))))
        prices.append((env._("Parcel already paid by your customer"), env._("nothing more")))
        if company.ocd_express_pickup_fee and company.ocd_express_pickup_free_from > 1:
            prices.append((env._("Pick-up, from %s parcels", company.ocd_express_pickup_free_from), env._("no charge")))
            prices.append((env._("Pick-up of fewer parcels"), money(company.ocd_express_pickup_fee)))
        else:
            prices.append((env._("Pick-up at your place"), env._("no charge")))
        if company.ocd_express_return_fee:
            prices.append((env._("Return of a parcel"), money(company.ocd_express_return_fee)))
        if agency:
            prices.append((env._("Towards another city (travel agency)"), env._("from %s", money(agency.price))))
        return request.render("ocd_express.landing_page", common.page_values(
            False,
            back="/ocd",
            sender=current_sender(),
            prices_title=env._("The prices in %s", city.name) if city else env._("The prices"),
            prices=prices,
            open_to_all=company.ocd_express_open_to == "all",
        ))

    # === MY PARCELS === #

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def parcels(self, vue=None, **kwargs):
        sender, answer = self._sender()
        if answer:
            return answer
        env = request.env
        Picking = env["stock.picking"].sudo()
        base = [("ocd_express", "=", True), ("ocd_express_sender_id", "=", sender.id)]
        tab = TABS.get(vue, "open")
        domains = {
            "open": [("ocd_stage", "in", OPEN)],
            "done": [("ocd_stage", "=", "delivered")],
            "problem": ["|", ("ocd_stage", "=", "problem"), "|", ("ocd_express_claim_state", "=", "open"),
                        ("ocd_express_return_state", "=", "to_return")],
            "returned": ["|", ("ocd_stage", "=", "returned"), ("ocd_stage", "=", "cancelled")],
        }
        counts = {key: Picking.search_count(base + domain) for key, domain in domains.items()}
        parcels = Picking.search(base + domains[tab], order="create_date desc, id desc", limit=50)
        start = today_start()
        today = Picking.search(base + [("create_date", ">=", start)])
        delivered_today = Picking.search(base + [("ocd_delivered_at", ">=", start)])
        collected = sum(delivered_today.mapped("ocd_cod_collected_amount"))
        tabs = [
            ("en_cours", "open", env._("In progress · %s", counts["open"])),
            ("livres", "done", env._("Delivered · %s", counts["done"])),
            ("problemes", "problem", env._("Problems · %s", counts["problem"])),
            ("retournes", "returned", env._("Returned and cancelled")),
        ]
        return self._page(
            "ocd_express.sender_parcels", sender,
            back="/express",
            rows=[self._row(parcel) for parcel in parcels],
            tabs=tabs, tab=tab,
            today_label=env._("%s parcels", len(today)) if len(today) != 1 else env._("1 parcel"),
            today_line=env._("%(delivered)s delivered · %(route)s on the way",
                             delivered=len(delivered_today),
                             route=len(today.filtered(lambda p: p.ocd_stage == "on_the_way"))),
            collected=money(collected),
            suspended=sender.ocd_express_state == "suspended",
        )

    # === NEW PARCEL === #

    def _form_values(self, sender, parcel=None, data=None):
        env = request.env
        country = common.default_country()
        values = dict(data or {})
        if parcel and not data:
            customer = parcel.partner_id
            values = {
                "name": customer.name, "phone": common.local_digits(country, customer.phone),
                "district_id": customer.district_id.id, "city_id": customer.city_id.id,
                "landmark": customer.delivery_landmark or "", "content": parcel.ocd_express_content,
                "prepaid": parcel.ocd_cod_state == "none" or not parcel.ocd_goods_amount,
                "amount": int(parcel.ocd_goods_amount) if parcel.ocd_goods_amount else "",
                "value": int(parcel.ocd_express_value) if parcel.ocd_express_value else "",
                "fee_by": parcel.ocd_express_fee_by, "can_open": parcel.ocd_express_can_open,
                "consent": True, "dropoff": parcel.ocd_express_dropoff,
            }
        company = common.company()
        slot = company._ocd_express_plan()
        return {
            "values": values,
            "parcel": parcel,
            "districts": self._districts(),
            "other_cities": self._other_cities(),
            "dial_rows": common.dial_rows(country),
            "phone_value": values.get("phone") or "",
            "currency": company.currency_id,
            "fee": self._local_fee(sender),
            "cod_rate": company.ocd_express_cod_rate,
            "cod_min": company.ocd_express_cod_min,
            "max_cod": sender.ocd_express_max_cod,
            "slot_line": env._(
                "Created now: picked up %(pickup)s, delivered %(deliver)s.",
                pickup=self._part_text(slot[0], slot[1]), deliver=self._part_text(slot[2], slot[3])),
            "point": company.ocd_express_point or "",
            "debt": sender._ocd_express_debt(),
            "debt_over": company.ocd_express_debt_max and sender._ocd_express_debt() > company.ocd_express_debt_max,
            "place_line": " · ".join(part for part in (sender.district_id.name, sender.delivery_landmark) if part),
            "change_title": env._("Change %s", parcel.name) if parcel else "",
            "max_line": env._("At most %s per parcel; above, the team checks it first.", money(sender.ocd_express_max_cod)),
            "point_line": env._("OCD point: %s", company.ocd_express_point) if company.ocd_express_point else "",
        }

    def _local_fee(self, sender):
        company = common.company()
        Rate = request.env["ocd.delivery.rate"].sudo()
        city = sender.city_id or sender.district_id.city_id or company.ocd_express_city_ids[:1]
        rate = Rate._ocd_rates(company).filtered(
            lambda r: not r.vendor_id and r.operator == "courier" and (not r.city_ids or city in r.city_ids))[:1]
        return rate.price if rate else 0.0

    def _read_form(self, post):
        env = request.env
        country = common.default_country()
        District = env["res.city.district"].sudo()
        City = env["res.city"].sudo()
        place = post.get("place") or ""
        district = District.browse(int(place[1:])).exists() if place.startswith("d") and place[1:].isdigit() else District
        city = City.browse(int(place[1:])).exists() if place.startswith("c") and place[1:].isdigit() else City

        def amount(key):
            raw = (post.get(key) or "").replace(" ", "").replace(" ", "").replace(".", "").replace(",", "")
            raw = raw.upper().removesuffix("F").removesuffix("FCFA").strip()
            if not raw:
                return 0.0
            if not raw.isdigit():
                raise UserError(env._("Type the amount in figures, e.g. 15000."))
            return float(raw)

        phone_country = env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists() or country
        phone = common.normalize_phone(phone_country, post.get("phone"))
        data = {
            "name": common.clean_text(post.get("name"), 60),
            "phone_typed": post.get("phone") or "",
            "phone": phone,
            "district": district,
            "city": city,
            "district_id": district.id,
            "city_id": city.id,
            "landmark": common.clean_text(post.get("landmark"), 120),
            "content": common.clean_text(post.get("content"), 120),
            "prepaid": post.get("prepaid") == "1",
            "fee_by": "customer" if post.get("fee_by") == "customer" else "sender",
            "can_open": bool(post.get("can_open")),
            "consent": bool(post.get("consent")),
            "dropoff": post.get("dropoff") == "1",
        }
        data["amount"] = amount("amount")
        data["value"] = amount("value")
        if post.get("phone") and not phone:
            raise UserError(common.phone_error(phone_country))
        return data

    @http.route("/express/colis/nouveau", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def new_parcel(self, **kwargs):
        sender, answer = self._sender()
        if answer:
            return answer
        if sender.ocd_express_state != "active":
            return request.redirect(HOME)
        return self._page("ocd_express.sender_form", sender, back=HOME,
                          **self._form_values(sender, data={"can_open": True, "consent": False}))

    @http.route("/express/colis/nouveau", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def new_parcel_post(self, **post):
        sender, answer = self._sender()
        if answer:
            return answer
        data = {}
        try:
            data = self._read_form(post)
            parcel = request.env["stock.picking"].sudo()._ocd_express_create(sender, data)
        except UserError as exc:
            return self._page("ocd_express.sender_form", sender, back=HOME, error=exc.args[0],
                              **self._form_values(sender, data=data or self._safe_form(post)))
        return request.redirect(f"/express/colis/{parcel.id}?cree=1")

    def _safe_form(self, post):
        return {key: post.get(key) for key in ("name", "landmark", "content", "amount", "value", "fee_by")} | {
            "phone": post.get("phone"), "prepaid": post.get("prepaid") == "1", "can_open": bool(post.get("can_open")),
            "consent": bool(post.get("consent")), "dropoff": post.get("dropoff") == "1",
        }

    @http.route("/express/colis/<int:picking_id>/modifier", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def edit_parcel(self, picking_id, **kwargs):
        sender, answer = self._sender()
        if answer:
            return answer
        parcel = self._parcel(sender, picking_id)
        if not parcel._ocd_express_editable():
            return request.redirect(f"/express/colis/{parcel.id}")
        return self._page("ocd_express.sender_form", sender, back=f"/express/colis/{parcel.id}",
                          **self._form_values(sender, parcel=parcel))

    @http.route("/express/colis/<int:picking_id>/modifier", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def edit_parcel_post(self, picking_id, **post):
        sender, answer = self._sender()
        if answer:
            return answer
        parcel = self._parcel(sender, picking_id)
        data = {}
        try:
            data = self._read_form(post)
            parcel._ocd_express_update(data)
        except UserError as exc:
            return self._page("ocd_express.sender_form", sender, back=f"/express/colis/{parcel.id}",
                              error=exc.args[0], **self._form_values(sender, parcel=parcel,
                                                                     data=data or self._safe_form(post)))
        return request.redirect(f"/express/colis/{parcel.id}")

    @http.route("/express/colis/<int:picking_id>/annuler", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def cancel_parcel(self, picking_id, **post):
        sender, answer = self._sender()
        if answer:
            return answer
        parcel = self._parcel(sender, picking_id)
        try:
            parcel._ocd_express_cancel_by_sender()
        except UserError as exc:
            return self._render_parcel(sender, parcel, error=exc.args[0])
        return request.redirect(HOME)

    def _render_parcel(self, sender, parcel, error=None, created=False, template="ocd_express.sender_parcel"):
        env = request.env
        url = parcel._ocd_express_tracking_url()
        customer = parcel.partner_id
        first = (customer.name or "").split(" ")[0]
        share = env._("Hello %(name)s, follow your parcel of %(sender)s here: %(url)s",
                      name=first, sender=sender.name, url=url)
        place = " · ".join(part for part in (customer.district_id.name or customer.city_id.name,
                                             customer.delivery_landmark) if part)
        return self._page(
            template, sender,
            back=HOME,
            title=env._("%(parcel)s · for %(customer)s", parcel=parcel.name, customer=customer.name),
            place=place,
            from_line=env._("From %s · OCD Express", sender.name),
            write_line=env._("Write %(parcel)s and the name of %(customer)s on the parcel, or show this label to the "
                             "courier: they scan it.", parcel=parcel.name, customer=first),
            told_line=env._("%s is told on WhatsApp", first),
            share_label=env._("Share the tracking with %s", first),
            row=self._row(parcel),
            parcel=parcel,
            customer=customer,
            error=error,
            created=created,
            qr=tools.qr_data_uri(parcel.name, box_size=6),
            pickup_line=self._pickup_line(parcel),
            share_url=tools.whatsapp_url(customer.phone, share),
            amount_label=env._("To collect: %s", money(parcel.ocd_cod_amount)) if parcel.ocd_cod_state != "none"
            else env._("Already paid"),
            return_code=parcel._ocd_express_return_code() if parcel.ocd_express_return_state == "to_return" else "",
            first_name=first,
        )

    @http.route("/express/colis/<int:picking_id>", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def parcel_page(self, picking_id, cree=None, **kwargs):
        sender, answer = self._sender()
        if answer:
            return answer
        return self._render_parcel(sender, self._parcel(sender, picking_id), created=bool(cree))

    @http.route("/express/colis/<int:picking_id>/etiquette", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def parcel_label(self, picking_id, **kwargs):
        sender, answer = self._sender()
        if answer:
            return answer
        return self._render_parcel(sender, self._parcel(sender, picking_id), template="ocd_express.sender_label")

    # === MY MONEY === #

    @http.route("/express/argent", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def money_page(self, **kwargs):
        sender, answer = self._sender()
        if answer:
            return answer
        return self._render_money(sender)

    def _render_money(self, sender, message=None, error=None, ask_code=False):
        env = request.env
        Move = env["account.move"].sudo()
        moves = Move.search([
            ("partner_id", "=", sender.id), ("ocd_express_kind", "!=", False), ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
        ], order="id")
        held = moves.filtered(lambda m: m.ocd_picking_id.ocd_express_claim_state == "open")
        lines = {}
        labels = {
            "collected": env._("Collected for you"),
            "fees": env._("Deliveries and collecting"),
            "return": env._("Returns"),
            "pickup": env._("Pick-ups"),
            "claim": env._("Paid back to your customers"),
            "lost": env._("Lost or damaged by OCD, paid back"),
            "debt_paid": env._("Paid by you"),
        }
        for move in moves - held:
            sign = 1 if move.move_type == "in_invoice" else -1
            row = lines.setdefault(move.ocd_express_kind, {"label": labels.get(move.ocd_express_kind), "amount": 0.0,
                                                           "count": 0})
            row["amount"] += sign * move.amount_residual
            row["count"] += 1
        total = sum(row["amount"] for row in lines.values())
        waiting = env["stock.picking"].sudo().search([
            ("ocd_express", "=", True), ("ocd_express_sender_id", "=", sender.id), ("ocd_stage", "=", "delivered"),
            ("ocd_cod_state", "=", "collected"), ("ocd_cod_method", "=", "cash"),
        ])
        payouts = env["ocd.payout"].sudo().search([("vendor_id", "=", sender.id), ("state", "=", "paid")],
                                                    order="date desc, id desc", limit=10)
        company = common.company()
        next_day = company._ocd_express_next_working_day(company._ocd_local_today())
        debt = max(-total, 0.0)
        momo = sender.ocd_payout_momo or ""
        day = common.day_text(next_day, "EEEE d MMMM")
        new_momo = request.session.get(SESSION_MOMO) or ""
        return self._page(
            "ocd_express.sender_money", sender,
            back=HOME,
            message=message, error=error,
            total=money(max(total, 0.0)),
            positive=total > 0,
            debt=money(debt) if debt else "",
            debt_over=bool(company.ocd_express_debt_max) and debt > company.ocd_express_debt_max,
            rows=[{"label": row["label"], "amount": money(row["amount"])} for row in lines.values()],
            held=[{"label": env._("%(parcel)s · problem reported · %(amount)s", parcel=move.ocd_picking_id.name,
                                  amount=money(move.amount_residual if move.move_type == "in_invoice"
                                               else -move.amount_residual))}
                  for move in held],
            waiting=env._("On its way to OCD: %s", money(sum(waiting.mapped("ocd_cod_collected_amount"))))
            if waiting else "",
            next_day=common.day_text(next_day, "EEEE d MMMM"),
            momo=sender.ocd_payout_momo or "",
            held_momo=sender._ocd_express_momo_held(),
            payouts=[{"label": " · ".join(part for part in (common.day_text(payout.date, "EEEE d MMMM", capital=True),
                                                             payout.payment_reference) if part),
                      "amount": money(payout.amount)} for payout in payouts],
            ask_code=ask_code,
            paid_line=env._("Paid on %(day)s · %(number)s", day=day, number=momo) if momo
            else env._("Paid on %s", day),
            send_line=env._("Or send it to the Mobile Money of OCD %(number)s with the reference %(ref)s: the team "
                            "notes it.", number=company.ocd_express_momo_number, ref=f"EXD-{sender.id}")
            if company.ocd_express_momo_number else "",
            code_label=env._("Code received on WhatsApp for %s", new_momo),
            number_label=env._("Mobile Money number (now %s)", momo) if momo else env._("Mobile Money number"),
            dial_rows=common.dial_rows(common.default_country()),
            phone_value="",
            ocd_momo=company.ocd_express_momo_number or "",
            reference=f"EXD-{sender.id}",
            can_pay_online=bool(debt) and bool(self._providers(debt)),
        )

    @http.route("/express/argent/numero", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def money_number(self, phone=None, country_id=None, code=None, **post):
        """Change the payout number: a code on the WhatsApp of the sender first."""
        sender, answer = self._sender()
        if answer:
            return answer
        env = request.env
        if code is not None:
            number = request.session.get(SESSION_MOMO)
            if not number or not sender._ocd_check_login_code(code):
                return self._render_money(sender, error=env._("Wrong or expired code. Ask for a new code."),
                                          ask_code=bool(number))
            request.session.pop(SESSION_MOMO, None)
            sender.sudo().ocd_payout_momo = number
            return self._render_money(sender, message=env._("Payout number changed: %s.", number))
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return self._render_money(sender, error=common.phone_error(country))
        request.session[SESSION_MOMO] = number
        sender._ocd_send_login_code()
        return self._render_money(sender, message=env._("A code arrives on your WhatsApp: type it to confirm."),
                                  ask_code=True)

    def _providers(self, amount):
        company = common.company()
        return request.env["payment.provider"].sudo()._find_available_providers(
            company.id, current_sender().id, amount, currency_id=company.currency_id.id)


class OcdExpressDebtPayment(PaymentPortal):
    """A sender pays what they owe on their phone: the payment form of OCD Live."""

    @http.route("/express/argent/regler", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def pay_debt(self, **kwargs):
        sender = current_sender()
        if not sender:
            return request.redirect(LOGIN)
        debt = sender._ocd_express_debt()
        env = request.env
        company = common.company()
        values = {"sender": sender, "debt": debt, "total": money(debt), "state": "done" if not debt else "form",
                  "back": "/express/argent"}
        if debt:
            values.update(self._prepare_payment_form_values(
                company.id, sender.id, debt, currency_id=company.currency_id.id))
            values.update({
                "amount": debt,
                "currency": company.currency_id,
                "partner_id": sender.id,
                "transaction_route": "/express/argent/transaction",
                "landing_route": "/express/argent",
                "submit_button_label": env._("Pay %s", money(debt)),
                "show_amount_input": False,
            })
        return request.render("ocd_express.sender_pay", common.page_values(False, **values))

    @http.route("/express/argent/transaction", type="jsonrpc", auth="public")
    def pay_debt_transaction(self, **kwargs):
        sender = current_sender()
        if not sender:
            raise ValidationError(request.env._("Log in again."))
        debt = sender._ocd_express_debt()
        if not debt:
            raise ValidationError(request.env._("You owe nothing to OCD."))
        self._validate_transaction_kwargs(kwargs)
        kwargs.update({"amount": debt, "currency_id": common.company().currency_id.id, "partner_id": sender.id})
        transaction = self._create_transaction(custom_create_values={"ocd_express_debt_partner_id": sender.id}, **kwargs)
        return transaction._get_processing_values()
