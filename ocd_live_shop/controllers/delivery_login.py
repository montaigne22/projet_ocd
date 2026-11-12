import logging

from odoo import http
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live.controllers.vendor_space import SESSION_LOGIN, OcdVendorSpace

_logger = logging.getLogger(__name__)

SESSION_COURIER = "ocd_courier_id"
SESSION_COURIER_TOKEN = "ocd_courier_token"
# The phone remembers the courier when the session of Odoo ends or is replaced (see
# common.VENDOR_COOKIE)
COURIER_COOKIE = "ocd_courier"


def current_courier():
    """Courier opened on this browser (personal link or code), as long as the contact is still
    an active courier and the team did not make a new personal link."""
    Partner = request.env["res.partner"].sudo()
    courier_id = request.session.get(SESSION_COURIER)
    if not courier_id:
        courier = common.browser_partner(COURIER_COOKIE, "courier")
        if courier.active and courier.ocd_is_courier:
            # The session of Odoo lost the courier: the cookie of this phone opens the app again
            _logger.info("OCD Live: courier %s opened again by the cookie of the browser", courier.id)
            remember_courier(courier)
            return courier
        return Partner
    courier = Partner.browse(courier_id).exists()
    token = request.session.get(SESSION_COURIER_TOKEN) or ""
    if courier.active and courier.ocd_is_courier and courier.ocd_space_token and consteq(courier.ocd_space_token, token):
        return courier
    # No more a courier, archived, or a new personal link: this phone asks for the number again
    forget_courier()
    return Partner


def remember_courier(courier):
    request.session[SESSION_COURIER] = courier.id
    request.session[SESSION_COURIER_TOKEN] = courier.sudo()._ocd_get_space_token()
    common.remember_browser(COURIER_COOKIE, courier, "courier")


def forget_courier():
    request.session.pop(SESSION_COURIER, None)
    request.session.pop(SESSION_COURIER_TOKEN, None)
    common.forget_browser(COURIER_COOKIE)


def _is_known_courier():
    # The code of the modules is shared by the databases of the server: only where the couriers exist
    return "ocd_is_courier" in request.env["res.partner"]._fields and bool(current_courier())


# The couriers known on this browser change page without reloading it, as the vendors
common.FAST_NAVIGATION_CHECKS.append(_is_known_courier)


def courier_login_mode():
    """The couriers log in like the vendors: the personal link in the link mode (a code while
    the links cannot leave), otherwise a code (they have no password)."""
    if common.company().ocd_vendor_login != "link":
        return "whatsapp_code"
    return "link" if request.env["res.partner"].sudo()._ocd_link_login_ready("livrer") else "whatsapp_code"


class OcdDeliveryLogin(OcdVendorSpace):
    """Login of the delivery app (/ocd/livrer): the courier, or the vendor who delivers, gives
    the number of its card at OCD Live and receives its link or a code on WhatsApp. Only the
    contacts the team made couriers (or vendors) get a message; the answer is the same for
    any number."""

    LOGIN_PAGES = dict(
        OcdVendorSpace.LOGIN_PAGES,
        livrer={"form": "/ocd/livrer", "code": "/ocd/livrer/code", "home": "/ocd/livrer/moi"},
    )

    def _login_page_mode(self, target):
        if target == "livrer":
            return courier_login_mode()
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        Partner = request.env["res.partner"].sudo()
        courier = Partner._ocd_find_by_phone(number, [("ocd_is_courier", "=", True)])
        if target == "livrer":
            if courier:
                return courier
            if common.company().ocd_vendor_login == "password":
                # The vendors log in to Odoo with their password (link on the page)
                return Partner
            return super()._ocd_login_partner(number, target)
        # The page of the vendors also answers a courier who types its number there
        return super()._ocd_login_partner(number, target) or courier

    def _ocd_send_link(self, partner, target):
        if partner.ocd_is_courier or target == "livrer":
            return partner._ocd_send_delivery_link(partner._ocd_get_livrer_url())
        return super()._ocd_send_link(partner, target)

    def _ocd_open_session(self, partner, target):
        if partner.ocd_is_courier and (target == "livrer" or not partner.ocd_is_vendor):
            remember_courier(partner)
            return self.LOGIN_PAGES["livrer"]["home"]
        return super()._ocd_open_session(partner, target)

    @http.route("/ocd/livrer", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def delivery_login(self, **kwargs):
        if current_courier() or common.current_vendor():
            return request.redirect("/ocd/livrer/moi")
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="livrer")

    @http.route("/ocd/livrer", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def delivery_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "livrer")

    @http.route("/ocd/livrer/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def delivery_login_code(self, code=None, **kwargs):
        return self._login_code(code, "livrer")

    @http.route("/ocd/livrer/deconnexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def delivery_logout_page(self, **kwargs):
        """An old link, or a link loaded in advance by the browser: it logs nobody out (« Log
        out » is a button that sends a form)."""
        return request.redirect("/ocd/livrer/moi")

    @http.route("/ocd/livrer/deconnexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def delivery_logout(self, **kwargs):
        """The courier leaves the app on this phone: the number is asked again."""
        forget_courier()
        request.session.pop(SESSION_LOGIN, None)
        return request.redirect("/ocd/livrer")
