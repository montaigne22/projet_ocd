import re

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.ocd_live.controllers import common



def delays():
    """The delays a vendor can choose for a price, in the language of the page."""
    env = request.env
    return [
        env._("Delivered the same day"),
        env._("Delivered within 24 hours"),
        env._("Delivered within 24 to 48 hours"),
        env._("Delivered within 2 to 4 days"),
    ]


class OcdVendorRates(http.Controller):
    """My delivery prices: a vendor who delivers sets a price per zone (a city, or districts of
    a city), within the limits set by the team. Elsewhere in their zones, they deliver at the
    price of the OCD courier of their city."""

    def _vendor(self):
        return common.current_vendor()

    def _delivers(self, vendor, company):
        return vendor.ocd_sale_mode == "ocd" and (vendor.ocd_delivery_mode or company.ocd_default_delivery_mode) == "vendor"

    def _render(self, vendor, values=None, error=None, saved=False):
        env = request.env
        company = common.company()
        Rate = env["ocd.delivery.rate"].sudo()
        country, origin_city = Rate._ocd_origin(vendor, company)
        cities = env["res.city"].sudo().search([("country_id", "=", country.id)], order="name") if country else env["res.city"]
        values = values or {}
        city_id = int(values["city_id"]) if str(values.get("city_id") or "").isdigit() else origin_city.id
        city = cities.filtered(lambda c: c.id == city_id)[:1] or origin_city or cities[:1]
        districts = env["res.city.district"].sudo().search([("city_id", "=", city.id)], order="name") if city else []
        chosen = {int(d) for d in values.get("district_ids", []) if str(d).isdigit()}
        currency = company.currency_id
        own = Rate.search([("vendor_id", "=", vendor.id)])
        ocd_rates = Rate._ocd_rates(company).filtered(
            lambda r: not r.vendor_id and r._ocd_origin_level(country, origin_city) >= 0
        )
        low, high = company._ocd_vendor_rate_bounds()
        if low and high:
            bounds = env._("Between %(low)s and %(high)s.", low=common.money(low, currency), high=common.money(high, currency))
        elif low:
            bounds = env._("At least %s.", common.money(low, currency))
        elif high:
            bounds = env._("At most %s.", common.money(high, currency))
        else:
            bounds = ""
        return request.render("ocd_live_shop.vendor_rates", common.page_values(
            "mes_livraisons",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("My delivery prices"),
            vendor=vendor,
            delivers=self._delivers(vendor, company),
            origin_line=env._("Your parcels leave from %s.", origin_city.name) if origin_city else env._(
                "Add your city to your space to set your prices: write to OCD Live."
            ),
            rows=[{
                "rate": rate,
                "zone": rate._ocd_zone_label(),
                "price": common.money(rate.price, rate.currency_id) if rate.price else env._("Free"),
                "description": rate.description or "",
            } for rate in own],
            ocd_rows=[{
                "zone": rate._ocd_zone_label(),
                "price": common.money(rate.price, rate.currency_id) if rate.price else env._("Free"),
                "who": dict(rate._fields["operator"]._description_selection(env)).get(rate.operator),
            } for rate in ocd_rates.sorted(lambda r: (r.operator == "agency", r.sequence, r.price))[:6]],
            cities=cities,
            city=city,
            districts=districts,
            chosen=chosen,
            delays=delays(),
            values=values,
            bounds=bounds,
            currency_symbol=currency.symbol,
            error=error,
            saved=saved,
        ))

    @http.route("/ocd/espace/moi/livraison", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def rates(self, enregistre=None, **kwargs):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        return self._render(vendor, values=kwargs, saved=bool(enregistre))

    @http.route("/ocd/espace/moi/livraison", type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def rate_add(self, city_id=None, price=None, description=None, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        company = common.company()
        values = {"city_id": city_id, "price": price, "description": description,
                  "district_ids": request.httprequest.form.getlist("district_ids")}
        if not self._delivers(vendor, company):
            return self._render(vendor, values, error=env._("OCD Live delivers your parcels: its prices are used."))
        city = env["res.city"].sudo().browse(int(city_id or 0)).exists()
        if not city:
            return self._render(vendor, values, error=env._("Choose a city."))
        districts = env["res.city.district"].sudo().browse(
            [int(d) for d in values["district_ids"] if str(d).isdigit()]
        ).exists().filtered(lambda d: d.city_id == city)
        digits = re.sub(r"[^\d]", "", price or "")
        if not digits:
            return self._render(vendor, values, error=env._("Write a price in francs, for example 1000."))
        try:
            # sudo: the vendor has no account; the price is checked against the limits of the
            # team. A refused price leaves nothing behind (savepoint).
            with env.cr.savepoint():
                rate = env["ocd.delivery.rate"].sudo().create({
                    "company_id": company.id,
                    "currency_id": company.currency_id.id,
                    "vendor_id": vendor.id,
                    "operator": "vendor",
                    "country_id": city.country_id.id,
                    "city_ids": [(6, 0, city.ids)],
                    "district_ids": [(6, 0, districts.ids)],
                    "price": int(digits),
                    "description": common.clean_text(description, 80) or False,
                })
        except (UserError, ValidationError) as exc:
            return self._render(vendor, values, error=exc.args[0])
        vendor.sudo().message_post(body=env._(
            "Delivery price added by the vendor: %(zone)s · %(price)s",
            zone=rate._ocd_zone_label(), price=common.money(rate.price, rate.currency_id),
        ))
        return request.redirect("/ocd/espace/moi/livraison?enregistre=1")

    @http.route("/ocd/espace/moi/livraison/<int:rate_id>/supprimer", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def rate_remove(self, rate_id, **post):
        vendor = self._vendor()
        if not vendor:
            return request.redirect("/ocd/connexion")
        rate = request.env["ocd.delivery.rate"].sudo().browse(rate_id).exists()
        if not rate or rate.vendor_id != vendor:
            raise request.not_found()
        # Archived, not deleted: the orders already paid keep their rate
        rate.active = False
        vendor.sudo().message_post(body=request.env._(
            "Delivery price removed by the vendor: %(zone)s · %(price)s",
            zone=rate._ocd_zone_label(), price=common.money(rate.price, rate.currency_id),
        ))
        return request.redirect("/ocd/espace/moi/livraison")
