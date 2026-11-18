"""« Put in promo » of « My products » (plan, 3.1; chantier 7, design ProgrammeSoirees): a discount
or a new price, until a date; the vendor sees what the customers will see. The rules (lowest price
of the last days, discount and duration at most) are the ones of the model (ocd.product.promo)."""
import json
import math
from datetime import datetime, time, timedelta

import pytz

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

# The discounts offered in one tap; « Another price » for the rest
PERCENTS = (10, 20, 25, 30)
# The durations offered in one tap, in days (cut at the duration allowed)
DURATIONS = (7, 14, 30)


def promo_amount(reference, percent, currency):
    """The price of a discount of `percent` % on `reference`; a round price in francs (8,975 F
    becomes 9,000 F), never more than the discount chosen."""
    amount = currency.round(reference * (100 - percent) / 100)
    if currency.decimal_places == 0 and amount >= 1000:
        rounded = math.ceil(amount / 50) * 50
        amount = rounded if rounded < reference else amount
    return amount


def until_end_of_day(vendor, days):
    """The end of the `days`-th day, today included, at the hour of the vendor (UTC, naive)."""
    tz_name = vendor._ocd_tz_name() or "Africa/Lome"
    zone = pytz.timezone(tz_name)
    today = tools.to_tz(common.now(), tz_name).date()
    last = today + timedelta(days=max(days, 1) - 1)
    local_end = zone.localize(datetime.combine(last + timedelta(days=1), time.min))
    return local_end.astimezone(pytz.utc).replace(tzinfo=None)


class OcdVendorPromo(http.Controller):

    def _product(self, product_id):
        vendor = common.current_vendor()
        if not vendor:
            return None, None
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or product.ocd_vendor_id != vendor:
            raise request.not_found()
        return vendor, product

    def _render(self, vendor, product, error=None, values=None, done=None):
        env = request.env
        Promo = env["ocd.product.promo"].sudo()
        limits = Promo._ocd_limits(vendor.company_id or common.company())
        currency = product.currency_id
        reference = product._ocd_reference_price()
        running = Promo._ocd_running(product).get(product.id)
        values = values or {}
        percent = values.get("percent") or ("autre" if values.get("price") else "20")
        durations = [days for days in DURATIONS if days <= limits["days"]] or [limits["days"]]
        days = int(values["days"]) if str(values.get("days") or "").isdigit() else durations[min(1, len(durations) - 1)]
        return request.render("ocd_live_shop.vendor_product_promo", common.page_values(
            "mes_produits",
            space_page="products",
            back="/ocd/espace/moi/produits",
            back_label=env._("Back to my products"),
            header_title=env._("My products"),
            vendor=vendor,
            product=product,
            image=f"/ocd/espace/moi/produits/{product.id}/photo/image_128",
            price_text=common.money(product.list_price, currency),
            reference=reference,
            reference_text=common.money(reference, currency),
            reference_line=env._(
                "The price struck through is %(price)s, the lowest price of this product in the last %(days)s days.",
                price=common.money(reference, currency), days=limits["reference_days"],
            ) if currency.compare_amounts(reference, product.list_price) else False,
            running=running,
            running_line=env._("In promo now: %(price)s instead of %(was)s, %(until)s.",
                               price=common.money(running.price, currency), was=common.money(running.reference_price, currency),
                               until=running._ocd_until_text()) if running else False,
            percents=[p for p in PERCENTS if p <= limits["discount"]],
            percent=str(percent),
            price_value=values.get("price") or "",
            durations=durations,
            days=days,
            rules_line=env._(
                "%(discount)s %% of discount at most, %(days)s days at most. The price struck through is your lowest "
                "price of the last %(reference)s days: a price raised just before does not make a promo. The commission "
                "of OCD is counted on the price reduced.",
                discount=limits["discount"], days=limits["days"], reference=limits["reference_days"],
            ),
            preview_title=env._("The customers see: %(price)s instead of %(was)s"),
            preview_line=env._("%(off)s %(until)s, in your boutique, the shop, your lives and the cart."),
            symbol=currency.symbol,
            position=currency.position,
            until_json=json.dumps({str(d): env["ocd.product.promo"].new({
                "date_end": until_end_of_day(vendor, d), "product_tmpl_id": product.id,
            })._ocd_until_text(vendor._ocd_tz_name()) for d in durations}),
            error=error,
            message=done,
        ))

    @http.route("/ocd/espace/moi/produits/<int:product_id>/promo", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def promo_page(self, product_id, fait=None, **kwargs):
        vendor, product = self._product(product_id)
        if not vendor:
            return request.redirect("/ocd/connexion")
        done = {
            "1": request.env._("Done: your promo is shown at once."),
            "0": request.env._("Done: the promo is stopped, the usual price is back."),
        }.get(fait)
        return self._render(vendor, product, done=done)

    @http.route("/ocd/espace/moi/produits/<int:product_id>/promo", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def promo_put(self, product_id, percent=None, price=None, days=None, **post):
        vendor, product = self._product(product_id)
        if not vendor:
            return request.redirect("/ocd/connexion")
        env = request.env
        values = {"percent": percent, "price": price, "days": days}
        Promo = env["ocd.product.promo"].sudo()
        limits = Promo._ocd_limits(vendor.company_id or common.company())
        reference = product._ocd_reference_price()
        currency = product.currency_id
        try:
            if percent and percent != "autre":
                if not str(percent).isdigit():
                    raise UserError(env._("Choose the discount."))
                amount = promo_amount(reference, int(percent), currency)
            else:
                amount = tools.parse_amount(price or "", currency.decimal_places, currency.symbol)
                if amount is None:
                    raise UserError(env._("Write the promo price, in numbers."))
            count = int(days) if str(days or "").isdigit() else 0
            if not 1 <= count <= limits["days"]:
                raise UserError(env._("%s days at most.", limits["days"]))
            Promo._ocd_put(product, amount, until_end_of_day(vendor, count), source="vendor", limits=limits)
        except (UserError, ValidationError) as exc:
            return self._render(vendor, product, error=exc.args[0], values=values)
        return request.redirect(f"/ocd/espace/moi/produits/{product.id}/promo?fait=1")

    @http.route("/ocd/espace/moi/produits/<int:product_id>/promo/arreter", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def promo_stop(self, product_id, **post):
        vendor, product = self._product(product_id)
        if not vendor:
            return request.redirect("/ocd/connexion")
        promos = request.env["ocd.product.promo"].sudo().search([
            ("product_tmpl_id", "=", product.id), ("source", "=", "vendor"), ("date_end", ">", common.now()),
        ])
        promos._ocd_stop(request.env._("Stopped by the vendor."))
        return request.redirect(f"/ocd/espace/moi/produits/{product.id}/promo?fait=0")
