"""The pages of the ambassadors (chantier 11, design Ambassadeurs).

- /ambassadeurs: become an ambassador (name, WhatsApp checked by a code, Mobile Money, charter);
- /ambassadeur/connexion: the login with the number and a code on WhatsApp;
- /ambassadeur: « My ambassador space » (to pay next, waiting, the week, the sales and their state);
- /ambassadeur/argent: « My money » (the next payout line by line, why it waits, the payouts
  made, a new payout number);
- /ambassadeur/produits, /ambassadeur/partager/<product>: the products to share, the image drawn by
  OCD Live with the personal link, the text;
- /ambassadeur/liens: the personal link of any page of the site;
- /a/<code>[/<product>]: the personal link. The last link opened is kept on the phone (the
  session) for the days of the settings, one visit per phone and per day is counted; robots (the
  previews of the links) and the ambassador themselves are not. A small cookie the scripts read
  shows « Grâce recommends this product » on the product, so that the pages stay kept in memory
  for the crowds (page_cache)."""
import re
import zlib
from datetime import timedelta
from urllib.parse import quote, urlsplit

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.ocd_live import page_cache
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live_shop import share_image
from odoo.addons.ocd_live_shop.controllers.member_space import OcdMemberLogin
from odoo.addons.ocd_live_shop.controllers.vendor_share import drawn, jpeg_response, photo_bytes, share_price, short_link
from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY

from ..models.res_partner import SPACE_STATES
from ..models.sale_order import SESSION_KEY

SESSION_AMBASSADOR = "ocd_ambassador_partner_id"
SESSION_AMBASSADOR_TOKEN = "ocd_ambassador_token"
# The links counted today on this phone: {code: ISO date}
SESSION_DAYS = "ocd_ambassador_days"
AMBASSADOR_COOKIE = "ocd_ambassador"
# « <product id>:<first name> », read by the script of the product page
RECO_COOKIE = "ocd_reco"
HOME = "/ambassadeur"
LOGIN = "/ambassadeur/connexion"
SIGNUP = "/ambassadeurs"
PAGE_SIZE = 30
SALES_SHOWN = 40
TEXT_MAX = 600

page_cache.PERSONAL_COOKIES.add(AMBASSADOR_COOKIE)
# The link kept on the phone changes no public page: the pages stay kept for these visitors
page_cache.SESSION_KEYS = page_cache.SESSION_KEYS | {SESSION_KEY, SESSION_DAYS}

# The robots that open the links (previews of WhatsApp, Facebook, TikTok, search engines)
ROBOTS = re.compile(
    r"bot|crawl|spider|slurp|preview|facebookexternalhit|facebookcatalog|whatsapp|telegram|discord|skype|"
    r"bytespider|tiktok|embedly|quora link|pinterest|vkshare|w3c_validator|curl|wget|python-requests|headless",
    re.IGNORECASE,
)


def is_robot():
    agent = request.httprequest.headers.get("User-Agent") or ""
    return not agent or bool(ROBOTS.search(agent))


def _opens_space(partner):
    return bool(partner) and partner.ocd_ambassador_state in SPACE_STATES


def current_ambassador():
    """The ambassador opened on this browser (a code checked), else an empty contact."""
    Partner = request.env["res.partner"].sudo()
    partner_id = request.session.get(SESSION_AMBASSADOR)
    if partner_id:
        partner = Partner.browse(partner_id).exists()
        token = request.session.get(SESSION_AMBASSADOR_TOKEN) or ""
        if _opens_space(partner) and partner.ocd_space_token and consteq(partner.ocd_space_token, token):
            return partner
        forget_ambassador()
        return Partner
    partner = common.browser_partner(AMBASSADOR_COOKIE, "ambassadeur")
    if _opens_space(partner):
        remember_ambassador(partner)
        return partner
    return Partner


