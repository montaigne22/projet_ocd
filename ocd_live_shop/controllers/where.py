"""« Where? » of the shop and of the directory of the lives (chantier 20, A.3 of the plan of « My
products », design VacancesProximite): a city and a district (?ville=, ?quartier=), or the
position of the phone (?pres=1&lat=&lon=: only in the address of the page, never kept, and such
a page is never kept in memory either: see ocd_live/page_cache.py)."""
from urllib.parse import urlencode

from odoo.http import request

from odoo.addons.ocd_live.controllers import common

from ..models.vendor_nearby import read_position

PARAMS = ("ville", "quartier", "pres", "lat", "lon")


def state():
    """The filter of the address, read once per request: {city, district, position, vendors
    (the vendors kept, None without a filter), ranked (from the nearest), approved}."""
    cached = getattr(request, "_ocd_where_cache", None)
    if cached is not None:
        return cached
    env = request.env
    params = request.params
    City, District = env["res.city"].sudo(), env["res.city.district"].sudo()
    city = City.browse(int(params["ville"])).exists() if str(params.get("ville") or "").isdigit() else City
    district = District.browse(int(params["quartier"])).exists() if str(params.get("quartier") or "").isdigit() else District
    if district and city and district.city_id != city:
        district = District  # another city was chosen: its districts
    city = city or district.city_id
    position = read_position(params.get("lat"), params.get("lon")) if params.get("pres") else None
    approved = env["res.partner"].sudo().search([("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "approved")])
    vendors, ranked = None, []
    if position:
        ranked = approved._ocd_by_distance(*position)
        vendors = env["res.partner"].sudo().browse([row[0].id for row in ranked])
    elif city:
        vendors = approved._ocd_in_area(city, district)
    result = {
        "city": city, "district": district, "position": position, "vendors": vendors, "ranked": ranked,
        "approved": approved,
    }
    request._ocd_where_cache = result
    return result


def url(base, keep=("categorie", "search"), **changes):
    """The address `base` with the filters of today, and `changes` (None removes one)."""
    query = {key: request.params[key] for key in (*keep, *PARAMS) if request.params.get(key)}
    for key, value in changes.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    return base + (f"?{urlencode(query)}" if query else "")


def lines():
    """{vendor id: « Akwa · 400 m »}: where each vendor kept sells, while a filter is on."""
    env = request.env
    where = state()
    result = {}
    if where["position"]:
        for vendor, km, place in where["ranked"]:
            area = (place.district_id.name or place.city_id.name) if place else (
                vendor.district_id.name or vendor.city_id.name)
            parts = [area, env["res.partner"]._ocd_distance_text(km) if km is not None else ""]
            result[vendor.id] = " · ".join(part for part in parts if part)
    elif where["vendors"] is not None:
        areas = where["vendors"]._ocd_areas()
        for vendor in where["vendors"]:
            names = [district.name or city.name for city, district, _place in areas[vendor.id]
                     if city == where["city"] and (not where["district"] or district == where["district"])]
            result[vendor.id] = ", ".join(dict.fromkeys(name for name in names if name))
    return result


def values(base, country=None):
    """The filter « Where? » of a page: the cities where vendors sell (in `country`, else in
    the country of the visitor), the districts of the city chosen."""
    env = request.env
    where = state()
    Partner = env["res.partner"]
    cities = Partner._ocd_area_cities(where["approved"], country or common.default_country())
    if not cities and not country:
        cities = Partner._ocd_area_cities(where["approved"])
    districts = cities.get(where["city"], env["res.city.district"]) if where["city"] else env["res.city.district"]
    plain = url(base, ville=None, quartier=None, pres=None, lat=None, lon=None, page=None)
    return {
        "cities": [{"id": city.id, "name": city.name, "on": city == where["city"]} for city in cities],
        "districts": [{"id": district.id, "name": district.name, "on": district == where["district"]}
                      for district in districts.sorted("name")],
        "near": bool(where["position"]),
        "near_url": plain,
        "clear_url": plain,
        "active": bool(where["city"] or where["position"]),
    }
