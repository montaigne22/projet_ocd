"""The vendors near me (chantier 20, A.3 of the plan of « My products », design
VacancesProximite): where each vendor sells (their places the customers see, else their own city
and district), filtered by city and district, and ranked from the nearest when the customer gives
the position of their phone (never kept: it is only in the address of the page).

The distance is counted to the stores whose position was taken on the spot: a district has no
position, and a vendor who sells from home never shows theirs. The vendors without a position come
after, those of the city of the nearest store first."""
import math
from collections import defaultdict

from odoo import api, models
from odoo.tools.misc import formatLang

EARTH_KM = 6371.0
# A store farther than this is not in the city of the customer
SAME_CITY_KM = 30.0


def distance_km(lat1, lon1, lat2, lon2):
    """The distance between two positions on the earth, in km (haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_KM * math.asin(math.sqrt(min(1.0, a)))


def read_position(lat, lon):
    """(latitude, longitude) of the address of a page, or None when it is not a position."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    return lat, lon


class OcdVendorPlace(models.Model):
    _inherit = "ocd.vendor.place"

    @api.model
    def _ocd_shown_by_vendor(self, vendors):
        """{vendor id: the places the customers see}, for many vendors in one query (see
        `_ocd_shown_places`)."""
        places = self.sudo().search(
            [("vendor_id", "in", vendors.ids), ("state", "=", "approved")], order="sequence, id"
        )
        allowed = {vendor.id: vendor._ocd_places_allowed() for vendor in vendors}
        shown = defaultdict(lambda: self.browse())
        for place in places:
            if len(shown[place.vendor_id.id]) < allowed.get(place.vendor_id.id, 1):
                shown[place.vendor_id.id] |= place
        return shown


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_areas(self):
        """{vendor id: [(city, district, place)]}: where each vendor sells, their places the
        customers see, else their own city and district (`place` False)."""
        shown = self.env["ocd.vendor.place"]._ocd_shown_by_vendor(self)
        areas = {}
        for vendor in self.sudo():
            places = shown.get(vendor.id)
            if places:
                areas[vendor.id] = [
                    (place.city_id or place.district_id.city_id, place.district_id, place) for place in places
                ]
            elif vendor.city_id or vendor.district_id:
                areas[vendor.id] = [(vendor.city_id or vendor.district_id.city_id, vendor.district_id, False)]
            else:
                areas[vendor.id] = []
        return areas

    def _ocd_in_area(self, city=None, district=None):
        """The vendors who sell in `city` (and `district`, when given)."""
        areas = self._ocd_areas()
        return self.filtered(lambda vendor: any(
            (not city or area_city == city) and (not district or area_district == district)
            for area_city, area_district, _place in areas[vendor.id]
        ))

    def _ocd_by_distance(self, lat, lon):
        """The vendors from the nearest: [(vendor, km or None, place or False)]. The distance
        goes to their nearest store with a position: the stores of the city of the customer
        first (within SAME_CITY_KM), then the vendors of that city without a position (a home,
        a store without one), then the farther stores, then the others."""
        areas = self._ocd_areas()
        measured, others = [], []
        for vendor in self:
            best = None
            for _city, _district, place in areas[vendor.id]:
                if place and place.kind == "store" and place._ocd_has_position():
                    km = distance_km(lat, lon, place.latitude, place.longitude)
                    if best is None or km < best[0]:
                        best = (km, place)
            if best:
                measured.append((vendor, best[0], best[1]))
            elif areas[vendor.id]:
                others.append((vendor, None, areas[vendor.id][0][2]))
        measured.sort(key=lambda row: (row[1], row[0].id))
        near = measured[0] if measured and measured[0][1] <= SAME_CITY_KM else None
        city = (near[2].city_id or near[2].district_id.city_id) if near else None
        same_city = [row for row in others if city and any(area_city == city for area_city, _d, _p in areas[row[0].id])]
        elsewhere = [row for row in others if row not in same_city]
        # The stores of the city first, then the vendors of the city without a position, then
        # the farther stores, then the rest
        close = [row for row in measured if row[1] <= SAME_CITY_KM]
        far = [row for row in measured if row[1] > SAME_CITY_KM]
        return close + sorted(same_city, key=lambda row: row[0].id) + far + sorted(elsewhere, key=lambda row: row[0].id)

    @api.model
    def _ocd_distance_text(self, km):
        """« 400 m », « 2.1 km » (in the language of the page)."""
        if km < 1:
            return self.env._("%s m", max(100, int(round(km * 10)) * 100))
        return self.env._("%s km", formatLang(self.env, km, digits=1))

    @api.model
    def _ocd_area_cities(self, vendors, country=None):
        """The cities where `vendors` sell (in `country`), for the filter « Where? »:
        {city: districts}."""
        cities = defaultdict(lambda: self.env["res.city.district"])
        for rows in vendors._ocd_areas().values():
            for city, district, _place in rows:
                if city and (not country or city.country_id == country):
                    cities[city] |= district
        return dict(sorted(cities.items(), key=lambda item: item[0].name or ""))
