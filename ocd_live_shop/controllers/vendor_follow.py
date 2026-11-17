"""Follow a vendor (chantier 1, design SuivreVendeur): « Follow » on the boutique, the cards of the
lives, the replay and the page of a product; « Followed » to change what comes or stop; « My
followed vendors ».

Who follows: the person known on this browser (a vendor, an account, a follower who opened the
button of one of its messages), else the WhatsApp number typed. A number typed is not checked:
this browser only remembers the follows made on it (signed cookie), never the other follows of
that number; the button of a message (its secret) opens all of them on the phone that received
it."""
from urllib.parse import urlencode

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.misc import hmac

from odoo.addons.ocd_live import page_cache
from odoo.addons.ocd_live.controllers import common

# A follower opened the button of one of its messages on this browser: its contact
FOLLOWER_COOKIE = "ocd_follower"
# The follows made on this browser with a number typed (signed ids)
FOLLOWS_COOKIE = "ocd_follows"
FOLLOWS_KEPT = 30
# The pages of a person known on this browser are built for them (ocd_live.page_cache)
page_cache.PERSONAL_COOKIES.update({FOLLOWER_COOKIE, FOLLOWS_COOKIE})
SOURCES = ("boutique", "feed", "product", "replay")


def _follows_signature(ids):
    return hmac(request.env(su=True), "ocd_live-follows", ids)


def browser_follows():
    """The follows made on this browser with a number typed."""
    Follower = request.env["ocd.vendor.follower"].sudo().with_context(active_test=False)
    ids, _sep, signature = (request.httprequest.cookies.get(FOLLOWS_COOKIE) or "").rpartition(".")
    if not ids or not signature or not consteq(signature, _follows_signature(ids)):
        return Follower.browse()
    return Follower.browse([int(part) for part in ids.split("-") if part.isdigit()]).exists()


def remember_follow(follower):
    """This browser remembers a follow made on it."""
    ids = [str(record.id) for record in browser_follows() if record != follower][-(FOLLOWS_KEPT - 1):]
    value = "-".join([*ids, str(follower.id)])
    request.future_response.set_cookie(
        FOLLOWS_COOKIE, f"{value}.{_follows_signature(value)}", max_age=common.BROWSER_COOKIE_DAYS * 24 * 60 * 60,
        httponly=True, samesite="Lax", secure=request.httprequest.scheme == "https",
    )


def visitor_partner():
    """The contact known on this browser: the vendor, the account logged in, or the follower who
    opened the button of one of its messages here."""
    vendor = common.current_vendor()
    if vendor:
        return vendor
    user = request.env.user
    if not user._is_public() and user.partner_id.phone:
        return user.partner_id.sudo()
    return common.browser_partner(FOLLOWER_COOKIE, "follower")


def visitor_follows():
    """The follows of the visitor (active or not): the ones of the contact known, and the ones
    made on this browser."""
    Follower = request.env["ocd.vendor.follower"].sudo().with_context(active_test=False)
    partner = visitor_partner()
    follows = Follower.search([("partner_id", "=", partner.id)]) if partner else Follower
    return follows | browser_follows()


def visitor_follow(vendor):
    """The follow of `vendor` by the visitor, active (empty when they do not follow it)."""
    return visitor_follows().filtered(lambda follower: follower.vendor_id == vendor and follower.active)[:1]


def follow_url(vendor, back=None, source="boutique"):
    params = {"depuis": back} if back else {}
    if source != "boutique":
        params["source"] = source
    return f"/ocd/suivre/{vendor.id}" + (f"?{urlencode(params)}" if params else "")


