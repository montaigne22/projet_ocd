"""The pages of the big events (chantier 7, design ProgrammeSoirees): the events, an event
(countdown, its programme day by day, its promos, « Tell me on WhatsApp »), and for a vendor
invited: « Join » (their live during the event and their promos of the event). The pages were first
at /soirees: these addresses lead to /evenements."""
from datetime import timedelta
from urllib.parse import urlencode

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live_shop.controllers import shop_common
from odoo.addons.ocd_live_shop.controllers.programme import DAYS, OcdProgramme
from odoo.addons.ocd_live_shop.controllers.vendor_follow import follow_url, visitor_follows, visitor_partner
from odoo.addons.ocd_live_shop.controllers.vendor_products import vendor_photo_url
from odoo.addons.ocd_live_shop.controllers.vendor_promo import promo_amount

# The discounts offered for each product of a participation (cut at the discount at most)
PERCENTS = (10, 20, 30, 40, 50)


def evening_or_404(slug):
    evening = request.env["ocd.evening"].sudo().search([("slug", "=", slug)], limit=1)
    if not evening or not evening._ocd_public():
        raise request.not_found()
    return evening


def visitor_money(amount, company):
    """An amount of the company in the currency of the visitor, rounded as the pricelists."""
    currency = shop_common.currency()
    if currency and currency != company.currency_id:
        amount = company.currency_id._convert(amount, currency, company, fields.Date.today())
        amount = round(amount)
    return common.money(amount, currency or company.currency_id)


