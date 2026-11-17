from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live.controllers import common


class OcdVendorHoliday(http.Controller):
    """The holiday mode of the vendor (design VacancesProximite, chantier 20): back on a day, a
    word for the customers; the products stay visible, the orders are paused."""

    def _render(self, vendor, values=None, error=None):
        env = request.env
        today = vendor._ocd_today()
        longest = vendor._ocd_holiday_max_days()
        on_holiday = vendor._ocd_on_holiday()
        return request.render("ocd_live_shop.vendor_holiday", common.page_values(
            "vacances",
            space_page="space",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("Holiday mode"),
            vendor=vendor,
            on_holiday=on_holiday,
            back_text=vendor._ocd_holiday_back_text() if on_holiday else False,
            waiting=vendor._ocd_holiday_waiting_count() if on_holiday else 0,
            values=values or {},
            error=error,
            day_min=fields.Date.to_string(today + timedelta(days=1)),
            day_max=fields.Date.to_string(today + timedelta(days=longest)),
            longest_line=env._("%s days at most. Your lives already booked do not move.", longest),
        ))

    @http.route("/ocd/espace/moi/vacances", type="http", auth="public", website=True, methods=["GET", "POST"],
                sitemap=False)
    def holiday(self, retour_le=None, mot=None, **post):
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        if request.httprequest.method != "POST":
            return self._render(vendor)
        values = {"retour_le": retour_le or "", "mot": mot or ""}
        try:
            day = fields.Date.to_date(retour_le) if retour_le else None
        except ValueError:
            day = None
        try:
            with request.env.cr.savepoint():
                vendor._ocd_start_holiday(day, mot)
        except UserError as exc:
            return self._render(vendor, values, exc.args[0])
        return request.redirect("/ocd/espace/moi/vacances?parti=1")

    @http.route("/ocd/espace/moi/vacances/fin", type="http", auth="public", website=True, methods=["POST"],
                sitemap=False)
    def holiday_end(self, **post):
        """« Come back now »: the orders start again, the customers who asked are told."""
        vendor = common.current_vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        vendor._ocd_end_holiday()
        return request.redirect("/ocd/espace/moi?revenu=1")
