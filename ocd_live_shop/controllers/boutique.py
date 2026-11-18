import re
from urllib.parse import quote as url_quote, urlencode

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY
from odoo.addons.ocd_live.controllers import common

from . import shop_common
from .vendor_follow import follow_url, remember_follow, visitor_follow, visitor_partner
from .vendor_places import place_photo_url

def review_rows(reviews):
    """The reviews of the buyers as shown (chantier 2): « Estelle N. », the stars, verified
    purchase, the products, when, their word."""
    env = request.env
    return [{
        "author": review.author_name,
        "stars": review.stars,
        "line": " · ".join(part for part in (
            env._("Verified purchase"), ", ".join(review.product_ids.mapped("name")[:2]), review._ocd_when(),
        ) if part),
        "comment": review.comment,
    } for review in reviews]


def platform(url):
    """Return the name of the platform of a live link ("TikTok"), or "" (the live platforms of
    the configuration)."""
    return request.env["ocd.live.platform"].sudo()._ocd_for_url(url).name or ""


def duration_text(minutes):
    """Return a duration written for the visitor: "45 min", "1 h 28"."""
    minutes = max(0, int(minutes))
    if minutes < 60:
        return request.env._("%s min", minutes)
    return f"{minutes // 60} h {minutes % 60:02d}"


def clock_text(minutes):
    """Return the length of a video: "48:00", "1:28:00"."""
    minutes = max(0, int(minutes))
    return f"{minutes // 60}:{minutes % 60:02d}:00" if minutes >= 60 else f"{minutes}:00"


def whatsapp_url(phone, text):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 8:
        return False
    return f"https://wa.me/{digits}?text={url_quote(text)}"


