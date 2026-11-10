from odoo import http
from odoo.http import request

from . import common


class OcdLiveDirectory(http.Controller):
    """Public directory of the lives of the moment, by country and by category."""

    def _published(self, domain=None):
        return request.env["ocd.directory.listing"].sudo().search(
            [("state", "=", "published"), ("window_end", ">", common.now())] + (domain or []),
            order="checked_at desc, id desc",
        )

    def _next_window_label(self):
        found = request.env["ocd.directory.window"].sudo()._ocd_find(company=common.company())
        if not found:
            return False
        _window, start, _end = found
        return common.company()._ocd_to_local(start).strftime("%H:%M")

    @http.route("/lives", type="http", auth="public", website=True, sitemap=True)
    def directory(self, **kwargs):
        listings = self._published()
        counts = {}
        for listing in listings:
            counts[listing.country_id] = counts.get(listing.country_id, 0) + 1
        countries = request.env["res.country"].sudo().search([("code", "in", ["CM", "TG", "BJ", "CI", "SN"])])
        countries |= request.env["res.country"].browse([c.id for c in counts if c])
        rows = sorted(
            ({"country": country, "count": counts.get(country, 0)} for country in countries),
            key=lambda row: (-row["count"], row["country"].name),
        )
        return request.render("ocd_live.directory_countries", common.page_values(
            "directory", rows=rows, total=len(listings), next_window=self._next_window_label(),
        ))

    @http.route("/lives/<string:code>", type="http", auth="public", website=True, sitemap=False)
    def directory_country(self, code, category=None, **kwargs):
        country = request.env["res.country"].sudo().search([("code", "=", (code or "").upper())], limit=1)
        if not country:
            raise request.not_found()
        domain = [("country_id", "=", country.id)]
        category_record = request.env["ocd.live.category"].sudo().browse(int(category)).exists() if category and category.isdigit() else None
        if category_record:
            domain.append(("category_id", "=", category_record.id))
        listings = self._published(domain)
        categories = request.env["ocd.live.category"].sudo().search([])
        return request.render("ocd_live.directory_country", common.page_values(
            "directory",
            country=country,
            listings=listings,
            categories=categories,
            category=category_record,
            next_window=self._next_window_label(),
        ))