class OcdVendorFollow(http.Controller):

    def _vendor(self, vendor_id):
        vendor = request.env["res.partner"].sudo().browse(vendor_id).exists()
        if not vendor or not vendor.ocd_is_vendor or vendor.ocd_vendor_state != "approved":
            raise request.not_found()
        return vendor

    def _back(self, vendor, depuis):
        return common.local_path(depuis, f"/ocd/boutique/{vendor.id}")

    def _known_number(self):
        """The contact whose number is already known here (one of their follows on this browser),
        so the visitor does not type it again."""
        partner = visitor_partner()
        if partner:
            return partner
        follows = browser_follows()
        return follows[-1:].partner_id if follows else request.env["res.partner"]

    def _render(self, vendor, depuis=None, source="boutique", error=None, phone_value="", country=None):
        env = request.env
        follower = visitor_follow(vendor)
        known = self._known_number()
        weekly = vendor._ocd_news_weekly()
        company = vendor.company_id or env.company
        day = dict(company._fields["ocd_news_weekday"]._description_selection(env)).get(company.ocd_news_weekday or "4", "")
        return request.render("ocd_live_shop.vendor_follow", common.page_values(
            False,
            nav="lives",
            back=self._back(vendor, depuis),
            header_title=env._("Follow"),
            vendor=vendor,
            initials=common.initials(vendor.name),
            follower=follower,
            known=known,
            first_name=(vendor.name or "").split()[0],
            depuis=self._back(vendor, depuis),
            source=source if source in SOURCES else "boutique",
            live_line=env._("« %s is live now »", vendor.name),
            news_line=env._("A message on %(day)s with what is new at %(vendor)s, each week", day=day.lower(), vendor=vendor.name)
            if weekly else env._("A message once a month, on %(day)s, with what is new at %(vendor)s",
                                 day=day.lower(), vendor=vendor.name),
            error=error,
            phone_value=phone_value,
            dial_rows=common.dial_rows(country or known.country_id or vendor.country_id or common.default_country()),
        ))

    @http.route("/ocd/suivre/<int:vendor_id>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def follow_page(self, vendor_id, depuis=None, source=None, **kwargs):
        return self._render(self._vendor(vendor_id), depuis=depuis, source=source or "boutique")

    @http.route("/ocd/suivre/<int:vendor_id>", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def follow(self, vendor_id, phone=None, country_id=None, depuis=None, source=None, action=None, **post):
        """Follow (with the number typed, or the one known here), change what comes, or stop."""
        vendor = self._vendor(vendor_id)
        if post.get("website_url"):
            raise request.not_found()  # a robot filled the hidden field
        env = request.env
        back = self._back(vendor, depuis)
        lives, news = bool(post.get("lives")), bool(post.get("news"))
        follower = visitor_follow(vendor)
        Follower = env["ocd.vendor.follower"].sudo().with_company(common.company())
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists()
        try:
            if action == "stop" and follower:
                follower._ocd_unfollow()
                return request.redirect(self._with(back, suivi="0"))
            if follower:
                follower._ocd_set(lives, news)
                return request.redirect(self._with(back, suivi="1" if (lives or news) else "0"))
            partner = self._known_number()
            if phone or not partner:
                country = country or common.default_country()
                number = common.normalize_phone(country, phone)
                if not number:
                    raise UserError(common.phone_error(country))
                partner = Follower._ocd_contact(number)
            follower = Follower._ocd_follow(vendor, partner, lives=lives, news=news, source=source if source in SOURCES else "boutique")
        except (UserError, ValidationError) as exc:
            return self._render(vendor, depuis=depuis, source=source, error=exc.args[0], phone_value=phone or "", country=country)
        if not visitor_partner():
            remember_follow(follower)
        return request.redirect(self._with(back, suivi="1"))

    @staticmethod
    def _with(path, **params):
        """`path` with `params`, before its anchor."""
        path, _sep, anchor = path.partition("#")
        joiner = "&" if "?" in path else "?"
        return f"{path}{joiner}{urlencode(params)}" + (f"#{anchor}" if anchor else "")

    @http.route("/ocd/abonne/<int:follower_id>/<string:token>", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def from_message(self, follower_id, token, vers=None, **kwargs):
        """The button of a message to a follower: its phone now knows it (it can stop or change
        what comes), then the boutique (with the news first, from the message of the news)."""
        follower = request.env["ocd.vendor.follower"].sudo().with_context(active_test=False).browse(follower_id).exists()
        if not follower or not follower._ocd_check_token(token):
            raise request.not_found()
        if not common.current_vendor():
            common.remember_browser(FOLLOWER_COOKIE, follower.partner_id, "follower")
        remember_follow(follower)
        if vers != "nouveautes":
            # The message of a live: « Opened from OCD » for the live of the vendor (chantier 3)
            now = fields.Datetime.now()
            live = request.env["ocd.live.booking"].sudo().search([
                ("partner_id", "=", follower.vendor_id.id), ("state", "=", "confirmed"),
                ("start_datetime", "<=", now), ("end_datetime", ">", now),
            ], limit=1)
            if live:
                request.env["ocd.vendor.count"]._ocd_add(follower.vendor_id, "watch", live.id)
        path = f"/ocd/boutique/{follower.vendor_id.id}"
        return request.redirect(f"{path}?nouveautes=1#produits" if vers == "nouveautes" else path)

    # === MY FOLLOWED VENDORS === #

    @http.route("/ocd/suivis", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def followed(self, **kwargs):
        env = request.env
        follows = visitor_follows().filtered("active").sorted(lambda follower: follower.vendor_id.name or "")
        lives = env["ocd.live.booking"].sudo().search([
            ("partner_id", "in", follows.vendor_id.ids), ("state", "=", "confirmed"),
            ("end_datetime", ">", common.now()),
        ], order="start_datetime")
        now = common.now()
        rows = []
        for follower in follows:
            vendor = follower.vendor_id
            live = lives.filtered(lambda booking, vendor=vendor: booking.partner_id == vendor)[:1]
            if live and live.start_datetime <= now:
                status, status_line = "live", env._("Live now")
            elif live:
                status, status_line = "next", env._("Live %s", common.day_text(common.to_viewer(live.start_datetime).date(), "EEE d MMM"))
            else:
                status, status_line = "", ""
            rows.append({
                "follower": follower,
                "initials": common.initials(vendor.name),
                "status": status,
                "status_line": status_line,
            })
        partner = visitor_partner() or follows[:1].partner_id
        return request.render("ocd_live_shop.followed_vendors", common.page_values(
            False,
            nav="me",
            back="/ocd/connexion",
            header_title=env._("My followed vendors"),
            rows=rows,
            number=partner.phone if partner else "",
        ))

    @http.route("/ocd/suivis/<int:follower_id>", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def followed_change(self, follower_id, action=None, **post):
        follower = visitor_follows().filtered(lambda record: record.id == follower_id)
        if not follower:
            raise request.not_found()
        if action == "stop":
            follower._ocd_unfollow()
        else:
            follower._ocd_set(bool(post.get("lives")), bool(post.get("news")))
        return request.redirect(f"/ocd/suivis#abonnement-{follower.id}")
