from odoo import http
from odoo.http import request

from odoo.addons.ocd_live.controllers.directory import OcdLiveDirectory

from . import where as where_filter


class OcdShopDirectory(OcdLiveDirectory):
    """The lives of a country with « Where? » (chantier 20, design VacancesProximite): the
    vendors of a city and a district, or from the nearest; each row says where the vendor sells,
    or that they are on holiday."""

    @http.route(
        "/lives/<string:code>", type="http", auth="public", website=True, sitemap=False, methods=["GET"],
        ocd_cache=20, ocd_cache_params=("categorie", "ville", "quartier"),
    )
    def directory_country(self, code, categorie=None, **kwargs):
        request._ocd_directory_code = (code or "").lower()
        return super().directory_country(code, categorie=categorie, **kwargs)

    def _ocd_directory_base(self):
        return f"/lives/{getattr(request, '_ocd_directory_code', '')}"

    def _ocd_directory_filter(self, country, listings):
        listings = super()._ocd_directory_filter(country, listings)
        where = where_filter.state()
        if where["vendors"] is None:
            return listings
        kept = listings.filtered(lambda listing: listing.partner_id in where["vendors"])
        if where["position"]:
            rank = {row[0].id: index for index, row in enumerate(where["ranked"])}
            kept = kept.sorted(lambda listing: rank.get(listing.partner_id.id, len(rank)))
        return kept

    def _ocd_directory_rows(self, rows):
        rows = super()._ocd_directory_rows(rows)
        env = request.env
        lines = where_filter.lines()
        partners = env["res.partner"].sudo().browse([row["listing"].partner_id.id for row in rows]).filtered("ocd_is_vendor")
        stores = env["ocd.vendor.place"]._ocd_shown_by_vendor(partners)
        for row in rows:
            partner = row["listing"].partner_id.sudo()
            if not partner.ocd_is_vendor:
                continue
            if partner._ocd_on_holiday():
                row["where"] = env._("On holiday until %s", partner._ocd_holiday_back_text())
            elif lines.get(partner.id):
                row["where"] = lines[partner.id]
            else:
                shown = stores.get(partner.id, env["ocd.vendor.place"]).filtered(lambda place: place.kind == "store")
                if shown:
                    names = ", ".join(dict.fromkeys(place.district_id.name or place.name for place in shown))
                    row["where"] = (env._("1 store · %s", names) if len(shown) == 1
                                    else env._("%(count)s stores · %(names)s", count=len(shown), names=names))
        return rows

    def _ocd_directory_values(self, country):
        values = super()._ocd_directory_values(country)
        return {**values, "where": where_filter.values(self._ocd_directory_base(), country), "search": False}

    def _ocd_directory_url(self, code, category_id):
        return where_filter.url(f"/lives/{code.lower()}", keep=(), categorie=category_id)