def remember_ambassador(partner, browser=True):
    request.session[SESSION_AMBASSADOR] = partner.id
    request.session[SESSION_AMBASSADOR_TOKEN] = partner._ocd_get_space_token()
    if browser:
        common.remember_browser(AMBASSADOR_COOKIE, partner, "ambassadeur")


def forget_ambassador():
    request.session.pop(SESSION_AMBASSADOR, None)
    request.session.pop(SESSION_AMBASSADOR_TOKEN, None)
    common.forget_browser(AMBASSADOR_COOKIE)


def money(amount):
    return common.money(amount, common.company().currency_id)


def masked(number):
    """« 6 77 •• •• 18 »: enough to recognise their number, not to read it over a shoulder."""
    digits = re.sub(r"\D", "", number or "")
    if len(digits) < 6:
        return number or ""
    local = digits[-9:] if len(digits) >= 9 else digits
    return f"{local[:1]} {local[1:3]} •• •• {local[-2:]}"


def site_root():
    return request.httprequest.url_root.rstrip("/")


def image_version(product):
    """The version of the image to share of `product`: it changes with its photos and its price
    (a promo), so that the phones and the CDN never keep an old price."""
    price = share_price(product)
    return f"{product._ocd_photo_stamp(product)}-{zlib.crc32(price.encode()):08x}"


