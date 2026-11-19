"""The relay points (chantier 10, design PointsRelais): « My relay point » for the one who holds
it, and the page where a shop asks to become one.

The holder of a relay point logs in with their WhatsApp number and a code, like the senders of OCD
Express (a vendor whose store is a relay point finds it from their space). Their page: the parcels
kept on its places, the parcels on the way with the courier (counted one by one when they arrive, a
parcel damaged or open refused with a note), the parcels to give back to the courier, « Hand over a
parcel » (the QR of the customer read by the camera, or the parcel chosen and the code typed; paid
on the phone of the customer at the counter, never in cash), the earnings of the month, « On
holiday »."""
from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live import page_cache, tools
from odoo.addons.ocd_live.controllers import common

from .member_space import OcdMemberLogin

SESSION_RELAY = "ocd_relay_partner_id"
SESSION_RELAY_TOKEN = "ocd_relay_token"
RELAY_COOKIE = "ocd_relay"
HOME = "/ocd/point-relais"
LOGIN = "/ocd/point-relais/connexion"
BECOME = "/points-relais"

page_cache.PERSONAL_COOKIES.add(RELAY_COOKIE)


def _holds(partner):
    return bool(partner) and (partner.ocd_is_relay or (partner.ocd_is_vendor and bool(partner._ocd_relay_places())))


def current_relay_holder():
    """The holder of a relay point opened on this browser (a code checked), or the vendor of OCD
    Live opened on it whose store is a relay point."""
    Partner = request.env["res.partner"].sudo()
    partner_id = request.session.get(SESSION_RELAY)
    if partner_id:
        partner = Partner.browse(partner_id).exists()
        token = request.session.get(SESSION_RELAY_TOKEN) or ""
        if _holds(partner) and partner.ocd_space_token and consteq(partner.ocd_space_token, token):
            return partner
        forget_relay_holder()
    else:
        partner = common.browser_partner(RELAY_COOKIE, "relais")
        if _holds(partner):
            remember_relay_holder(partner)
            return partner
    vendor = common.current_vendor()
    return vendor if _holds(vendor) else Partner


def remember_relay_holder(partner):
    request.session[SESSION_RELAY] = partner.id
    request.session[SESSION_RELAY_TOKEN] = partner._ocd_get_space_token()
    common.remember_browser(RELAY_COOKIE, partner, "relais")


def forget_relay_holder():
    request.session.pop(SESSION_RELAY, None)
    request.session.pop(SESSION_RELAY_TOKEN, None)
    common.forget_browser(RELAY_COOKIE)


