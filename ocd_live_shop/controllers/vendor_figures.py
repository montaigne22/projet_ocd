from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from .vendor_products import vendor_photo_url

# How far « Book a live » looks for the day and the hour proposed
BOOK_WEEKS = 4


class OcdVendorFigures(http.Controller):
    """« My figures » (chantier 3 of the roadmap, design MesChiffres): the sales and the pieces for
    every vendor; with OCD Business (offered during the launch), the period, the visits, the
    WhatsApp contacts, the lives, the best hours, the loyal customers, the sales per product (3.3)
    and the stores. The calculation is the model ocd.vendor.figures, the same for « My space »,
    « My products » and the summary of the week."""

    @http.route("/ocd/espace/<string:token>/chiffres", type="http", auth="public", website=True, methods=["GET"],
                sitemap=False)
    def figures_link(self, token, **kwargs):
        """The button of the summary of the week on WhatsApp: the personal link opens the space on
        the phone, then « My figures ». (« moi » takes the route below.)"""
        vendor = common.current_vendor(token)
        if not vendor:
            return request.redirect("/ocd/connexion")
        return request.redirect("/ocd/espace/moi/chiffres")

    @http.route("/ocd/espace/moi/chiffres", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def figures(self, periode=None, vue=None, resume=None, **kwargs):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        Figures = env["ocd.vendor.figures"]
        days = Figures._ocd_period(periode)
        business = vendor._ocd_business()
        figures = Figures._ocd_figures(vendor, days if business else 30, detail=business)
        view = "unsold" if vue == "pas-vendus" else "best"
        values = {
            "vendor": vendor,
            "figures": figures,
            "business": business,
            "sold_by_ocd": vendor.ocd_sale_mode == "ocd",
            "periods": [
                {"days": value, "label": label, "url": self._url(value, vue), "on": value == figures["days"]}
                for value, label in ((7, env._("7 days")), (30, env._("30 days")), (90, env._("3 months")))
            ],
            "period_label": {7: env._("7 days"), 90: env._("3 months")}.get(figures["days"], env._("30 days")),
            "message": {
                "1": env._("Done: your week arrives on WhatsApp on Monday morning."),
                "0": env._("Done: no more summary on WhatsApp."),
            }.get(resume),
        }
        if business:
            products = figures["products"]
            unsold = [row for row in products if not row["pieces"]]
            unsold.sort(key=lambda row: -row["contacts"])
            values.update({
                "view": view,
                "product_rows": [
                    dict(row, image=vendor_photo_url(row["product"], "image_128"))
                    for row in (unsold if view == "unsold" else products)[:60]
                ],
                "best_url": self._url(figures["days"], None) + "#produits",
                "unsold_url": self._url(figures["days"], "pas-vendus") + "#produits",
                "unsold_count": len(unsold),
                "next_live": self._next_live(vendor),
                "book_url": self._book_url(vendor, figures["hours"]["book"]),
                "lives_title": self._lives_title(figures["days"], len(figures["lives"])),
            })
        return request.render("ocd_live_shop.vendor_figures", common.page_values(
            False,
            space_page="figures",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My figures"),
            **values,
        ))

    def _url(self, days, view):
        url = f"/ocd/espace/moi/chiffres?periode={days}"
        return f"{url}&vue={view}" if view else url

    def _lives_title(self, days, count):
        env = request.env
        if days == 7:
            return env._("1 these 7 days") if count == 1 else env._("%s these 7 days", count)
        if days == 90:
            return env._("1 these 3 months") if count == 1 else env._("%s these 3 months", count)
        return env._("1 these 30 days") if count == 1 else env._("%s these 30 days", count)

    def _next_live(self, vendor):
        return request.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", vendor.id), ("state", "in", ("draft", "confirmed")),
            ("end_datetime", ">", fields.Datetime.now()),
        ], order="start_datetime", limit=1)

    def _book_url(self, vendor, book):
        """« Book a live on Saturday at 19:00 »: the booking opens on the next such day, on the hour
        when the studio has it (at the hour of the vendor), else on the day."""
        if not book:
            return False
        last = request.env["ocd.live.booking"].sudo().search([("partner_id", "=", vendor.id)], order="id desc", limit=1)
        mode = last.mode if last.mode in common.MODES else "studio"
        company = common.company()
        tz_name = vendor._ocd_tz_name()
        day = common.first_bookable_day()
        fallback = False
        for _offset in range(7 * BOOK_WEEKS):
            for start in company._ocd_slot_starts(day):
                local = tools.to_tz(start, tz_name)
                if local.weekday() == book["weekday"] and local.hour == book["hour"] and local.minute == 0:
                    return f"/reserver/{mode}/{day.isoformat()}/{company._ocd_to_local(start):%H%M}"
            if not fallback and day.weekday() == book["weekday"]:
                fallback = f"/reserver/{mode}/{day.isoformat()}"
            day += timedelta(days=1)
        return fallback or f"/reserver/{mode}"

    @http.route("/ocd/espace/moi/chiffres/resume", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def week_summary(self, actif=None, **post):
        """« Receive the summary of my week »: on WhatsApp on Monday, only when asked for."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        on = actif == "1"
        vendor.sudo().ocd_week_summary = on
        return request.redirect(f"/ocd/espace/moi/chiffres?resume={'1' if on else '0'}#resume")

    @http.route("/ocd/espace/moi/chiffres/live/<int:product_id>", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def add_to_live(self, product_id, **post):
        """« Add to my next live »: the product goes to the end of the products prepared for the
        next live (chantier 21), then its page opens to put it in order; no live booked: the page
        says so."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor:
            raise request.not_found()
        booking = self._next_live(vendor)
        if not booking:
            return request.redirect("/ocd/espace/moi/live")
        chosen = booking._ocd_prepared_products()
        if product not in chosen:
            try:
                booking._ocd_prepare(chosen | product, booking.ocd_host_note)
            except UserError:
                pass  # the page of the live says why
        return request.redirect(f"/ocd/espace/moi/live/{booking.id}")