class OcdBoutique(http.Controller):
    """Boutique of a vendor: the products, the live of the moment with the product shown on
    screen, the next live (with a WhatsApp alert), and the replay of the last live."""

    def _vendor(self, vendor_id):
        vendor = request.env["res.partner"].sudo().browse(vendor_id).exists()
        if not vendor or not vendor.ocd_is_vendor or vendor.ocd_vendor_state != "approved":
            raise request.not_found()
        return vendor

    def _current_live(self, vendor):
        now = fields.Datetime.now()
        return request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id),
            ("state", "=", "confirmed"),
            ("start_datetime", "<=", now),
            ("end_datetime", ">", now),
        ], limit=1)

    def _count_live_visit(self, vendor_id, **kwargs):
        """One visit per browser and per live, shown in the control room: also for a boutique
        given from memory (ocd_cache_hit). Return the live of the vendor now."""
        vendor = self._vendor(vendor_id)
        live = self._current_live(vendor)
        if live:
            seen = request.session.get("ocd_live_visits", [])
            if live.id not in seen:
                live._ocd_count_visit()
                request.session["ocd_live_visits"] = (seen + [live.id])[-20:]
            # The sales of the live (chantier 3): the cart of the visitor remembers the live
            cart_id = request.session.get(CART_SESSION_CACHE_KEY)
            if cart_id:
                request.env["sale.order"].sudo().browse(cart_id).exists()._ocd_note_lives(live)
        return live

    @http.route("/ocd/boutique/<int:vendor_id>/vu", type="http", auth="public", website=True, methods=["POST"], csrf=False,
                sitemap=False)
    def boutique_seen(self, vendor_id, **kwargs):
        """« Visits of your boutique » (chantier 3): told by the page once shown (boutique_visit.js),
        so that the page stays the same for everyone; one per phone and per day, never the vendor's
        own. Answers nothing."""
        vendor = self._vendor(vendor_id)
        today = fields.Date.today().isoformat()
        days = request.session.get("ocd_shop_days") or {}
        seen = days.get("v", []) if days.get("d") == today else []
        if vendor.id not in seen and common.current_vendor() != vendor:
            request.session["ocd_shop_days"] = {"d": today, "v": (seen + [vendor.id])[-50:]}
            request.env["ocd.vendor.count"]._ocd_add(vendor, "visit")
        return request.make_response("", status=204)

    def _next_live(self, vendor):
        return request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id),
            ("state", "=", "confirmed"),
            ("start_datetime", ">", fields.Datetime.now()),
        ], order="start_datetime", limit=1)

    def _replay_of(self, vendor, live=None):
        """The published replay `live` of the vendor, else its last one."""
        if live and str(live).isdigit():
            replay = request.env["ocd.live.booking"].sudo().search([
                ("id", "=", int(live)), ("partner_id", "=", vendor.id),
                ("replay_published", "=", True), ("replay_url", "!=", False),
            ], limit=1)
            if replay:
                return replay
        return self._last_replay(vendor)

    def _last_replay(self, vendor):
        return request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id),
            ("replay_published", "=", True),
            ("replay_url", "!=", False),
        ], order="start_datetime desc", limit=1)

    def _products(self, vendor):
        return request.env["product.template"].sudo().search([
            ("ocd_vendor_id", "=", vendor.id),
            ("ocd_review_state", "=", "approved"),
            ("is_published", "=", True),
            ("sale_ok", "=", True),
        ], order="website_sequence, id")

    def _follow_values(self, vendor, back, source="boutique", noted=False):
        """« Follow » or « Followed » (chantier 1): the follow of the visitor, how many follow the
        vendor, the message after following."""
        env = request.env
        follower = visitor_follow(vendor)
        count = vendor._ocd_follower_stats()[0]
        first = (vendor.name or "").split()[0]
        done = request.params.get("suivi")
        message = False
        if done == "1" or (noted and follower):
            message = env._("You follow %s: a WhatsApp at each live, and their news.", first) if follower.news \
                else env._("You follow %s: a WhatsApp at each live.", first)
        elif done == "0":
            message = env._("You no longer follow %s.", first)
        return {
            "follower": follower,
            "followers_line": (env._("1 follower") if count == 1 else env._("%s followers", count)) if count else "",
            "follow_href": follow_url(vendor, back, source),
            "follow_message": message,
        }

    def _review_values(self, vendor):
        Review = request.env["ocd.vendor.review"]
        summary = Review._ocd_summary(vendor)
        return {
            "reviews": summary,
            "review_rows": review_rows(Review._ocd_latest(vendor)),
            "reviews_all": request.env._("See the %s reviews", summary["count"]),
        }

    @http.route(
        "/ocd/boutique/<int:vendor_id>/avis", type="http", auth="public", website=True, sitemap=False, ocd_cache=60,
    )
    def boutique_reviews(self, vendor_id, **kwargs):
        """All the reviews of the buyers of a vendor (chantier 2)."""
        vendor = self._vendor(vendor_id)
        Review = request.env["ocd.vendor.review"].sudo()
        reviews = Review.search([("vendor_id", "=", vendor.id)] + Review._ocd_visible_domain(), limit=200)
        return request.render("ocd_live_shop.boutique_reviews", common.page_values(
            False,
            nav="lives",
            back=f"/ocd/boutique/{vendor.id}",
            back_label=request.env._("Back to the boutique"),
            header_title=request.env._("Reviews"),
            title=request.env._("Reviews of %s", vendor.name),
            vendor=vendor,
            reviews=Review._ocd_summary(vendor),
            review_rows=review_rows(reviews),
        ))

    def _price(self, product):
        return shop_common.prices(product).get(product.id) or common.money(product.list_price, product.currency_id)

    def _product_card(self, product):
        """What the boutique shows of a product: price, photo and stock, as in the shop."""
        return shop_common.card(product, shop_common.prices(product))

    def _live_info(self, live):
        name = platform(live._ocd_watch_url())
        minutes = max(1, int((fields.Datetime.now() - live.start_datetime).total_seconds() // 60))
        since = duration_text(minutes)
        return {
            "booking": live,
            "line": request.env._("For %(since)s, on %(platform)s", since=since, platform=name)
            if name else request.env._("Live for %s", since),
        }

    def _next_info(self, booking):
        local = common.to_viewer(booking.start_datetime)
        where = request.env._("At the OCD Live studio") if booking.mode == "studio" else request.env._(
            "From home, with OCD Live"
        )
        name = platform(booking._ocd_watch_url())
        if name:
            # The live goes on an account of OCD Live: where it is watched too
            where = f"{where} · {request.env._('On %s', name)}"
        return {
            "title": request.env._(
                "Next live: %(day)s at %(hour)s",
                day=tools.day_text(request.env, local.date(), "EEE d MMM"),
                hour=local.strftime("%H:%M"),
            ),
            "where": where,
        }

    def _replay_info(self, replay):
        local = common.to_viewer(replay.start_datetime)
        minutes = (replay.end_datetime - replay.start_datetime).total_seconds() // 60
        count = len(replay.moment_ids.product_tmpl_id)
        return {
            "booking": replay,
            "title": request.env._("Watch their live of %s again", tools.day_text(request.env, local.date(), "d MMM")),
            "line": request.env._(
                "%(duration)s · %(count)s products shown", duration=duration_text(minutes), count=count
            ),
        }

    def _contact(self, vendor):
        """The WhatsApp button: OCD Live when OCD sells, the vendor otherwise."""
        first_name = (vendor.name or "").split()[0] if vendor.name else ""
        if vendor.ocd_sale_mode == "ocd":
            return {
                "url": whatsapp_url(
                    common.company().phone,
                    request.env._("Hello, I have a question about the boutique of %s.", vendor.name),
                ),
                "label": request.env._("A question? Write to OCD Live"),
                "note": request.env._("You pay on the website, OCD delivers to your door."),
            }
        return {
            "url": f"/ocd/boutique/{vendor.id}/ecrire" if whatsapp_url(vendor.phone, "-") else False,
            "label": request.env._("Write to %s on WhatsApp", first_name),
            "note": request.env._("Payment and delivery are agreed with %s.", first_name),
        }

    def _location(self, vendor):
        """The city and the district of the vendor: never their landmark, which is the address
        where they receive the couriers (their home, when they sell from home). The stores show
        their own landmark."""
        return ", ".join(part for part in (vendor.city, vendor.district_id.name) if part)

    def _stores(self, vendor):
        """The places of the vendor the customers see (VitrineMagasins): a store with its front,
        open or closed at its hour, its hours, the itinerary, call, WhatsApp; a home with its
        district and WhatsApp only. And the line under the name: « 2 stores in Douala »."""
        env = request.env
        places = env["ocd.vendor.place"]._ocd_shown_places(vendor)
        vendor_digits = re.sub(r"\D", "", vendor.phone or "")
        rows = []
        for place in places:
            store = place.kind == "store"
            digits = re.sub(r"\D", "", place.phone or "") if store else ""
            chat = digits or vendor_digits
            text = (env._("Hello, I saw your store %s on OCD Live.", place.name) if store
                    else env._("Hello, I saw your boutique on OCD Live: when can I come by?"))
            rows.append({
                "place": place,
                "store": store,
                "title": place.name if store else place._ocd_area(),
                "address": place._ocd_address_line() if store else env._("By appointment: write before you come."),
                "photo": place_photo_url(place, 512) if store else False,
                "open": place._ocd_open_state() if store else False,
                "hours": place._ocd_hours_lines() if store else [],
                "directions": place._ocd_directions_url() if store else False,
                "call": f"tel:+{digits or vendor_digits}" if store and len(digits or vendor_digits) >= 8 else False,
                "whatsapp": f"https://wa.me/{chat}?text={url_quote(text)}" if len(chat) >= 8 else False,
            })
        stores = [row for row in rows if row["store"]]
        cities = {row["place"].city_id.name for row in stores if row["place"].city_id}
        if not stores:
            line = False
        elif len(cities) == 1:
            city = cities.pop()
            line = env._("1 store in %s", city) if len(stores) == 1 else env._("%(count)s stores in %(city)s", count=len(stores), city=city)
        else:
            line = env._("%s stores", len(stores))
        return rows, line

    @http.route(
        "/ocd/boutique/<int:vendor_id>", type="http", auth="public", website=True, sitemap=False,
        ocd_cache=15, ocd_cache_hit="_count_live_visit",
    )
    def boutique(self, vendor_id, noted=None, error=None, **kwargs):
        vendor = self._vendor(vendor_id)
        live = self._count_live_visit(vendor.id)
        next_live = self._next_live(vendor) if not live else False
        replay = self._last_replay(vendor) if not live else False
        on_screen = live.current_product_tmpl_id if live else False
        visitor = common.current_vendor()
        stores, stores_line = self._stores(vendor)
        products = self._products(vendor)
        price_by_id = shop_common.prices(products)
        promo_by_id = shop_common.promos(products)
        country = vendor.country_id
        categories = " · ".join(part for part in (vendor.ocd_category_id.name, vendor.ocd_business) if part)
        # « New » (chantier 1): put on sale this week; from the message of the news, its products
        # first
        news_first = bool(kwargs.get("nouveautes"))
        news_ids = set(vendor.sudo().ocd_news_product_ids.ids) if news_first else set()
        cards = [shop_common.card(product, price_by_id, promo_by_id) for product in products]
        for card in cards:
            card["new"] = card["product"].id in news_ids or card["product"]._ocd_is_new()
        if news_first:
            cards.sort(key=lambda card: card["product"].id not in news_ids)
        return request.render("ocd_live_shop.boutique", common.page_values(
            "boutique",
            nav="lives",
            back=f"/lives/{country.code.lower()}" if country else "/lives",
            header_title=request.env._("Boutique"),
            header_share=request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}",
            vendor=vendor,
            initials=common.initials(vendor.name),
            categories=categories,
            sold_by_ocd=vendor.ocd_sale_mode == "ocd",
            flag=country.code.lower() if country else False,
            location=self._location(vendor),
            stores=stores,
            stores_line=stores_line,
            live=self._live_info(live) if live else False,
            on_screen=self._product_card(on_screen) if on_screen else False,
            next_live=self._next_info(next_live) if next_live else False,
            replay=self._replay_info(replay) if replay else False,
            contact=self._contact(vendor),
            cards=cards,
            visitor=visitor,
            noted=bool(noted),
            **self._review_values(vendor),
            **self._follow_values(vendor, f"/ocd/boutique/{vendor.id}", noted=bool(noted)),
            count_label=request.env._("%s products", len(products)) if len(products) != 1 else request.env._("1 product"),
            error=error,
            dial_rows=common.dial_rows(visitor.country_id if visitor else common.default_country()),
            holiday=shop_common.holiday(vendor),
        ))

    @http.route("/ocd/boutique/<int:vendor_id>/prevenir", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def boutique_alert(self, vendor_id, phone=None, country_id=None, replay=None, **post):
        """The form « Tell me on WhatsApp » of before (a page kept by a browser): the visitor
        follows the lives of the vendor (chantier 1), not their news, never asked here."""
        vendor = self._vendor(vendor_id)
        if post.get("website_url"):
            raise request.not_found()
        Follower = request.env["ocd.vendor.follower"].sudo().with_company(common.company())
        live = int(replay) if replay and str(replay).isdigit() else None

        def again(**values):
            if live:
                return self.boutique_replay(vendor_id, live=live, **values)
            return self.boutique(vendor_id, **values)

        try:
            partner = visitor_partner()
            if not partner:
                country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists()
                number = common.normalize_phone(country, phone)
                if not number:
                    return again(error=common.phone_error(country))
                partner = Follower._ocd_contact(number)
            follower = Follower._ocd_follow(vendor, partner, lives=True, news=False, source="replay" if live else "boutique")
        except (UserError, ValidationError) as exc:
            return again(error=exc.args[0])
        if not visitor_partner():
            remember_follow(follower)
        if live:
            return request.redirect(f"/ocd/boutique/{vendor.id}/replay?live={live}&noted=1#prevenir")
        return request.redirect(f"/ocd/boutique/{vendor.id}?noted=1")

    @http.route("/ocd/boutique/<int:vendor_id>/retour", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def boutique_back_alert(self, vendor_id, phone=None, country_id=None, produit=None, **post):
        """« Tell me when they are back »: a WhatsApp message when the vendor is back from
        holiday (from the boutique, or from a product: `produit`, where the visitor comes back)."""
        vendor = self._vendor(vendor_id)
        if post.get("website_url"):
            raise request.not_found()
        product = request.env["product.template"].sudo().browse(int(produit)).exists() \
            if produit and str(produit).isdigit() else request.env["product.template"]
        if product and product.ocd_vendor_id != vendor:
            raise request.not_found()
        back = product.website_url if product else f"/ocd/boutique/{vendor.id}"
        Alert = request.env["ocd.boutique.alert"].sudo().with_company(common.company())
        visitor = common.current_vendor()
        try:
            if visitor:
                Alert._ocd_register(vendor, partner=visitor, kind="back")
            else:
                country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists()
                number = common.normalize_phone(country, phone)
                if not number:
                    return request.redirect(f"{back}?{urlencode({'erreur_retour': common.phone_error(country)})}#vacances")
                Alert._ocd_register(vendor, phone=number, kind="back")
        except (UserError, ValidationError) as exc:
            return request.redirect(f"{back}?{urlencode({'erreur_retour': exc.args[0]})}#vacances")
        return request.redirect(f"{back}?retour=1#vacances")

    @http.route("/ocd/boutique/<int:vendor_id>/ecrire", type="http", auth="public", website=True, sitemap=False)
    def boutique_whatsapp(self, vendor_id, **kwargs):
        """Open WhatsApp with the vendor who sells directly."""
        vendor = self._vendor(vendor_id)
        url = whatsapp_url(vendor.phone, request.env._("Hello, I saw your boutique on OCD Live."))
        if not url:
            raise request.not_found()
        request.env["ocd.vendor.count"]._ocd_add(vendor, "contact")
        return request.redirect(url, local=False)

    @http.route("/ocd/boutique/<int:vendor_id>/live", type="jsonrpc", auth="public", website=True, ocd_cache=10)
    def boutique_live(self, vendor_id):
        """Product shown now during the live, read by the boutique every 20 seconds."""
        vendor = self._vendor(vendor_id)
        product = self._current_live(vendor).current_product_tmpl_id
        if not product:
            return {"id": False}
        card = self._product_card(product)
        return {
            "id": product.id,
            "name": product.name,
            "url": card["url"],
            "price": card["price"],
            "was": card.get("was") or False,
            "image": product._ocd_image_url("image_128"),
        }

    @http.route(
        "/ocd/boutique/<int:vendor_id>/replay", type="http", auth="public", website=True, sitemap=False,
        ocd_cache=60, ocd_cache_params=("live", "t"),
    )
    def boutique_replay(self, vendor_id, live=None, t=None, noted=None, error=None, **kwargs):
        """A live again (the last one, or `live`), with the moments where each product is shown.
        The video plays in the page when its platform allows it, and a product touched goes to
        its moment; `t` starts the video at a second (link « watch the moment » of a product)."""
        vendor = self._vendor(vendor_id)
        replay = self._replay_of(vendor, live)
        if not replay:
            return request.redirect(f"/ocd/boutique/{vendor.id}")
        local = common.to_viewer(replay.start_datetime)
        minutes = (replay.end_datetime - replay.start_datetime).total_seconds() // 60
        if replay.mode == "studio":
            how = request.env._("at the OCD Live studio")
        elif replay.animatrice_id:
            how = request.env._("from home, with the OCD host")
        else:
            how = request.env._("from home")
        name = platform(replay.replay_url)
        embed = replay._ocd_replay_embed()
        start = int(t) if t and str(t).isdigit() else 0
        rows = []
        for moment in replay.moment_ids.sorted("offset_seconds"):
            product = moment.product_tmpl_id
            if not (product.is_published and product.ocd_review_state == "approved"):
                continue
            variant = moment._ocd_variant_query()
            rows.append({
                "moment": moment,
                "product": product,
                "see_url": f"{product.website_url}{variant}",
                "price": self._price(product),
                "url": replay._ocd_replay_url_at(moment.offset_seconds),
                "seconds": moment.offset_seconds,
                "on": bool(start) and moment.offset_seconds <= start,
                "image": product._ocd_image_url("image_128"),
                "order_label": request.env._("Order “%s”", product.name)
                if vendor.ocd_sale_mode == "ocd" else
                request.env._("Write to %(name)s about “%(product)s”", name=(vendor.name or "").split()[0], product=product.name),
                "order_url": f"{product.website_url}{variant}" if vendor.ocd_sale_mode == "ocd" else f"/ocd/wa/{product.id}",
                "aria": request.env._("Go to %(time)s: %(product)s", time=moment.offset_label, product=product.name),
                "see_aria": request.env._("See the product: %s", product.name),
            })
        # The product on screen at the start: the last one shown before `t`
        current = [row for row in rows if row["on"]]
        for row in rows:
            row["on"] = bool(current) and row is current[-1]
        if rows and not current:
            rows[0]["on"] = True
        seconds = max(int((replay.end_datetime - replay.start_datetime).total_seconds()), 1)
        shown = next((row for row in rows if row["on"]), None)
        fill = round(min(shown["seconds"] / seconds, 1) * 100, 2) if shown else 0
        place = " · ".join(part for part in (vendor.ocd_category_id.name, vendor.city) if part)
        visitor = common.current_vendor()
        replay_url = request.httprequest.url_root.rstrip("/") + f"/ocd/boutique/{vendor.id}/replay?live={replay.id}"
        return request.render("ocd_live_shop.replay", common.page_values(
            False,
            back=f"/ocd/boutique/{vendor.id}",
            back_label=request.env._("Back to the boutique"),
            header_title=request.env._("Watch the live again"),
            header_share=replay_url,
            vendor=vendor,
            replay=replay,
            embed=embed,
            start=start,
            fill=fill,
            total_seconds=seconds,
            marks=[
                {"left": round(min(row["seconds"] / seconds, 1) * 100, 2), "seconds": row["seconds"], "label": row["moment"].offset_label}
                for row in rows
            ],
            open_label=request.env._("Open on %s", name) if name else request.env._("Open the video"),
            moments_hint=request.env._("Tap a product: the video goes to its moment.") if embed["seek"]
            else request.env._("The video opens on %s: go to the time of the product.", name or request.env._("its site")),
            visitor=visitor,
            noted=bool(noted),
            error=error,
            dial_rows=common.dial_rows(visitor.country_id if visitor else common.default_country()),
            first_name=(vendor.name or "").split()[0] if vendor.name else "",
            **self._follow_values(vendor, f"/ocd/boutique/{vendor.id}/replay?live={replay.id}#prevenir", "replay", bool(noted)),
            title=request.env._("Live of %s", vendor.name),
            banner=" · ".join(part for part in (vendor.name, place) if part),
            shop_line=request.env._("Their boutique on OCD Live"),
            published_on=request.env._("Video published on %s", name) if name else request.env._("Video of the live"),
            duration=clock_text(minutes),
            line=" · ".join([
                tools.day_text(request.env, local.date(), "EEE d MMM", capital=True),
                duration_text(minutes),
                how,
            ]),
            rows=rows,
        ))

    @http.route("/ocd/wa/<int:product_id>", type="http", auth="public", website=True, sitemap=False)
    def whatsapp(self, product_id, **kwargs):
        """Count the contact, then open WhatsApp with the vendor."""
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or not product.ocd_vendor_id or product.ocd_review_state != "approved":
            raise request.not_found()
        if product.ocd_vendor_id._ocd_on_holiday():
            # The orders are paused: the page says until when (chantier 20)
            return request.redirect(f"{product.website_url}#vacances")
        chosen = []
        for line in product.valid_product_template_attribute_line_ids:
            value = kwargs.get(f"attribute_{line.id}")
            if value and str(value).isdigit():
                ptav = line.product_template_value_ids.filtered(lambda v: v.id == int(value))
                if ptav:
                    chosen.append(f"{line.attribute_id.name} {ptav.name}")
        link = request.httprequest.url_root.rstrip("/") + product.website_url if chosen else None
        url = product._ocd_whatsapp_url(chosen, link)
        if not url:
            raise request.not_found()
        product.ocd_wa_clicks += 1
        # Day by day, for the figures of the vendor (chantier 3)
        request.env["ocd.vendor.count"]._ocd_add(product.ocd_vendor_id, "contact", product.id)
        return request.redirect(url, local=False)