class OcdAmbassadorLogin(OcdMemberLogin):
    """Become an ambassador, then the login: the number, then a code on WhatsApp."""

    LOGIN_PAGES = dict(OcdMemberLogin.LOGIN_PAGES, ambassadeur={"form": LOGIN, "code": "/ambassadeur/code", "home": HOME})

    def _login_page_mode(self, target):
        if target == "ambassadeur":
            return "whatsapp_code"
        return super()._login_page_mode(target)

    def _ocd_login_partner(self, number, target):
        if target == "ambassadeur":
            return request.env["res.partner"].sudo()._ocd_find_ambassador_by_phone(number)
        return super()._ocd_login_partner(number, target)

    def _ocd_open_session(self, partner, target):
        if target == "ambassadeur":
            if partner.ocd_ambassador_state == "new":
                # The code proves the number: the account opens
                partner._ocd_ambassador_open_account()
            remember_ambassador(partner)
            return HOME
        return super()._ocd_open_session(partner, target)

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def ambassador_login(self, **kwargs):
        if current_ambassador():
            return request.redirect(HOME)
        if request.env.user._is_internal():
            return self._render_team()
        return self._render_login(target="ambassadeur")

    @http.route(LOGIN, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ambassador_login_phone(self, phone=None, country_id=None, **kwargs):
        return self._login_phone(phone, country_id, "ambassadeur")

    @http.route("/ambassadeur/code", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ambassador_login_code(self, code=None, **kwargs):
        return self._login_code(code, "ambassadeur")

    @http.route("/ambassadeur/deconnexion", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def ambassador_logout_page(self, **kwargs):
        """A link loaded in advance by the browser logs nobody out (« Log out » is a form)."""
        return request.redirect(HOME)

    @http.route("/ambassadeur/deconnexion", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ambassador_logout(self, **kwargs):
        forget_ambassador()
        return request.redirect(LOGIN)

    @http.route("/ambassadeur/equipe/<int:partner_id>", type="http", auth="user", website=True, methods=["GET"],
                sitemap=False)
    def ambassador_team_view(self, partner_id, signature=None, **kwargs):
        """« See their space » of the back office: signed for the person of the team who touched it,
        it opens nothing for anyone else; not remembered on this browser."""
        user = request.env.user
        partner = request.env["res.partner"].sudo().browse(partner_id).exists()
        if (
            not user.has_group("ocd_live.group_ocd_live_user")
            or not _opens_space(partner)
            or not signature
            or not consteq(partner._ocd_team_view_signature(user.id), signature)
        ):
            raise request.not_found()
        remember_ambassador(partner, browser=False)
        return request.redirect(HOME)

    # === BECOME AN AMBASSADOR === #

    @http.route(SIGNUP, type="http", auth="public", website=True, methods=["GET"], sitemap=True)
    def ambassador_signup(self, **kwargs):
        if current_ambassador():
            return request.redirect(HOME)
        return self._render_signup()

    def _render_signup(self, values=None, error=None, sent=False):
        env = request.env
        company = common.company()
        values = values or {}
        country = values.get("country") or common.default_country()
        example_price = 12000.0
        example = company.currency_id.round(example_price * company.ocd_ambassador_rate / 100.0)
        if company.ocd_ambassador_cap:
            example = min(example, company.ocd_ambassador_cap)
        return request.render("ocd_ambassadors.signup_page", common.page_values(
            False,
            back="/",
            header_brand=True,
            values=values,
            error=error,
            sent=sent,
            closed=company.ocd_ambassador_open == "closed",
            invited=company.ocd_ambassador_open == "invited",
            title_line=env._(
                "You share a product of OCD Live with your link. Your contact orders within %(days)s days: when "
                "their parcel is delivered and they keep it, you earn %(rate)s of the articles.",
                days=company.ocd_ambassador_link_days, rate=f"{company.ocd_ambassador_rate:g} %"),
            payout_line=env._("On your Mobile Money, from %s.", money(company.ocd_ambassador_min_payout)),
            example=money(example),
            example_line=env._("for a wax dress at %s delivered and kept. Your contact pays the same price as on the site.",
                               money(example_price)),
            dial_rows=common.dial_rows(country),
            phone_value=values.get("phone", ""),
        ))

    @http.route(SIGNUP, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ambassador_signup_post(self, **post):
        env = request.env
        if request.env.user._is_internal():
            return self._render_team()
        country = env["res.country"].sudo().browse(int(post.get("country_id") or 0)).exists() or common.default_country()
        values = {
            "name": common.clean_text(post.get("name"), 80), "phone": post.get("phone") or "",
            "momo": post.get("momo") or "", "country": country, "charter": bool(post.get("charter")),
        }
        number = common.normalize_phone(country, post.get("phone"))
        if not number:
            return self._render_signup(values, error=common.phone_error(country))
        momo = common.normalize_phone(country, post.get("momo")) if post.get("momo") else number
        if not momo:
            return self._render_signup(values, error=env._("Type your Mobile Money number, with the same country."))
        if not values["charter"]:
            return self._render_signup(values, error=env._("Tick that you share honestly and that you are 18 or more."))
        try:
            partner = env["res.partner"].sudo()._ocd_ambassador_signup(values["name"], number, country, momo, lang=env.lang)
        except UserError as exc:
            return self._render_signup(values, error=exc.args[0])
        if partner.ocd_ambassador_state == "requested":
            return self._render_signup(sent=True)
        # The number is proved by the code on WhatsApp (same page whether it is new or not)
        return self._login_phone(post.get("phone"), country.id, "ambassadeur")


class OcdAmbassadorSpace(http.Controller):
    """The space of an ambassador: their sales, their money, the products to share."""

    def _ambassador(self):
        """(ambassador, None) of the visitor, or (None, the answer to give)."""
        ambassador = current_ambassador()
        if not ambassador:
            return None, request.redirect(LOGIN)
        common.viewer_tz(ambassador)
        return ambassador, None

    def _page(self, ambassador, template, title, **values):
        env = request.env
        return request.render(template, common.page_values(
            False,
            nav="me",
            header_link={"href": "/ambassadeur/deconnexion", "post": True, "label": env._("Log out")},
            ambassador=ambassador,
            tabs=[
                {"key": "sales", "label": env._("My sales"), "url": HOME},
                {"key": "money", "label": env._("My money"), "url": "/ambassadeur/argent"},
                {"key": "products", "label": env._("Products to share"), "url": "/ambassadeur/produits"},
                {"key": "links", "label": env._("My links"), "url": "/ambassadeur/liens"},
            ],
            additional_title=title,
            home_link=short_link(f"{site_root()}/a/{ambassador.ocd_ambassador_code}"),
            notes=self._notes(ambassador),
            **values,
        ))

    def _notes(self, ambassador):
        env = request.env
        notes = []
        if ambassador.ocd_ambassador_state == "paused":
            notes.append(env._("Your account is paused: your links still work, nothing is earned for now. %s",
                               ambassador.ocd_ambassador_note or ""))
        elif ambassador.ocd_ambassador_state == "to_check":
            notes.append(env._("The team checks your account before your next payout: your gains are kept."))
        return [note.strip() for note in notes]

    def _next_payout_day(self):
        return request.env["ocd.live.dashboard"].sudo()._ocd_next_payout_day()

    def _unpaid_moves(self, ambassador):
        return request.env["account.move"].sudo().search([
            ("partner_id", "=", ambassador.id), ("ocd_ambassador_kind", "!=", False), ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
        ], order="invoice_date, id")

    # === MY SALES === #

    def _sale_row(self, gain):
        env = request.env
        state = gain.state
        amount = money(gain.amount)
        day = common.day_text(common.to_viewer(gain.delivered_at).date(), "d MMMM") if gain.delivered_at else ""
        if state == "ordered":
            pill, label, line = "route", env._("On the way"), env._("%s if it is delivered and kept", amount)
        elif state == "delivered":
            pill, label = "prep", env._("Delivered")
            line = env._("%(amount)s confirmed on %(day)s", amount=amount,
                         day=common.day_text(gain.confirm_on, "EEEE d MMMM")) if gain.confirm_on else amount
        elif state == "held":
            pill, label, line = "prep", env._("Return asked"), env._("%s waits for the decision of the team", amount)
        elif state == "confirmed":
            pill, label = "done", env._("Confirmed")
            line = env._("%s in your next payout", amount) if gain.bill_id.payment_state in ("not_paid", "partial") \
                else env._("%s paid", amount)
        elif state == "taken_back":
            pill, label, line = "problem", env._("Returned"), env._("− %s: already confirmed, taken from your next payout",
                                                                     amount)
        elif state == "cancelled":
            pill, label = "problem", env._("No gain")
            line = env._("Refused at the door or returned: no gain.") if gain.reason == "returned" \
                else env._("Cancelled: no gain.")
        else:
            reasons = {
                "own": env._("Ordered with your own number: your own purchase does not count."),
                "limit": env._("This customer already ordered several times this month with your links."),
                "paused": env._("Ordered while your account was paused."),
                "closed": env._("Ordered while the program was closed."),
            }
            pill, label, line = "locked", env._("No gain"), reasons.get(gain.reason, "")
        detail = " · ".join(part for part in (
            gain.customer_label, env._("delivered on %s", day) if day and state in ("delivered", "held") else "",
        ) if part)
        return {"title": gain.products_label or gain.picking_id.name, "pill": pill, "label": label, "line": line,
                "detail": detail}

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def ambassador_home(self, **kwargs):
        ambassador, answer = self._ambassador()
        if answer:
            return answer
        env = request.env
        Gain = env["ocd.ambassador.gain"].sudo()
        unpaid = self._unpaid_moves(ambassador)
        to_pay = sum(m.amount_total if m.move_type == "in_invoice" else -m.amount_total for m in unpaid)
        waiting = Gain.search([("ambassador_id", "=", ambassador.id), ("state", "in", ("ordered", "delivered", "held"))])
        on_the_way = len(waiting.filtered(lambda g: g.state == "ordered"))
        gains = Gain.search([("ambassador_id", "=", ambassador.id)], limit=SALES_SHOWN)
        blocks = ambassador._ocd_ambassador_payout_blocks()
        if blocks and to_pay > 0:
            to_pay_line = blocks[0]
        elif to_pay > 0:
            to_pay_line = env._("On your Mobile Money %s", masked(ambassador.ocd_payout_momo))
        else:
            to_pay_line = env._("Your gains confirmed come here.")
        return self._page(
            ambassador, "ocd_ambassadors.space_home", env._("My ambassador space"),
            tab="sales",
            to_pay=money(max(to_pay, 0.0)),
            to_pay_title=env._("To pay on %s", common.day_text(self._next_payout_day(), "EEEE d MMMM")),
            to_pay_line=to_pay_line,
            waiting=money(sum(waiting.mapped("amount"))),
            waiting_line=self._waiting_line(len(waiting) - on_the_way, on_the_way),
            week=self._week(ambassador),
            rows=[self._sale_row(gain) for gain in gains],
        )

    def _waiting_line(self, delivered, on_the_way):
        env = request.env
        days = common.company().ocd_ambassador_confirm_days
        parts = []
        if delivered:
            parts.append(env._("1 parcel delivered less than %s days ago", days) if delivered == 1 else env._(
                "%(count)s parcels delivered less than %(days)s days ago", count=delivered, days=days))
        if on_the_way:
            parts.append(env._("1 on the way") if on_the_way == 1 else env._("%s on the way", on_the_way))
        return ", ".join(parts) or env._("Nothing waiting.")

    def _week(self, ambassador):
        """The last 7 days: orders, visits by the links, parcels delivered."""
        env = request.env
        since = fields.Datetime.now() - timedelta(days=7)
        Gain = env["ocd.ambassador.gain"].sudo()
        gains = Gain.search([("ambassador_id", "=", ambassador.id), ("create_date", ">=", since),
                             ("state", "!=", "refused")])
        orders = len(gains.order_id)
        delivered = Gain.search_count([("ambassador_id", "=", ambassador.id), ("delivered_at", ">=", since)])
        today = common.to_viewer(fields.Datetime.now()).date()
        visits = env["ocd.vendor.count"].sudo()._ocd_totals(ambassador, "ambassador_visit", today - timedelta(days=6), today)
        return {
            "orders": env._("1 order") if orders == 1 else env._("%s orders", orders),
            "line": " · ".join((
                env._("1 visit") if visits == 1 else env._("%s visits", visits),
                env._("1 delivered") if delivered == 1 else env._("%s delivered", delivered),
            )),
        }

    # === MY MONEY === #

    def _move_line(self, move):
        """« Chemise wax homme, Pagne wax · Carine M. »: what the line of the payout is."""
        gain = move.ocd_ambassador_gain_id
        label = " · ".join(part for part in (gain.products_label, gain.customer_label) if part) or move.ref or move.name
        if move.ocd_ambassador_kind == "taken_back":
            label = request.env._("%s, returned", label)
        sign = -1 if move.move_type == "in_refund" else 1
        return {"label": label, "amount": money(sign * move.amount_total), "negative": sign < 0}

    @http.route("/ambassadeur/argent", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def ambassador_money(self, numero=None, **kwargs):
        ambassador, answer = self._ambassador()
        if answer:
            return answer
        env = request.env
        company = common.company()
        unpaid = self._unpaid_moves(ambassador)
        to_pay = sum(m.amount_total if m.move_type == "in_invoice" else -m.amount_total for m in unpaid)
        blocks = ambassador._ocd_ambassador_payout_blocks()
        if to_pay > 0 and company.currency_id.compare_amounts(to_pay, company.ocd_ambassador_min_payout) < 0:
            blocks.append(env._("Below %s, it waits for the next payout day.", money(company.ocd_ambassador_min_payout)))
        elif to_pay < 0:
            blocks.append(env._("A return taken back is more than your gains: it waits for your next gains."))
        payouts = env["ocd.payout"].sudo().search([("vendor_id", "=", ambassador.id), ("state", "=", "paid")], limit=12)
        paid_total = sum(env["ocd.payout"].sudo().search([("vendor_id", "=", ambassador.id), ("state", "=", "paid")]).mapped("amount"))
        country = ambassador.country_id or common.default_country()
        return self._page(
            ambassador, "ocd_ambassadors.space_money", env._("My money"),
            tab="money",
            next_title=common.day_text(self._next_payout_day(), "EEEE d MMMM", capital=True),
            to_pay=money(max(to_pay, 0.0)),
            lines=[self._move_line(move) for move in unpaid],
            blocks=blocks,
            payouts=[{
                "label": " · ".join(part for part in (common.day_text(payout.date, "EEEE d MMMM", capital=True),
                                                     payout.payment_reference) if part),
                "amount": money(payout.amount),
            } for payout in payouts],
            paid_total=money(paid_total),
            momo_line=self._momo_line(ambassador),
            hold_line=env._("A new number waits %s hours before the first payout, and the number of your account is "
                            "told on WhatsApp: if it is not you, you stop it.", company.ocd_ambassador_momo_hold_hours),
            id_line=env._("Above %s earned, the team sees your identity document before the next payout (once).",
                          money(company.ocd_ambassador_id_above)) if company.ocd_ambassador_id_above else "",
            confirm_line=env._("A gain is confirmed %s days after the delivery. A return later is taken from the next "
                               "payout; below the minimum, or nothing, it waits for the next week: nothing is lost, "
                               "nothing is paid too much.", company.ocd_ambassador_confirm_days),
            dial_rows=common.dial_rows(country),
            phone_value="",
            message={"1": env._("Noted: your new number waits %s hours before a payout, the number of your account is told.",
                                company.ocd_ambassador_momo_hold_hours),
                     "0": env._("This is already your number.")}.get(numero),
        )

    def _momo_line(self, ambassador):
        env = request.env
        if not ambassador.ocd_payout_momo:
            return env._("No number yet")
        if ambassador._ocd_ambassador_momo_wait_until():
            return env._("%s · waits before a payout", masked(ambassador.ocd_payout_momo))
        return masked(ambassador.ocd_payout_momo)

    @http.route("/ambassadeur/numero", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def ambassador_momo(self, phone=None, country_id=None, **kwargs):
        ambassador, answer = self._ambassador()
        if answer:
            return answer
        country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return request.redirect("/ambassadeur/argent?numero=0")
        changed = ambassador._ocd_ambassador_set_momo(number)
        return request.redirect(f"/ambassadeur/argent?numero={1 if changed else 0}")

    # === PRODUCTS TO SHARE === #

    def _product_row(self, ambassador, product):
        env = request.env
        price, was = product.sudo()._ocd_on_sale_price()
        currency = common.company().currency_id
        return {
            "product": product,
            "image": f"/web/image/product.template/{product.id}/image_256",
            "vendor": product.ocd_vendor_id.name or common.company().name,
            "price": common.money(price, currency),
            "was": common.money(was, currency) if was else "",
            "earn": env._("You earn %s", money(product._ocd_ambassador_earn(common.company()))),
            "share_url": f"/ambassadeur/partager/{product.id}",
        }

    @http.route("/ambassadeur/produits", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def ambassador_products(self, vue=None, q=None, page=None, **kwargs):
        ambassador, answer = self._ambassador()
        if answer:
            return answer
        env = request.env
        tabs = [("best", env._("Best sellers")), ("promo", env._("In promo")), ("live", env._("In live tonight")),
                ("new", env._("New"))]
        tab = vue if vue in dict(tabs) else "best"
        search = common.clean_text(q, 60) if q else ""
        page_number = max(int(page), 1) if str(page or "").isdigit() else 1
        products, more = env["product.template"].sudo()._ocd_ambassador_products(
            ambassador, tab, search, offset=(page_number - 1) * PAGE_SIZE, limit=PAGE_SIZE)
        query = f"vue={tab}" + (f"&q={quote(search)}" if search else "")
        return self._page(
            ambassador, "ocd_ambassadors.space_products", env._("Products to share"),
            tab="products",
            product_tabs=[{"key": key, "label": label, "url": f"/ambassadeur/produits?vue={key}",
                           "on": key == tab} for key, label in tabs],
            product_tab=tab,
            search=search,
            rows=[self._product_row(ambassador, product) for product in products],
            more_url=f"/ambassadeur/produits?{query}&page={page_number + 1}" if more else "",
        )

    def _share_text(self, product, link):
        env = request.env
        price, _was = product.sudo()._ocd_on_sale_price()
        vendor = product.ocd_vendor_id.name or common.company().name
        return env._("Look at %(product)s of %(vendor)s: %(price)s on OCD Live, delivered with a code. %(link)s",
                     product=product.name, vendor=vendor, price=common.money(price, common.company().currency_id),
                     link=link)

    @http.route("/ambassadeur/partager/<int:product_id>", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def ambassador_share(self, product_id, **kwargs):
        ambassador, answer = self._ambassador()
        if answer:
            return answer
        env = request.env
        Product = env["product.template"].sudo()
        product = Product.search(Product._ocd_ambassador_domain() + [("id", "=", product_id)], limit=1)
        if not product:
            return request.redirect("/ambassadeur/produits")
        code = ambassador.ocd_ambassador_code
        url = f"{site_root()}/a/{code}/{product.id}"
        link = short_link(url)
        image = f"/a/{code}/{product.id}/image.jpg?unique={image_version(product)}"
        text = self._share_text(product, link)
        clip = self._clip(product)
        own = ambassador._ocd_ambassador_same_person(product.ocd_vendor_id) if product.ocd_vendor_id else False
        return self._page(
            ambassador, "ocd_ambassadors.space_share", env._("Share"),
            tab="products",
            product=product,
            url=url,
            link=link,
            image=image,
            text=text,
            whatsapp_url=f"https://wa.me/?text={quote(text)}",
            earn=env._("You earn %s on each piece delivered and kept.",
                       money(product._ocd_ambassador_earn(common.company()))),
            own=own,
            clip=clip,
            link_line=env._("Your link: %s", link),
        )

    def _clip(self, product):
        """The clip of the live of the product, when the clips are installed and one is ready."""
        if "ocd.live.clip" not in request.env:
            return False
        clip = request.env["ocd.live.clip"].sudo().search(
            [("product_tmpl_id", "=", product.id), ("state", "=", "ready")], order="id desc", limit=1)
        if not clip or not clip._ocd_public():
            return False
        return {"video": clip._ocd_video_url(), "name": f"ocd-live-{clip.id}.mp4"}

    # === MY LINKS === #

    @http.route("/ambassadeur/liens", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def ambassador_links(self, page=None, **kwargs):
        ambassador, answer = self._ambassador()
        if answer:
            return answer
        env = request.env
        code = ambassador.ocd_ambassador_code
        home_url = f"{site_root()}/a/{code}"
        made = error = ""
        if page:
            path = self._site_path(page)
            if path:
                made = f"{home_url}?r={quote(path, safe='/')}"
            else:
                error = env._("Paste the address of a page of OCD Live (a boutique, a live, the programme).")
        return self._page(
            ambassador, "ocd_ambassadors.space_links", env._("My links"),
            tab="links",
            home_url=home_url,
            made=made,
            made_short=short_link(made) if made else "",
            page_value=page or "",
            error=error,
            days_line=env._("Each link counts for you %s days on the phone that opens it, for everything ordered there; "
                            "the last link opened counts.", common.company().ocd_ambassador_link_days),
        )

    def _site_path(self, address):
        """The path of `address` when it is a page of this site, else ''."""
        address = (address or "").strip()[:500]
        if not address:
            return ""
        parts = urlsplit(address if "://" in address or address.startswith("/") else f"https://{address}")
        here = urlsplit(site_root())
        if parts.netloc and parts.netloc.lower() not in (here.netloc.lower(), f"www.{here.netloc.lower()}"):
            return ""
        path = parts.path or "/"
        if parts.query:
            path = f"{path}?{parts.query}"
        return common.local_path(path, "")

    # === THE PERSONAL LINK === #

    @http.route(["/a/<string:code>", "/a/<string:code>/<int:product_id>"], type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def ambassador_link(self, code, product_id=None, r=None, **kwargs):
        env = request.env
        ambassador = env["res.partner"].sudo()._ocd_ambassador_by_code(code)
        product = env["product.template"].sudo().browse(product_id).exists() if product_id else env["product.template"]
        if product and not product.is_published:
            product = env["product.template"]
        if product:
            target = product.website_url
        else:
            target = common.local_path(r, "/shop") if r else "/shop"
            if target.startswith(("/a/", "/ambassadeur", "/web", "/odoo")):
                target = "/shop"
        response = request.redirect(target, code=302)
        response.headers["X-Robots-Tag"] = "noindex"
        response.headers["Cache-Control"] = "no-store"
        if ambassador and ambassador.ocd_ambassador_state in ("active", "to_check", "paused") \
                and not self._own_visit(ambassador, product):
            self._keep_link(ambassador, product, response)
        return response

    def _own_visit(self, ambassador, product):
        """The robots, the team, the ambassador themselves, the vendor of the product: no visit."""
        if is_robot() or request.env.user._is_internal():
            return True
        if current_ambassador() == ambassador:
            return True
        vendor = common.current_vendor()
        return bool(vendor and product and product.ocd_vendor_id == vendor)

    def _keep_link(self, ambassador, product, response):
        """The last link opened counts: kept on the phone, on its cart, counted once a day."""
        now = fields.Datetime.now()
        request.session[SESSION_KEY] = {"id": ambassador.id, "at": now.isoformat(timespec="seconds")}
        days = dict(request.session.get(SESSION_DAYS) or {})
        today = now.date().isoformat()
        code = ambassador.ocd_ambassador_code
        if days.get(code) != today:
            request.env["ocd.vendor.count"]._ocd_add(ambassador, "ambassador_visit", product.id if product else 0)
            days = {key: value for key, value in days.items() if value == today}
            days[code] = today
            request.session[SESSION_DAYS] = days
        cart_id = request.session.get(CART_SESSION_CACHE_KEY)
        if cart_id:
            request.env["sale.order"].sudo().browse(cart_id).exists()._ocd_note_ambassador(ambassador.id, now)
        first = (ambassador.name or "").split()[0] if (ambassador.name or "").split() else ""
        days_kept = max(common.company().ocd_ambassador_link_days, 1)
        response.set_cookie(
            RECO_COOKIE, f"{product.id if product else 0}:{quote(first[:40])}", max_age=days_kept * 24 * 60 * 60,
            httponly=False, samesite="Lax", secure=request.httprequest.scheme == "https",
        )

    @http.route("/a/<string:code>/<int:product_id>/image.jpg", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def ambassador_image(self, code, product_id, unique=None, **kwargs):
        """The image of a product with the personal link of the ambassador and its QR code: drawn
        once, then kept (by this process and the CDN)."""
        env = request.env
        ambassador = env["res.partner"].sudo()._ocd_ambassador_by_code(code)
        Product = env["product.template"].sudo()
        product = Product.search(Product._ocd_ambassador_domain() + [("id", "=", product_id)], limit=1)
        if not ambassador or not product:
            raise request.not_found()
        version = image_version(product)
        url = f"{site_root()}/a/{ambassador.ocd_ambassador_code}/{product.id}"
        lang = env.lang or ""
        price = share_price(product)
        data = drawn(("ambassador", ambassador.ocd_ambassador_code, product.id, version, lang, url),
                     lambda: share_image.product({
                         "photo": photo_bytes(product),
                         "name": product.name,
                         "price": price,
                         "vendor": product.ocd_vendor_id.name or common.company().name,
                         "cta": env._("Order it on OCD Live"),
                         "link": short_link(url),
                         "url": url,
                     }))
        return jpeg_response(data, unique, version)
