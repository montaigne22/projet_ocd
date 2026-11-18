"""The entrance of an event (design OcdTickets): the controllers of the organiser log in with their
number (a code on WhatsApp), scan the tickets with the camera of their phone on a page of OCD Live,
without an application. The list of the tickets stays in the phone when the network is gone; the
entries made then leave as soon as it is back. When the organiser allows it, they sell at the door
(cash or Mobile Money)."""
import logging
from datetime import datetime, timedelta, timezone

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live import page_cache, tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_vote.controllers.organizer import OcdVoteOrganizerLogin

_logger = logging.getLogger(__name__)

SESSION_CONTROLLER = "ocd_ticket_controller_partner"
SESSION_CONTROLLER_TOKEN = "ocd_ticket_controller_token"
CONTROLLER_COOKIE = "ocd_controller"
HOME = "/billets/entree"
LOGIN = "/billets/entree/connexion"
# An entry made without the network is taken with its hour if it is at most this old
OFFLINE_HOURS = 24

page_cache.PERSONAL_COOKIES.add(CONTROLLER_COOKIE)


def current_controller_partner():
    """The contact of the controllers opened on this browser (a code checked)."""
    Partner = request.env["res.partner"].sudo()
    partner_id = request.session.get(SESSION_CONTROLLER)
    if not partner_id:
        partner = common.browser_partner(CONTROLLER_COOKIE, "controller")
        if partner and partner.ocd_ticket_controller_ids:
            remember_controller(partner)
            return partner
        return Partner
    partner = Partner.browse(partner_id).exists()
    token = request.session.get(SESSION_CONTROLLER_TOKEN) or ""
    if partner and partner.ocd_ticket_controller_ids and partner.ocd_space_token and consteq(partner.ocd_space_token, token):
        return partner
    forget_controller()
    return Partner


def remember_controller(partner):
    request.session[SESSION_CONTROLLER] = partner.id
    request.session[SESSION_CONTROLLER_TOKEN] = partner._ocd_get_space_token()
    common.remember_browser(CONTROLLER_COOKIE, partner, "controller")


def forget_controller():
    request.session.pop(SESSION_CONTROLLER, None)
    request.session.pop(SESSION_CONTROLLER_TOKEN, None)
    common.forget_browser(CONTROLLER_COOKIE)


