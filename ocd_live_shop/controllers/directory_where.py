from odoo import http
from odoo.http import request

from odoo.addons.ocd_live.controllers import feed
from odoo.addons.ocd_live.controllers.directory import OcdLiveDirectory

from . import where as where_filter


class OcdShopDirectory(OcdLiveDirectory):
    """The lives of a country with « Where? » (chantier 20, design VacancesProximite): the
    vendors of a city and a district, or from the nearest; each card says where the vendor sells,
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

    def _ocd_directory_items(self, country, items):
        items = super()._ocd_directory_items(country, items)
        where = where_filter.state()
        if where["vendors"] is None:
            return items
        kept = [item for item in items if feed.item_vendor(item) in where["vendors"]]
        if where["position"]:
            # From the nearest, the lives now still before the next lives and the replays
            rank = {row[0].id: index for index, row in enumerate(where["ranked"])}
            kept.sort(key=lambda item: (feed.KIND_ORDER[item["kind"]], rank.get(feed.item_vendor(item).id, len(rank))))
        return kept

    def _ocd_directory_cards(self, cards):
        cards = super()._ocd_directory_cards(cards)
        env = request.env
        lines = where_filter.lines()
        partners = env["res.partner"].sudo().browse([card["vendor_id"] for card in cards if card.get("vendor_id")])
        partners = partners.filtered("ocd_is_vendor")
        by_id = {partner.id: partner for partner in partners}
        stores = env["ocd.vendor.place"]._ocd_shown_by_vendor(partners)
        for card in cards:
            partner = by_id.get(card.get("vendor_id"))
            if not partner:
                continue
            if partner._ocd_on_holiday():
                card["place"] = env._("On holiday until %s", partner._ocd_holiday_back_text())
            elif lines.get(partner.id):
                card["place"] = lines[partner.id]
            else:
                shown = stores.get(partner.id, env["ocd.vendor.place"]).filtered(lambda place: place.kind == "store")
                if shown:
                    names = ", ".join(dict.fromkeys(place.district_id.name or place.name for place in shown))
                    card["place"] = (env._("1 store · %s", names) if len(shown) == 1
                                     else env._("%(count)s stores · %(names)s", count=len(shown), names=names))
        return cards

    def _ocd_directory_values(self, country):
        values = super()._ocd_directory_values(country)
        return {**values, "where": where_filter.values(self._ocd_directory_base(), country), "search": False}

    def _ocd_directory_url(self, code, category_id):
        return where_filter.url(f"/lives/{code.lower()}", keep=(), categorie=category_id)
