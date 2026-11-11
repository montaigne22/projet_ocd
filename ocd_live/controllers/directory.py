from odoo import Command, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from . import common

PLATFORMS = {"tiktok": "TikTok", "facebook": "Facebook", "instagram": "Instagram", "youtube": "YouTube"}
LISTING_STATES = {"queued": "pending", "to_check": "pending", "published": "live"}


class OcdLiveDirectory(http.Controller):
    """Directory of the lives of the moment, by country and by category, and the pages of the
    vendor who is live: the pass, the link to send and the answer of the team."""

    # === LIVES OF THE MOMENT === #

    @http.route("/lives", type="http", auth="public", website=True, sitemap=True, methods=["GET"])
    def directory(self, note=None, error=None, **kwargs):
        listings, counts = common.live_counts()
        vendor = common.current_vendor()
        return request.render("ocd_live.lives", common.page_values(
            "directory",
            nav="lives",
            bottom_cta=self._live_cta(),
            windows=common.windows_info(),
            cards=common.country_chips(counts),
            total=len(listings),
            noted=bool(note),
            error=error,
            vendor=vendor,
            dial_rows=common.dial_rows(vendor.country_id if vendor else common.default_country()),
        ))

    @http.route("/lives/prevenir", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def directory_alert(self, phone=None, country_id=None, **post):
        """Tell the visitor on WhatsApp when the next checking window opens."""
        if post.get("website_url"):
            raise request.not_found()
        Alert = request.env["ocd.directory.alert"].sudo().with_company(common.company())
        vendor = common.current_vendor()
        try:
            if vendor:
                Alert._ocd_register(partner=vendor)
            else:
                country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists()
                number = common.normalize_phone(country, phone)
                if not number:
                    return self.directory(error=common.phone_error(country))
                Alert._ocd_register(phone=number)
        except (UserError, ValidationError) as error:
            return self.directory(error=error.args[0])
        return request.redirect("/lives?note=1")

    @http.route("/lives/<string:code>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def directory_country(self, code, categorie=None, **kwargs):
        country = request.env["res.country"].sudo().search([("code", "=", (code or "").upper())], limit=1)
        if not country or len(code) != 2:
            raise request.not_found()
        listings, _counts = common.live_counts()
        listings = listings.filtered(lambda listing: listing.country_id == country)
        categories = request.env["ocd.live.category"].sudo().search([])
        category = categories.filtered(lambda c: str(c.id) == categorie)[:1]
        shown = listings.filtered(lambda listing: listing.category_id == category) if category else listings
        now = common.now()
        rows = []
        for listing in shown:
            name = listing.title or listing.partner_id.name
            since = max(1, int((now - (listing.checked_at or listing.window_start or now)).total_seconds() // 60))
            rows.append({
                "listing": listing,
                "name": name,
                "initials": common.initials(name),
                "meta": request.env._(
                    "%(category)s · for %(minutes)s min", category=listing.category_id.name or "", minutes=since
                ),
                "shop_url": self._shop_url(listing.partner_id),
                "aria": request.env._("See the live of %s", name),
            })
        return request.render("ocd_live.lives_country", common.page_values(
            False,
            nav="lives",
            bottom_cta=self._live_cta(),
            back="/lives",
            header_h1=country.name,
            header_flag=country.code.lower(),
            header_count=request.env._("%s lives", len(shown)),
            country=country,
            chips=[{"label": request.env._("All"), "href": f"/lives/{code.lower()}", "on": not category}] + [
                {"label": c.name, "href": f"/lives/{code.lower()}?categorie={c.id}", "on": c == category}
                for c in categories
            ],
            rows=rows,
            windows=common.windows_info(),
        ))

    def _live_cta(self):
        return {"href": "/lives/pass", "label": request.env._("I am live"), "dot": True}

    def _shop_url(self, partner):
        """Return the shop of the vendor on OCD Live. Extended by ocd_live_shop."""
        return False

    # === I AM LIVE: PASS, LINK, ANSWER === #

    @http.route("/lives/pass", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def directory_pass(self, errors=None, error=None, **kwargs):
        vendor = common.current_vendor()
        product = self._pass_product()
        amount, currency = common.package_price(product, common.pricelist(vendor=vendor))
        days = product.ocd_pass_days or 30
        price = common.money(amount, currency)
        return request.render("ocd_live.pass_page", common.page_values(
            "pass",
            back="/lives",
            header_title=request.env._("I am live"),
            vendor=vendor,
            price=price,
            days=days,
            per_day=request.env._("About %s a day. Nothing is taken by itself.", common.money(amount / days, currency)),
            windows=common.windows_info(),
            pass_end=common.day_text(vendor.ocd_pass_end_date, "d MMMM") if vendor and vendor.ocd_pass_active else False,
            reminder_days=common.company().ocd_pass_reminder_days,
            take_label=request.env._("Take the pass · %s", price),
            values=kwargs,
            errors=errors or {},
            error=error,
            dial_rows=common.dial_rows(vendor.country_id if vendor else common.default_country()),
        ))

    @http.route("/lives/pass", type="http", auth="public", website=True, sitemap=False, methods=["POST"])
    def directory_pass_buy(self, **post):
        if post.get("website_url"):
            raise request.not_found()
        vendor = common.current_vendor()
        try:
            if not vendor:
                vendor = common.find_or_create_vendor(post, need_category=False)
        except common.FormErrors as error:
            return self.directory_pass(errors=error.errors, **post)
        if vendor.ocd_pass_active:
            return request.redirect("/lives/envoyer")
        order = request.env["sale.order"].sudo().with_company(common.company()).create({
            "partner_id": vendor.id,
            "company_id": common.company().id,
            "require_signature": False,
            # A positive prepayment makes Odoo ask for the payment of the order
            "prepayment_percent": 1.0,
            "order_line": [Command.create({"product_id": self._pass_product().id, "product_uom_qty": 1})],
        })
        return request.redirect(f"/ocd/payer/{order.id}?access_token={order._portal_ensure_token()}")

    def _pass_product(self):
        product = request.env.ref("ocd_live.product_directory_pass", raise_if_not_found=False)
        if not product:
            raise request.not_found()
        return product.sudo().product_variant_id

    @http.route("/lives/envoyer", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def directory_send(self, error=None, **kwargs):
        vendor = common.current_vendor()
        if not vendor or not vendor.ocd_pass_active:
            return request.redirect("/lives/pass")
        values = dict(kwargs)
        business = vendor.ocd_business if vendor.ocd_business != vendor.ocd_category_id.name else False
        values.setdefault("title", business or vendor.name)
        values.setdefault("country_id", str((vendor.country_id or common.default_country()).id))
        values.setdefault("category_id", str(vendor.ocd_category_id.id or ""))
        return request.render("ocd_live.send_link", common.page_values(
            "send_link",
            back="/lives/pass",
            header_title=request.env._("I am live"),
            vendor=vendor,
            countries=[
                {"country": country, "flag": country.code.lower()} for country in common.directory_countries()
            ],
            categories=request.env["ocd.live.category"].sudo().search([]),
            values=values,
            error=error,
        ))

    @http.route("/lives/envoyer", type="http", auth="public", website=True, sitemap=False, methods=["POST"])
    def directory_send_post(self, url=None, title=None, country_id=None, category_id=None, **post):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/lives/pass")
        env = request.env
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists()
        category = env["ocd.live.category"].sudo().browse(int(category_id or 0)).exists()
        url = (url or "").strip()
        if url and "://" not in url:
            # Links copied without their beginning, e.g. tiktok.com/@shop/live
            url = f"https://{url}"
        retry = {"url": url, "title": title, "country_id": country_id, "category_id": category_id}
        if not url or len((title or "").strip()) < 2:
            return self.directory_send(error=env._("The link of your live and your name are needed."), **retry)
        try:
            listing = env["ocd.directory.listing"].sudo().with_company(common.company())._ocd_submit(
                vendor, url, category or None, country=country or None, title=title
            )
        except (UserError, ValidationError) as error:
            return self.directory_send(error=error.args[0], **retry)
        return request.redirect(f"/lives/statut/{listing.id}")

    def _vendor_listing(self, listing_id):
        listing = request.env["ocd.directory.listing"].sudo().browse(listing_id).exists()
        vendor = common.current_vendor()
        if not listing or not vendor or listing.partner_id != vendor:
            raise request.not_found()
        return listing

    @http.route("/lives/statut/<int:listing_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def directory_status(self, listing_id, **kwargs):
        listing = self._vendor_listing(listing_id)
        env = request.env
        name = listing.title or listing.partner_id.name
        return request.render("ocd_live.listing_status", common.page_values(
            False,
            back="/lives/envoyer",
            header_title=env._("I am live"),
            listing=listing,
            state=LISTING_STATES.get(listing.state, listing.state),
            name=name,
            initials=common.initials(name),
            shown_in=env._(
                "Shown: %(country)s, %(category)s",
                country=listing.country_id.name or "",
                category=listing.category_id.name or "",
            ),
            queued=listing.state == "queued",
            window_start=common.to_viewer(listing.window_start).strftime("%H:%M") if listing.window_start else "",
            window_end=common.to_viewer(listing.window_end).strftime("%H:%M") if listing.window_end else "",
            reason=listing.refuse_note or listing.refuse_reason_id.message or listing.refuse_reason_id.name or "",
            poll_url=f"/lives/statut/{listing.id}/etat",
        ))

    @http.route("/lives/statut/<int:listing_id>/etat", type="jsonrpc", auth="public", website=True)
    def directory_status_state(self, listing_id):
        listing = self._vendor_listing(listing_id)
        return {"state": LISTING_STATES.get(listing.state, listing.state)}

    @http.route(
        "/lives/statut/<int:listing_id>/fin", type="http", auth="public", website=True, sitemap=False, methods=["POST"]
    )
    def directory_status_end(self, listing_id, **post):
        """The vendor ended the live: the link leaves the directory."""
        self._vendor_listing(listing_id).action_end()
        return request.redirect("/lives")