class OcdTicketsControllerLogin(OcdVoteOrganizerLogin):
    """The login of the controllers: their number, then a code on WhatsApp."""

    LOGIN_PAGES = dict(OcdVoteOrganizerLogin.LOGIN_PAGES,
                       billets={"form": LOGIN, "code": "/billets/entree/code", "home": HOME})

    def _login_page_mode(self, target):
        if target == "billets":
            return "whatsapp_code"
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        if target == "billets":
            return request.env["ocd.ticket.controller"].sudo()._ocd_find_by_phone(number)
        return super()._ocd_login_partner(number, target)

    def _ocd_open_session(self, partner, target):
        if target == "billets":
            remember_controller(partner)
            return HOME
        return super()._ocd_open_session(partner, target)

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def controller_login(self, **kwargs):
        if current_controller_partner():
            return request.redirect(HOME)
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="billets")

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def controller_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "billets")

    @http.route("/billets/entree/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def controller_login_code(self, code=None, **kwargs):
        return self._login_code(code, "billets")

    @http.route("/billets/entree/deconnexion", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def controller_logout(self, **kwargs):
        forget_controller()
        return request.redirect(LOGIN)


class OcdTicketsEntrance(http.Controller):

    def _controls(self, partner):
        now = common.now()
        return request.env["ocd.ticket.controller"].sudo()._ocd_of_partner(partner).filtered(
            lambda control: control.event_id.date_end + timedelta(hours=6) > now
        ).sorted(lambda control: control.event_id.date_begin)

    def _control(self, event_id):
        partner = current_controller_partner()
        if not partner:
            return None
        control = self._controls(partner).filtered(lambda control: control.event_id.id == event_id)[:1]
        if not control:
            raise request.not_found()
        return control

    def _page(self, template, **values):
        return request.render(template, common.page_values(
            False,
            nav="tickets",
            header_link={"href": "/billets/entree/deconnexion", "post": True, "label": request.env._("Log out")},
            **values,
        ))

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def home(self, **kwargs):
        partner = current_controller_partner()
        if not partner:
            return request.redirect(LOGIN)
        controls = self._controls(partner)
        if len(controls) == 1:
            return request.redirect(f"{HOME}/{controls.event_id.id}")
        return self._page("ocd_tickets.entrance_home", back="/billets", header_title=request.env._("Entrance"),
                          controls=controls)

    def _counter(self, event):
        return f"{event._ocd_number(event.ocd_entered_count)} / {event._ocd_number(event.ocd_sold_count)}"

    @http.route(f"{HOME}/<int:event_id>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def scanner(self, event_id, **kwargs):
        control = self._control(event_id)
        if control is None:
            return request.redirect(LOGIN)
        return self._render_scanner(control)

    @http.route(f"{HOME}/<int:event_id>", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def scanner_typed(self, event_id, code=None, **post):
        """A code typed, without JavaScript: the same answer as the scan."""
        control = self._control(event_id)
        if control is None:
            return request.redirect(LOGIN)
        return self._render_scanner(control, result=self._check(control, (code or "")[:60]))

    def _render_scanner(self, control, result=None):
        event = control.event_id
        env = request.env
        return self._page(
            "ocd_tickets.entrance_scanner",
            back=HOME,
            header_title=env._("Entrance · %s", control.gate) if control.gate else env._("Entrance"),
            control=control,
            event=event,
            counter=self._counter(event),
            can_sell=control.can_sell and event._ocd_door_open(),
            result=result,
        )

    # === CHECK A TICKET === #

    def _result(self, kind, title, lines=(), event=None):
        return {"kind": kind, "title": title, "lines": [line for line in lines if line],
                "counter": self._counter(event) if event else ""}

    def _check(self, control, text, at=None):
        """The answer of the entrance for the QR read or the code typed."""
        env = request.env
        event = control.event_id
        registration, current = env["event.registration"].sudo()._ocd_find(text)
        if not registration or not current or not registration.ocd_code:
            return self._result("unknown", env._("Unknown ticket"),
                                [env._("Wrong code or changed copy: refuse.")], event)
        other = registration.event_id
        if other != event:
            local = other._ocd_local(other.date_begin)
            return self._result("other", env._("Not for tonight"), [env._(
                "Ticket of « %(event)s », on %(day)s", event=other.name,
                day=tools.day_text(env, local.date(), "d MMMM"))], event)
        if registration.ocd_refund_state != "none" or registration.state == "cancel" or not registration.active:
            return self._result("unknown", env._("Ticket not valid"),
                                [env._("Refunded or cancelled: refuse.")], event)
        if registration.state == "done":
            who = registration.ocd_controller_id
            lines = [env._("At %(hour)s, %(gate)s, by %(who)s", hour=event._ocd_hour(event._ocd_local(
                registration.ocd_entered_at)), gate=who.gate or "-", who=who.name or "-")
                     if registration.ocd_entered_at else "",
                     env._("Do not let in. A ticket given to a friend has a new QR: the old one is refused.")]
            if at:
                registration.message_post(body=env._("Shown again without the network at %(hour)s by %(who)s.",
                                                     hour=event._ocd_hour(event._ocd_local(at)), who=control.name))
            return self._result("already", env._("Already entered"), lines, event)
        registration._ocd_let_in(control, at=at)
        return self._result("ok", env._("Entry OK"), [" · ".join(part for part in (
            registration.event_ticket_id.name, registration.name, registration._ocd_index_text()
            if registration._ocd_index_text() != registration.event_ticket_id.name else "",
        ) if part)], event)

    @http.route(f"{HOME}/<int:event_id>/scan", type="jsonrpc", auth="public", website=True)
    def scan(self, event_id, text=None, at=None):
        """A QR read by the camera, or a code typed. `at`: an entry made without the network, sent
        when it came back (its hour, in seconds)."""
        control = self._control(event_id)
        if control is None:
            return {"kind": "login", "title": request.env._("Log in again")}
        moment = None
        if at:
            try:
                moment = datetime.fromtimestamp(float(at), tz=timezone.utc).replace(tzinfo=None)
            except (TypeError, ValueError, OverflowError):
                moment = None
            now = fields.Datetime.now()
            if moment and not now - timedelta(hours=OFFLINE_HOURS) <= moment <= now + timedelta(minutes=5):
                moment = None
        return self._check(control, (text or "")[:300], at=moment)

    @http.route(f"{HOME}/<int:event_id>/liste", type="jsonrpc", auth="public", website=True)
    def offline_list(self, event_id):
        """The tickets of the event, kept in the phone for the moments without the network: their
        code, the address of their QR, the name, and whether they entered."""
        control = self._control(event_id)
        if control is None:
            return {"tickets": []}
        event = control.event_id
        registrations = event._ocd_valid_registrations()
        return {"tickets": [{
            "code": registration.ocd_code,
            "qr": registration._ocd_ticket_path(),
            "label": " · ".join(part for part in (registration.event_ticket_id.name, registration.name) if part),
            "entered": registration.state == "done",
        } for registration in registrations], "counter": self._counter(event)}

    # === SELL AT THE DOOR === #

    def _render_sell(self, control, error=None, values=None):
        event = control.event_id
        env = request.env
        values = values or {}
        left = event._ocd_left()
        kinds = []
        for ticket in event.event_ticket_ids.sorted("sequence"):
            available = left.get(ticket.id)
            raw = str(values.get(f"q_{ticket.id}") or "0")
            kinds.append({
                "ticket": ticket,
                "price": ticket.price,
                "price_text": event._ocd_money(ticket.price),
                "out": available is not None and available <= 0,
                "max": min(available, 10) if available is not None else 10,
                "quantity": int(raw) if raw.isdigit() else 0,
            })
        if not any(kind["quantity"] for kind in kinds):
            first = next((kind for kind in kinds if not kind["out"]), None)
            if first:
                first["quantity"] = 1
        country = env["res.country"].sudo().browse(int(values.get("country_id") or 0)).exists() \
            or event.address_id.country_id or common.default_country()
        return self._page(
            "ocd_tickets.entrance_sell",
            back=f"{HOME}/{event.id}",
            header_title=env._("Sell at the door"),
            control=control,
            event=event,
            kinds=kinds,
            dial_rows=common.dial_rows(country),
            phone_value=values.get("phone") or "",
            currency_symbol=event.ocd_currency_id.symbol,
            error=error,
            message=env._("Sold: the ticket left on the WhatsApp of the customer and entered.") if values.get("vendu") else None,
        )

    @http.route(f"{HOME}/<int:event_id>/vendre", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def sell(self, event_id, **kwargs):
        control = self._control(event_id)
        if control is None:
            return request.redirect(LOGIN)
        if not (control.can_sell and control.event_id._ocd_door_open()):
            return request.redirect(f"{HOME}/{event_id}")
        return self._render_sell(control, values=kwargs)

    @http.route(f"{HOME}/<int:event_id>/vendre", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def sell_post(self, event_id, phone=None, country_id=None, method=None, **post):
        control = self._control(event_id)
        if control is None:
            return request.redirect(LOGIN)
        event = control.event_id
        env = request.env
        values = dict(post, phone=phone, country_id=country_id)
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return self._render_sell(control, error=common.phone_error(country), values=values)
        partner = env["ocd.vendor.follower"].sudo()._ocd_contact(number)
        if not partner.country_id:
            partner.country_id = country
        quantities = {}
        for ticket in event.event_ticket_ids:
            raw = str(post.get(f"q_{ticket.id}") or "0")
            quantities[ticket] = int(raw) if raw.isdigit() else 0
        try:
            order = env["sale.order"].sudo()._ocd_ticket_create(
                event, quantities, partner, partner.name if not partner.name.startswith("+") else "",
                source="door", controller=control,
            )
            if method == "cash":
                order._ocd_ticket_sell_cash()
                return request.redirect(f"{HOME}/{event.id}/vendre?vendu=1")
        except UserError as exc:
            return self._render_sell(control, error=exc.args[0], values=values)
        # Mobile Money: the payment form of OCD Live, on the phone of the controller; the ticket
        # enters once paid
        return request.redirect(order._ocd_tickets_path())
