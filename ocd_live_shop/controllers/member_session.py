"""The session of a person of the team of a vendor (chantier 22): her phone remembers her like
the phone of a vendor (session of Odoo and a cookie of its own), until « Log out », a new personal
link, or her removal from the team. Used by her space and by the app of the parcels."""
import logging

from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live import page_cache
from odoo.addons.ocd_live.controllers import common

_logger = logging.getLogger(__name__)

SESSION_MEMBER = "ocd_member_partner_id"
SESSION_MEMBER_TOKEN = "ocd_member_token"
MEMBER_COOKIE = "ocd_member"
HOME = "/ocd/mon-magasin"
LOGIN = "/ocd/mon-magasin/connexion"


def current_member():
    """Her place in a team, opened on this browser (personal link or code), as long as she is
    still in the team and her personal link is the same."""
    Member = request.env["ocd.vendor.member"].sudo()
    partner_id = request.session.get(SESSION_MEMBER)
    if not partner_id:
        partner = common.browser_partner(MEMBER_COOKIE, "member")
        member = Member._ocd_of_partner(partner) if partner else Member
        if member:
            # The session of Odoo lost her: the cookie of this phone opens her space again
            _logger.info("OCD Live: person of a team %s opened again by the cookie of the browser", member.id)
            remember_member(member)
        return member
    partner = request.env["res.partner"].sudo().browse(partner_id).exists()
    member = Member._ocd_of_partner(partner) if partner else Member
    token = request.session.get(SESSION_MEMBER_TOKEN) or ""
    if member and partner.ocd_space_token and consteq(partner.ocd_space_token, token):
        return member
    # Removed from the team, or a new personal link: this phone asks for the number again
    forget_member()
    return Member


def remember_member(member):
    partner = member.sudo().partner_id
    request.session[SESSION_MEMBER] = partner.id
    request.session[SESSION_MEMBER_TOKEN] = partner._ocd_get_space_token()
    common.remember_browser(MEMBER_COOKIE, partner, "member")


def forget_member():
    request.session.pop(SESSION_MEMBER, None)
    request.session.pop(SESSION_MEMBER_TOKEN, None)
    common.forget_browser(MEMBER_COOKIE)


def _is_known_member():
    # The code of the modules is shared by the databases of the server: only where the teams exist
    return "ocd.vendor.member" in request.env and bool(current_member())


# She changes page without reloading it, as the vendors and the couriers
common.FAST_NAVIGATION_CHECKS.append(_is_known_member)
# Her pages are built for her (ocd_live.page_cache)
page_cache.PERSONAL_COOKIES.add(MEMBER_COOKIE)


def member_login_mode():
    """She logs in like the vendors: her personal link in the link mode (a code while the links
    cannot leave), otherwise a code (she has no password)."""
    if common.company().ocd_vendor_login != "link":
        return "whatsapp_code"
    return "link" if request.env["res.partner"].sudo()._ocd_link_login_ready("magasin") else "whatsapp_code"


def member_header_link():
    return {"href": "/ocd/mon-magasin/deconnexion", "post": True, "label": request.env._("Log out")}