class OcdRelayLogin(OcdMemberLogin):
    """The login of the relay points: their number, then a code on WhatsApp."""

    LOGIN_PAGES = dict(OcdMemberLogin.LOGIN_PAGES, relais={"form": LOGIN, "code": "/ocd/point-relais/code", "home": HOME})

    def _login_page_mode(self, target):
        if target == "relais":
            return "whatsapp_code"
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        if target == "relais":
            return request.env["res.partner"].sudo()._ocd_find_relay_by_phone(number)
        return super()._ocd_login_partner(number, target)

    def _ocd_open_session(self, partner, target):
        if target == "relais":
            remember_relay_holder(partner)
            return HOME
        return super()._ocd_open_session(partner, target)

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def relay_login(self, **kwargs):
        if current_relay_holder():
            return request.redirect(HOME)
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="relais")

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def relay_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "relais")

    @http.route("/ocd/point-relais/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def relay_login_code(self, code=None, **kwargs):
        return self._login_code(code, "relais")

    @http.route("/ocd/point-relais/deconnexion", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def relay_logout_page(self, **kwargs):
        """A link loaded in advance by the browser logs nobody out (« Log out » is a form)."""
        return request.redirect(HOME)

    @http.route("/ocd/point-relais/deconnexion", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def relay_logout(self, **kwargs):
        forget_relay_holder()
        return request.redirect(LOGIN)


class OcdRelaySpace(http.Controller):
    """« My relay point »: its parcels, receiving them, handing them over."""

    def _relay(self, place_id=None):
        """(holder, relay point) of the visitor, or (None, the answer to give)."""
        holder = current_relay_holder()
        if not holder:
            return None, request.redirect(LOGIN)
        places = holder._ocd_relay_places()
        if not places:
            return None, request.redirect(LOGIN)
        place = places.filtered(lambda p: p.id == int(place_id)) if str(place_id or "").isdigit() else places
        common.viewer_tz(holder)
        return holder, place[:1] or places[:1]

    def _page(self, holder, place, **values):
        env = request.env
        return common.page_values(
            False,
            nav="me",
            header_link={"href": "/ocd/point-relais/deconnexion", "post": True, "label": env._("Log out")},
            holder=holder,
            relay=place,
            **values,
        )

    def _customer(self, parcel):
        """« Estelle N. »: the first name and the initial of the customer."""
        words = (parcel.partner_id.name or "").split()
        if not words:
            return ""
        return f"{words[0]} {words[1][:1]}." if len(words) > 1 else words[0]

    def _row(self, parcel):
        env = request.env
        to_pay = parcel.ocd_cod_state == "to_collect"
        amount = common.money(parcel.ocd_cod_amount, parcel.ocd_currency_id)
        deadline = parcel.ocd_relay_deadline
        last_day = bool(deadline) and common.to_viewer(deadline).date() == common.to_viewer(fields.Datetime.now()).date()
        if parcel.ocd_relay_back:
            pill, pill_label = "problem", env._("To give back")
            line = env._("Not picked up in time: the courier takes it back")
        elif parcel.ocd_stage == "on_the_way":
            pill, pill_label = "route", env._("On the way")
            line = env._("With %s", (parcel.ocd_courier_id.name or "").split(" ")[0] or "-")
        elif last_day:
            pill, pill_label = "problem", env._("Last day")
            line = env._("Until %s", parcel._ocd_relay_deadline_text())
        else:
            pill, pill_label = ("prep", env._("To pay %s", amount)) if to_pay else ("done", env._("Paid"))
            line = env._("Until %s", parcel._ocd_relay_deadline_text()) if deadline else ""
        return {
            "parcel": parcel,
            "title": " · ".join(part for part in (parcel.sale_id.name or parcel.name, self._customer(parcel)) if part),
            "line": line,
            "pill": pill,
            "pill_label": pill_label,
            "last_day": last_day,
        }

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def relay_home(self, lieu=None, vue=None, message=None, **kwargs):
        holder, place = self._relay(lieu)
        if holder is None:
            return place
        return self._render_home(holder, place, vue=vue)

    def _render_home(self, holder, place, vue=None, message=None, error=None):
        env = request.env
        company = place.company_id
        held = place._ocd_relay_parcels("held")
        coming = place._ocd_relay_parcels("coming")
        back = place._ocd_relay_parcels("back")
        capacity = place.relay_capacity or company.ocd_relay_capacity or 1
        kept = len(held) + len(back)
        tab = vue if vue in ("garde", "recevoir", "rendre") else "garde"
        rows = {"garde": held, "recevoir": coming, "rendre": back}[tab]
        couriers = coming.ocd_courier_id
        if place.relay_pause_note:
            state, state_label = "problem", env._("Paused by the team")
        elif not place.relay_open:
            state, state_label = "prep", env._("On holiday")
        else:
            state, state_label = "done", place._ocd_open_state()["label"] or env._("Open")
        given = env["stock.picking"].sudo().search_count([
            ("ocd_relay_id", "=", place.id), ("ocd_stage", "=", "delivered"),
            ("ocd_delivered_at", ">=", place._ocd_month_start_utc()),
        ])
        return request.render("ocd_live_shop.relay_home", self._page(
            holder, place,
            header_name=env._("My relay point"),
            places=holder._ocd_relay_places(),
            state=state,
            state_label=state_label,
            intro=" · ".join(part for part in (place.name, place._ocd_area()) if part),
            kept_label=env._("%s parcels", kept) if kept != 1 else env._("1 parcel"),
            kept_line=env._("on %s places", capacity),
            kept_percent=min(100, round(100 * kept / capacity)),
            month_amount=common.money(place.relay_month_amount, company.currency_id),
            month_line=env._("%(count)s parcels handed over · %(fee)s each", count=given,
                             fee=common.money(company.ocd_relay_fee, company.currency_id)),
            coming_title=env._("%s arrives with your parcels", (couriers[:1].name or "").split(" ")[0])
            if couriers else "",
            coming_line=(env._("%s parcels", len(coming)) if len(coming) != 1 else env._("1 parcel")) if coming else "",
            tab=tab,
            tabs=[
                {"key": "garde", "label": env._("Kept · %s", len(held))},
                {"key": "recevoir", "label": env._("To receive · %s", len(coming))},
                {"key": "rendre", "label": env._("To give back · %s", len(back))},
            ],
            rows=[self._row(parcel) for parcel in rows],
            empty=env._("No parcel here."),
            hours=place._ocd_hours_lines(),
            paused_note=place.relay_pause_note or "",
            message=message,
            error=error,
        ))

    @http.route("/ocd/point-relais/conge", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def relay_holiday(self, lieu=None, recevoir=None, **kwargs):
        holder, place = self._relay(lieu)
        if holder is None:
            return place
        env = request.env
        try:
            place._ocd_relay_set_open(recevoir == "1")
        except UserError as exc:
            return self._render_home(holder, place, error=exc.args[0])
        return self._render_home(holder, place, message=env._("Noted: you receive parcels again.") if recevoir == "1"
                                 else env._("Noted: no new parcel until you come back; the parcels kept wait for "
                                            "their customers."))

    # === RECEIVE THE PARCELS OF THE COURIER === #

    @http.route("/ocd/point-relais/recevoir", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def relay_receive_page(self, lieu=None, **kwargs):
        holder, place = self._relay(lieu)
        if holder is None:
            return place
        return self._render_receive(holder, place)

    def _render_receive(self, holder, place, error=None):
        env = request.env
        coming = place._ocd_relay_parcels("coming")
        courier = coming.ocd_courier_id[:1]
        return request.render("ocd_live_shop.relay_receive", self._page(
            holder, place,
            header_name=env._("Receive"),
            back=HOME,
            courier_line=env._("%s, OCD courier", courier.name) if courier else "",
            rows=[{"parcel": parcel, "title": " · ".join(part for part in (
                parcel.sale_id.name or parcel.name, self._customer(parcel)) if part)} for parcel in coming],
            empty=env._("No parcel on the way to your relay point."),
            error=error,
        ))

    @http.route("/ocd/point-relais/recevoir", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def relay_receive(self, lieu=None, **post):
        holder, place = self._relay(lieu)
        if holder is None:
            return place
        env = request.env
        coming = place._ocd_relay_parcels("coming")
        form = request.httprequest.form
        ticked = {int(value) for value in form.getlist("recu") if value.isdigit()}
        damaged = {int(value) for value in form.getlist("abime") if value.isdigit()}
        received = coming.filtered(lambda parcel: parcel.id in ticked or parcel.id in damaged)
        if not received:
            return self._render_receive(holder, place, error=env._("Tick the parcels you counted."))
        refused = {parcel: common.clean_text(post.get(f"note_{parcel.id}"), 200) for parcel in received
                   if parcel.id in damaged}
        try:
            done = place._ocd_relay_receive(received, refused=refused)
        except UserError as exc:
            return self._render_receive(holder, place, error=exc.args[0])
        message = env._("You received %s parcels: each customer is told on WhatsApp.", len(done)) if len(done) != 1 \
            else env._("You received 1 parcel: its customer is told on WhatsApp.")
        if refused:
            message = env._("%(received)s The courier keeps %(count)s parcels damaged or open.",
                            received=message, count=len(refused))
        return self._render_home(holder, place, message=message)

    # === HAND A PARCEL OVER === #

    @http.route("/ocd/point-relais/remettre", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def relay_hand_over_page(self, lieu=None, colis=None, **kwargs):
        holder, place = self._relay(lieu)
        if holder is None:
            return place
        parcel = place._ocd_relay_parcels("held").filtered(lambda p: str(p.id) == str(colis or ""))
        return self._render_hand_over(holder, place, parcel)

    def _render_hand_over(self, holder, place, parcel=None, code="", error=None, message=None):
        env = request.env
        parcel = parcel or env["stock.picking"]
        pay = False
        if parcel and parcel.ocd_cod_state == "to_collect":
            try:
                url = parcel._ocd_payment_url()
                pay = {"url": url, "src": tools.qr_data_uri(url, box_size=8),
                       "label": env._("To pay at the counter: %s", common.money(parcel.ocd_cod_amount,
                                                                                 parcel.ocd_currency_id))}
            except UserError:
                pay = {"url": False, "src": False, "label": env._("To pay: call the team of OCD Live.")}
        return request.render("ocd_live_shop.relay_hand_over", self._page(
            holder, place,
            header_name=env._("Hand a parcel over"),
            back=HOME,
            parcel=parcel,
            parcel_title=" · ".join(part for part in (parcel.sale_id.name or parcel.name, self._customer(parcel))
                                    if part) if parcel else "",
            parcel_line=env._("Arrived %s", tools.day_text(env, common.to_viewer(parcel.ocd_relay_received_at).date(),
                                                           "EEE d MMM")) if parcel and parcel.ocd_relay_received_at
            else "",
            pay=pay,
            paid=bool(parcel) and parcel.ocd_cod_state != "to_collect",
            rows=[self._row(row) for row in place._ocd_relay_parcels("held")],
            code=code,
            error=error,
            message=message,
        ))

    @http.route("/ocd/point-relais/remettre", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def relay_hand_over(self, lieu=None, colis=None, code=None, qr=None, **kwargs):
        holder, place = self._relay(lieu)
        if holder is None:
            return place
        env = request.env
        if qr:
            parcel, code = place._ocd_relay_parcel_by_qr(qr)
            if not parcel:
                return self._render_hand_over(holder, place, error=env._("This QR is not a parcel kept here."))
        else:
            parcel = place._ocd_relay_parcels("held").filtered(lambda p: str(p.id) == str(colis or ""))
            if not parcel:
                return self._render_hand_over(holder, place, error=env._("Choose the parcel."))
        code = (code or "").strip()
        if parcel.ocd_cod_state == "to_collect":
            return self._render_hand_over(holder, place, parcel, code=code,
                                          error=env._("First the payment on the phone of the customer."))
        try:
            delivered, left = place._ocd_relay_hand_over(parcel, code)
        except UserError as exc:
            return self._render_hand_over(holder, place, parcel, error=exc.args[0])
        if delivered:
            return self._render_home(holder, place, message=env._("Handed over to %s. Thank you!",
                                                                  self._customer(parcel)))
        if left:
            return self._render_hand_over(holder, place, parcel,
                                          error=env._("This is not the code of this parcel. Attempts left: %s.", left))
        return self._render_hand_over(holder, place, parcel,
                                      error=env._("Too many wrong codes: the parcel is locked. Call the team."))

    # === BECOME A RELAY POINT === #

    @http.route(BECOME, type="http", auth="public", website=True, methods=["GET"], sitemap=True)
    def relay_become(self, **kwargs):
        return self._render_become()

    def _render_become(self, values=None, error=None, sent=False):
        env = request.env
        company = common.company()
        values = values or {}
        country = common.default_country()
        cities = env["res.city"].sudo().search([("country_id", "=", country.id)], order="name")
        city_id = int(values["city_id"]) if str(values.get("city_id") or "").isdigit() else 0
        city = cities.filtered(lambda c: c.id == city_id)[:1] or company.ocd_stock_city_id or cities[:1]
        districts = env["res.city.district"].sudo().search([("city_id", "=", city.id)], order="name") if city \
            else env["res.city.district"]
        return request.render("ocd_live_shop.relay_become", common.page_values(
            False,
            back="/",
            header_brand=True,
            fee=common.money(company.ocd_relay_fee, company.currency_id),
            capacity=company.ocd_relay_capacity,
            title=env._("Keep the parcels of OCD Live: %s per parcel handed over.",
                        common.money(company.ocd_relay_fee, company.currency_id)),
            capacity_line=env._("A closed place for %s parcels, sheltered from the rain.", company.ocd_relay_capacity),
            cities=cities,
            city=city,
            districts=districts,
            values=values,
            dial_rows=common.dial_rows(country),
            phone_value=values.get("phone", ""),
            error=error,
            sent=sent,
        ))

    @http.route(BECOME, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def relay_become_post(self, **post):
        env = request.env
        country = env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, post.get("phone"))
        if not number:
            return self._render_become(post, error=common.phone_error(country))
        district = env["res.city.district"].sudo().browse(int(post.get("district_id") or 0)).exists()
        try:
            env["ocd.vendor.place"].sudo()._ocd_relay_request(
                common.clean_text(post.get("shop"), 80), common.clean_text(post.get("name"), 80), number, country,
                district, common.clean_text(post.get("landmark"), 200), common.clean_text(post.get("business"), 300),
            )
        except UserError as exc:
            return self._render_become(post, error=exc.args[0])
        return self._render_become(sent=True)