class OcdEveningPages(http.Controller):

    @http.route(["/soirees", "/soirees/<path:rest>", "/ocd/espace/moi/soirees/<int:evening_id>"], type="http",
                auth="public", website=True, sitemap=False, methods=["GET"])
    def old_address(self, rest="", evening_id=None, **kwargs):
        """The first addresses of the pages (/soirees): to the ones of now."""
        if evening_id:
            return request.redirect(f"/ocd/espace/moi/evenements/{evening_id}", code=301)
        query = request.httprequest.query_string.decode()
        return request.redirect("/evenements" + (f"/{rest}" if rest else "") + (f"?{query}" if query else ""), code=301)

    @http.route("/evenements", type="http", auth="public", website=True, sitemap=True, ocd_cache=30)
    def evenings(self, **kwargs):
        tz_name = common.viewer_tz()
        rows = [{
            "evening": evening,
            "kicker": evening._ocd_kicker(),
            "when": evening._ocd_when_text(tz_name, "EEE d MMM"),
            "image": evening._ocd_image_url(),
            "running": evening._ocd_running(),
        } for evening in request.env["ocd.evening"]._ocd_shown()]
        return request.render("ocd_soirees.evenings", common.page_values(
            False, nav="lives", back="/lives/programme", header_title=request.env._("Big events"), rows=rows,
        ))

    def _programme_groups(self, evening, tz_name, back):
        """The lives of the event; for several days, by day (« Saturday 5 December »), each day with
        its link to the programme of the lives (the next 7 days)."""
        env = request.env
        rows = self._programme_rows(evening, tz_name, back)
        today = tools.to_tz(common.now(), tz_name).date()

        def lives_url(day):
            if not today <= day < today + timedelta(days=DAYS):
                return False
            return f"/lives/programme?{urlencode({'jour': day.isoformat(), 'pays': 'tous'})}"

        if evening._ocd_one_day():
            day = evening._ocd_local(evening.date_start, tz_name).date()
            return [{"title": False, "rows": rows, "lives_url": lives_url(day)}] if rows else []
        groups = {}
        for row in rows:
            group = groups.setdefault(row["day"], {
                "title": tools.day_text(env, row["day"], "EEEE d MMMM", capital=True),
                "rows": [],
                "lives_url": lives_url(row["day"]),
            })
            group["rows"].append(row)
        return list(groups.values())

    def _programme_rows(self, evening, tz_name, back):
        env = request.env
        followed = {follow.vendor_id.id for follow in visitor_follows() if follow.active and follow.lives}
        rows = []
        for booking in evening._ocd_lives():
            vendor = booking.partner_id
            best = evening._ocd_best_discount(vendor)
            local = tools.to_tz(booking.start_datetime, tz_name)
            rows.append({
                "day": local.date(),
                "hour": f"{local:%H:%M}",
                "name": vendor.name,
                "initials": common.initials(vendor.name),
                "line": " · ".join(part for part in (
                    vendor.ocd_category_id.name, env._("up to -%s %%", best) if best else "",
                ) if part),
                "boutique_url": f"/ocd/boutique/{vendor.id}",
                "followed": vendor.id in followed,
                "follow_url": follow_url(vendor, back=back, source="evening"),
                "bell_label": env._("%s: told at each live", vendor.name) if vendor.id in followed
                else env._("Tell me when %s is live", vendor.name),
                "live": booking.start_datetime <= common.now() < booking.end_datetime,
            })
        return rows

    def _promo_cards(self, evening, category):
        promos = evening.promo_ids.filtered(lambda promo: promo.active and not promo.stopped_at).sorted(
            lambda promo: (-promo.discount, promo.id))
        products = promos.product_tmpl_id.filtered(
            lambda product: product.is_published and product.sale_ok and product.ocd_review_state == "approved"
            and (not category or product.ocd_vendor_id.ocd_category_id == category)
        )
        price_by_id = shop_common.prices(products)
        running = evening._ocd_running()
        cards = []
        for promo in promos.filtered(lambda promo: promo.product_tmpl_id in products):
            product = promo.product_tmpl_id
            card = shop_common.card(product, price_by_id, {})
            # Before the event: its price of the event, « From 18:00 »
            card.update({
                "price": card["price"] if running else visitor_money(promo.price, evening.company_id),
                "was": visitor_money(promo.reference_price, evening.company_id),
                "off": promo._ocd_off_text(),
                "soon": not running,
                "by": product.ocd_vendor_id.name,
            })
            cards.append(card)
        return cards

    @http.route("/evenements/<string:slug>", type="http", auth="public", website=True, sitemap=False, ocd_cache=15,
                ocd_cache_params=("categorie", "prevenu"))
    def evening(self, slug, categorie=None, prevenu=None, **kwargs):
        evening = evening_or_404(slug)
        env = request.env
        tz_name = common.viewer_tz() or evening.tz
        now = common.now()
        categories = env["ocd.live.category"].sudo().search([])
        category = categories.filtered(lambda c: str(c.id) == str(categorie))[:1]
        back = evening._ocd_public_path()
        groups = self._programme_groups(evening, tz_name, back)
        cards = self._promo_cards(evening, category)
        running, passed = evening._ocd_running(now), evening._ocd_passed(now)
        number = common.company().phone or ""
        if running:
            state_line = env._("Now, until %s", evening._ocd_until_text(tz_name))
        elif passed:
            state_line = env._("This event is over: see you at the next one.")
        else:
            state_line = False
        return request.render("ocd_soirees.evening", common.page_values(
            False,
            nav="lives",
            back="/evenements",
            header_title=evening.name,
            header_share=request.httprequest.url_root.rstrip("/") + evening._ocd_public_path(),
            evening=evening,
            kicker=evening._ocd_kicker(),
            image=evening._ocd_image_url(),
            when=evening._ocd_when_text(tz_name) if evening._ocd_one_day() else evening._ocd_when_sentence(tz_name, capital=True),
            zone=tools.zone_text(env, tz_name),
            countries=evening._ocd_countries_text(),
            running=running,
            passed=passed,
            state_line=state_line,
            tiles=[
                (evening._ocd_left_text(now), env._("before")) if not running and not passed else
                (env._("Now") if running else "-", env._("live") if running else ""),
                (evening._ocd_number(evening.vendor_count), env._("vendor") if evening.vendor_count == 1 else env._("vendors")),
                (evening._ocd_number(len(cards)), env._("promo") if len(cards) == 1 else env._("promos")),
            ],
            groups=groups,
            cards=cards,
            categories=[{"label": env._("All"), "href": back, "on": not category}] + [
                {"label": c.name, "href": f"{back}?categorie={c.id}", "on": c == category} for c in categories
                if c in evening.participation_ids.filtered(lambda p: p.state == "approved").vendor_id.ocd_category_id
            ],
            alert_noted=bool(prevenu),
            alert_known=bool(visitor_partner()),
            dial_rows=common.dial_rows(common.default_country()),
            report_url=tools.whatsapp_url(number, env._("Hello, about the big event %s of OCD Live.", evening.name)),
            soon_line=env._("From %s", evening._ocd_start_short(tz_name)),
        ))

    @http.route("/evenements/<string:slug>/prevenir", type="http", auth="public", website=True, sitemap=False,
                methods=["POST"])
    def evening_alert(self, slug, phone=None, country_id=None, **post):
        """« Tell me on WhatsApp »: a message a little before the start (setting)."""
        evening = evening_or_404(slug)
        if post.get("website_url"):
            raise request.not_found()  # a robot filled the hidden field
        partner = visitor_partner()
        if not partner:
            country = request.env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
            number = common.normalize_phone(country, phone)
            if not number:
                return request.redirect(f"{evening._ocd_public_path()}#prevenir")
            partner = request.env["ocd.vendor.follower"].sudo()._ocd_contact(number)
            if not partner.country_id:
                partner.country_id = country
        Alert = request.env["ocd.evening.alert"].sudo()
        if not evening._ocd_passed() and not Alert.search_count(
                [("evening_id", "=", evening.id), ("partner_id", "=", partner.id)]):
            Alert.create({"evening_id": evening.id, "partner_id": partner.id})
            partner._ocd_agree_by_following()
        return request.redirect(f"{evening._ocd_public_path()}?prevenu=1#prevenir")

    @http.route("/evenements/image/<int:evening_id>", type="http", auth="public", website=True, sitemap=False)
    def evening_image(self, evening_id, v=None, **kwargs):
        evening = request.env["ocd.evening"].sudo().browse(evening_id).exists()
        if not evening or not evening.image or not evening._ocd_public():
            raise request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(evening, "image", width=1280, height=720)
        return common.media_response(stream, True, version=v)

    # === THE VENDOR JOINS === #

    def _vendor_evening(self, evening_id):
        vendor = common.current_vendor()
        if not vendor:
            return None, None
        evening = request.env["ocd.evening"].sudo().browse(evening_id).exists()
        if not evening or not evening._ocd_public() or not evening._ocd_invites(vendor):
            raise request.not_found()
        return vendor, evening

    def _render_join(self, vendor, evening, error=None, chosen=None):
        env = request.env
        Participation = env["ocd.evening.participation"].sudo()
        participation = Participation.search([("evening_id", "=", evening.id), ("vendor_id", "=", vendor.id)], limit=1)
        tz_name = vendor._ocd_tz_name() or evening.tz
        live = participation.booking_id if participation else Participation.new({
            "evening_id": evening.id, "vendor_id": vendor.id,
        }).booking_id
        current = {promo.product_tmpl_id.id: promo.discount
                   for promo in participation.promo_ids.filtered(lambda promo: not promo.stopped_at)} if participation else {}
        chosen = chosen if chosen is not None else current
        products = env["product.template"].sudo().search([
            ("ocd_vendor_id", "=", vendor.id), ("is_published", "=", True), ("sale_ok", "=", True),
            ("ocd_review_state", "=", "approved"),
        ], order="website_sequence, id")
        percents = [p for p in PERCENTS if p <= evening.max_discount]
        rows = []
        for product in products:
            reference = product._ocd_reference_price()
            options = [{
                "value": str(p),
                "label": env._("-%(percent)s %% · %(price)s", percent=p,
                               price=common.money(promo_amount(reference, p, product.currency_id), product.currency_id)),
                "selected": chosen.get(product.id) and abs(chosen[product.id] - p) < 5,
            } for p in percents]
            rows.append({
                "product": product,
                "image": vendor_photo_url(product, "image_128"),
                "price": common.money(reference, product.currency_id),
                "options": options,
                "on": bool(chosen.get(product.id)),
            })
        # The booking opens on the first day of the event still to come
        today = tools.to_tz(common.now(), evening.tz).date()
        day = max(evening._ocd_local(evening.date_start).date(), today).isoformat()
        local_live = tools.to_tz(live.start_datetime, tz_name) if live else None
        return request.render("ocd_soirees.join", common.page_values(
            False,
            space_page="space",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My space"),
            vendor=vendor,
            evening=evening,
            participation=participation,
            state_line=participation._ocd_state_line() if participation else False,
            open=evening._ocd_registration_open(),
            when=evening._ocd_when_text(tz_name),
            until_line=env._("Registrations until %s.", evening._ocd_registration_day(tz_name)),
            live_line=env._("Your live: %(hour)s, %(where)s.", hour=evening._ocd_hour(local_live) if evening._ocd_one_day()
                            else env._("%(day)s at %(hour)s", day=tools.day_text(env, local_live.date(), "EEEE d MMMM"),
                                       hour=evening._ocd_hour(local_live)),
                            where=env._("at the studio") if live.mode == "studio" else env._("remote"))
            if live else False,
            studio_url=f"/reserver/studio/{day}",
            remote_url=f"/reserver/remote/{day}",
            hours_line=env._("%s, at the studio or remote, at the usual price of a live: the usual booking, with your ticket.",
                             evening._ocd_when_sentence(tz_name, capital=True)),
            rows=rows,
            max_line=env._("%s %% of discount at most, from your lowest price of the last days.", evening.max_discount),
            error=error,
        ))

    @http.route("/ocd/espace/moi/evenements/<int:evening_id>", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def join_page(self, evening_id, **kwargs):
        vendor, evening = self._vendor_evening(evening_id)
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render_join(vendor, evening)

    @http.route("/ocd/espace/moi/evenements/<int:evening_id>", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def join(self, evening_id, **post):
        vendor, evening = self._vendor_evening(evening_id)
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        Product = env["product.template"].sudo()
        prices, chosen = {}, {}
        for key, value in post.items():
            if not key.startswith("p_") or not key[2:].isdigit() or not str(value or "").isdigit() or not int(value):
                continue
            product = Product.browse(int(key[2:])).exists()
            if not product or product.ocd_vendor_id != vendor:
                continue
            percent = min(int(value), evening.max_discount)
            chosen[product.id] = percent
            prices[product] = promo_amount(product._ocd_reference_price(), percent, product.currency_id)
        Participation = env["ocd.evening.participation"].sudo()
        live = Participation.new({"evening_id": evening.id, "vendor_id": vendor.id}).booking_id
        try:
            if not prices and not live:
                raise UserError(env._("Book your live during the event or choose at least one promo."))
            Participation._ocd_submit(evening, vendor, prices)
        except (UserError, ValidationError) as exc:
            return self._render_join(vendor, evening, error=exc.args[0], chosen=chosen)
        return request.redirect(f"/ocd/espace/moi/evenements/{evening.id}")


class OcdEveningProgramme(OcdProgramme):
    """The big events on the programme of the lives: the band, each day of the event."""

    def _ocd_evening_days(self, first, last, tz_name):
        days = super()._ocd_evening_days(first, last, tz_name)
        for evening in request.env["ocd.evening"]._ocd_shown():
            for day in evening._ocd_days(tz_name):
                if first <= day <= last:
                    days.setdefault(day, evening.name)
        return days

    def _ocd_evening_band(self, day, tz_name):
        """The event of the day shown, or else the next one."""
        evenings = request.env["ocd.evening"]._ocd_shown()
        if not evenings:
            return super()._ocd_evening_band(day, tz_name)
        evening = evenings.filtered(lambda e: day in e._ocd_days(tz_name))[:1] or evenings[:1]
        env = request.env
        best = evening._ocd_best_discount()
        return {
            "url": evening._ocd_public_path(),
            "kicker": evening._ocd_kicker(),
            "name": evening.name,
            "line": " · ".join(part for part in (
                evening._ocd_when_text(tz_name, "EEE d MMM"),
                (env._("1 vendor in live") if evening.vendor_count == 1 else env._("%s vendors in live", evening.vendor_count))
                if evening.vendor_count else "",
                env._("up to -%s %%", best) if best else "",
            ) if part),
        }
