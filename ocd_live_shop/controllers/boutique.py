import re
from urllib.parse import quote as url_quote
from urllib.parse import urlparse

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from . import shop_common

# Platforms of the lives, recognised from the link of the live
PLATFORMS = {
    "tiktok.com": "TikTok",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
}


def platform(url):
    """Return the name of the platform of a live link ("TikTok"), or ""."""
    host = (urlparse(url or "").hostname or "").lower()
    for domain, name in PLATFORMS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return ""


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

    def _price(self, product):
        return shop_common.prices(product).get(product.id) or common.money(product.list_price, product.currency_id)

    def _product_card(self, product):
        """What the boutique shows of a product: price, photo and stock, as in the shop."""
        return shop_common.card(product, shop_common.prices(product))

    def _live_info(self, live):
        name = platform(live.live_url)
        minutes = max(1, int((fields.Datetime.now() - live.start_datetime).total_seconds() // 60))
        since = duration_text(minutes)
        return {
            "booking": live,
            "line": request.env._("For %(since)s, on %(platform)s", since=since, platform=name)
            if name else request.env._("Live for %s", since),
        }

    def _next_info(self, booking):
        local = common.to_viewer(booking.start_datetime)
        name = platform(booking.live_url)
        if name:
            where = request.env._("On %s", name)
        elif booking.mode == "studio":
            where = request.env._("At the OCD Live studio")
        else:
            where = request.env._("From home, with OCD Live")
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
        place = ", ".join(part for part in (vendor.city, vendor.district_id.name) if part)
        if vendor.delivery_landmark:
            place = " · ".join(part for part in (place, vendor.delivery_landmark) if part)
        return place

    @http.route("/ocd/boutique/<int:vendor_id>", type="http", auth="public", website=True, sitemap=False)
    def boutique(self, vendor_id, noted=None, error=None, **kwargs):
        vendor = self._vendor(vendor_id)
        live = self._current_live(vendor)
        if live:
            # One visit per browser and per live, shown in the control room
            seen = request.session.get("ocd_live_visits", [])
            if live.id not in seen:
                live._ocd_count_visit()
                request.session["ocd_live_visits"] = (seen + [live.id])[-20:]
        next_live = self._next_live(vendor) if not live else False
        replay = self._last_replay(vendor) if not live else False
        on_screen = live.current_product_tmpl_id if live else False
        visitor = common.current_vendor()
        products = self._products(vendor)
        price_by_id = shop_common.prices(products)
        country = vendor.country_id
        categories = " · ".join(part for part in (vendor.ocd_category_id.name, vendor.ocd_business) if part)
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
            live=self._live_info(live) if live else False,
            on_screen=self._product_card(on_screen) if on_screen else False,
            next_live=self._next_info(next_live) if next_live else False,
            replay=self._replay_info(replay) if replay else False,
            contact=self._contact(vendor),
            cards=[shop_common.card(product, price_by_id) for product in products],
            visitor=visitor,
            noted=bool(noted),
            noted_text=request.env._("Noted. We write to you when %s goes live.", (vendor.name or "").split()[0]),
            count_label=request.env._("%s products", len(products)) if len(products) != 1 else request.env._("1 product"),
            error=error,
            dial_rows=common.dial_rows(visitor.country_id if visitor else common.default_country()),
        ))

    @http.route("/ocd/boutique/<int:vendor_id>/prevenir", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def boutique_alert(self, vendor_id, phone=None, country_id=None, replay=None, **post):
        """Tell the visitor on WhatsApp when the vendor goes live (from the boutique, or from a
        replay: `replay` is the live watched again, where the visitor comes back)."""
        vendor = self._vendor(vendor_id)
        if post.get("website_url"):
            raise request.not_found()
        Alert = request.env["ocd.boutique.alert"].sudo().with_company(common.company())
        visitor = common.current_vendor()
        live = int(replay) if replay and str(replay).isdigit() else None

        def again(**values):
            if live:
                return self.boutique_replay(vendor_id, live=live, **values)
            return self.boutique(vendor_id, **values)

        try:
            if visitor:
                Alert._ocd_register(vendor, partner=visitor)
            else:
                country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists()
                number = common.normalize_phone(country, phone)
                if not number:
                    return again(error=common.phone_error(country))
                Alert._ocd_register(vendor, phone=number)
        except (UserError, ValidationError) as exc:
            return again(error=exc.args[0])
        if live:
            return request.redirect(f"/ocd/boutique/{vendor.id}/replay?live={live}&noted=1#prevenir")
        return request.redirect(f"/ocd/boutique/{vendor.id}?noted=1")

    @http.route("/ocd/boutique/<int:vendor_id>/ecrire", type="http", auth="public", website=True, sitemap=False)
    def boutique_whatsapp(self, vendor_id, **kwargs):
        """Open WhatsApp with the vendor who sells directly."""
        vendor = self._vendor(vendor_id)
        url = whatsapp_url(vendor.phone, request.env._("Hello, I saw your boutique on OCD Live."))
        if not url:
            raise request.not_found()
        return request.redirect(url, local=False)

    @http.route("/ocd/boutique/<int:vendor_id>/live", type="jsonrpc", auth="public", website=True)
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
            "image": f"/web/image/product.template/{product.id}/image_128" if product.image_128 else False,
        }

    @http.route("/ocd/boutique/<int:vendor_id>/replay", type="http", auth="public", website=True, sitemap=False)
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
                "image": f"/web/image/product.template/{product.id}/image_128" if product.image_128 else False,
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
        return request.redirect(url, local=False)
