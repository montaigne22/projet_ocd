"""Delivery rates of OCD Live: the price of the delivery of each parcel (one per vendor).

A rate goes from an origin (the city of the vendor, or of the OCD stock) to a zone of the
customer (districts, cities or a whole country). The vendors who deliver themselves have their
own rates, within the limits set by the team; OCD Live has its rates for its couriers (in a
city) and for the travel agencies (to the other cities, or to another country).

The engine (`_ocd_quote`) finds the rate of a parcel; the checkout adds the parcels of the cart
(see `delivery.carrier`, type "ocd") and refuses an address that a parcel cannot reach. Every
step is a method, so that a module can change one rule without copying the others."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

OPERATORS = [
    ("vendor", "The vendor delivers"),
    ("courier", "An OCD courier delivers"),
    ("agency", "Sent through a travel agency"),
]


class OcdDeliveryRate(models.Model):
    _name = "ocd.delivery.rate"
    _description = "Delivery Rate"
    _order = "vendor_id, sequence, id"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", string="Zone")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10, help="Between two rates as precise as each other, the first one is used.")
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        index="btree_not_null",
        ondelete="cascade",
        domain=[("ocd_is_vendor", "=", True)],
        help="Empty: a rate of OCD Live, for its couriers or for a travel agency.",
    )
    operator = fields.Selection(selection=OPERATORS, string="Who Delivers", required=True, default="courier")
    origin_country_id = fields.Many2one(
        comodel_name="res.country",
        string="From Country",
        help="Rates of OCD Live: the parcel leaves from this country (any city when no city is set).",
    )
    origin_city_id = fields.Many2one(
        comodel_name="res.city",
        string="From City",
        help="Rates of OCD Live: the parcel leaves from this city (the city of the vendor, or of the "
        "OCD stock). The rates of a vendor leave from the city of the vendor.",
    )
    country_id = fields.Many2one(comodel_name="res.country", string="To Country", required=True)
    city_ids = fields.Many2many(
        comodel_name="res.city",
        relation="ocd_delivery_rate_city_rel",
        column1="rate_id",
        column2="city_id",
        string="To Cities",
        help="Empty: the whole country.",
    )
    district_ids = fields.Many2many(
        comodel_name="res.city.district",
        relation="ocd_delivery_rate_district_rel",
        column1="rate_id",
        column2="district_id",
        string="To Districts",
        help="Empty: the whole cities.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", required=True, default=lambda self: self.env.company.currency_id
    )
    price = fields.Monetary(string="Price", required=True, default=0.0)
    free_above = fields.Monetary(
        string="Free Above",
        help="The delivery is free when the products of the parcel cost at least this amount. 0: never free.",
    )
    description = fields.Char(
        string="For The Customer",
        translate=True,
        help="Shown to the customer, e.g. \"Delivered within 24 to 48 hours\".",
    )
    allow_cod = fields.Boolean(
        string="Payment At The Door",
        default=True,
        help="The customer may pay at the delivery. Never for a travel agency, nor towards another country.",
    )
    source_carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Created From",
        readonly=True,
        ondelete="set null",
        help="Delivery method this rate was created from.",
    )

    # === DISPLAY === #

    @api.depends("country_id", "city_ids", "district_ids")
    def _compute_name(self):
        for rate in self:
            rate.name = rate._ocd_zone_label()

    def _ocd_zone_label(self, limit=4):
        """Zone of the rate for the customer: "Akwa, Bonapriso", "Douala", "Cameroon"."""
        self.ensure_one()
        if self.district_ids:
            names = self.district_ids.mapped("name")
        elif self.city_ids:
            names = self.city_ids.mapped("name")
        else:
            names = [self.country_id.name or ""]
        label = ", ".join(names[:limit])
        if len(names) > limit:
            label = self.env._("%(names)s and %(count)s more", names=label, count=len(names) - limit)
        return label

    # === CHECKS === #

    @api.constrains("vendor_id", "operator")
    def _check_operator(self):
        for rate in self:
            if rate.vendor_id and rate.operator != "vendor":
                raise ValidationError(self.env._("The rates of a vendor are the deliveries made by the vendor."))
            if not rate.vendor_id and rate.operator == "vendor":
                raise ValidationError(self.env._("Choose the vendor of this rate."))

    @api.constrains("country_id", "city_ids", "district_ids", "origin_country_id", "origin_city_id")
    def _check_zone(self):
        for rate in self:
            if rate.city_ids.filtered(lambda c: c.country_id != rate.country_id):
                raise ValidationError(self.env._("The cities of the rate must be in %s.", rate.country_id.name))
            districts = rate.district_ids
            if districts.filtered(lambda d: d.city_id.country_id != rate.country_id):
                raise ValidationError(self.env._("The districts of the rate must be in %s.", rate.country_id.name))
            if rate.city_ids and districts.filtered(lambda d: d.city_id not in rate.city_ids):
                raise ValidationError(self.env._("The districts of the rate must be in its cities."))
            if rate.origin_city_id and rate.origin_country_id and rate.origin_city_id.country_id != rate.origin_country_id:
                raise ValidationError(self.env._("The city of departure must be in the country of departure."))

    @api.constrains("price", "free_above", "vendor_id", "company_id")
    def _check_price(self):
        for rate in self:
            if rate.price < 0 or rate.free_above < 0:
                raise ValidationError(self.env._("A price cannot be negative."))
            if rate.vendor_id:
                low, high = rate.company_id._ocd_vendor_rate_bounds()
                if (low and rate.price < low) or (high and rate.price > high):
                    raise ValidationError(rate._ocd_bounds_message())

    def _ocd_bounds_message(self):
        company = self.company_id or self.env.company
        low, high = company._ocd_vendor_rate_bounds()
        money = company.currency_id
        if low and high:
            return self.env._(
                "The price of a delivery is between %(low)s and %(high)s.",
                low=money.format(low), high=money.format(high),
            )
        if low:
            return self.env._("The price of a delivery is at least %s.", money.format(low))
        return self.env._("The price of a delivery is at most %s.", money.format(high))

    # === ENGINE === #

    @api.model
    def _ocd_origin(self, vendor, company):
        """Where a parcel leaves from: (country, city) of the vendor, or of the OCD stock for the
        products of OCD Live and the vendors whose products are in the OCD stock."""
        City = self.env["res.city"].sudo()
        if vendor and (vendor.ocd_delivery_mode or company.ocd_default_delivery_mode) != "stock":
            city = vendor.city_id
            if not city and vendor.city:
                city = City.search([
                    ("name", "=ilike", vendor.city.strip()),
                    *([("country_id", "=", vendor.country_id.id)] if vendor.country_id else []),
                ], limit=1)
            return (vendor.country_id or city.country_id), city
        city = company.ocd_stock_city_id
        if not city and company.city:
            city = City.search([
                ("name", "=ilike", company.city.strip()),
                *([("country_id", "=", company.country_id.id)] if company.country_id else []),
            ], limit=1)
        return (city.country_id or company.country_id), city

    def _ocd_destination_level(self, country, city, district):
        """How precisely the rate matches the address: 3 district, 2 city, 1 country, 0 no match."""
        self.ensure_one()
        if not country or self.country_id != country:
            return 0
        if self.city_ids and city not in self.city_ids:
            return 0
        if self.district_ids:
            return 3 if district and district in self.district_ids else 0
        return 2 if self.city_ids else 1

    def _ocd_origin_level(self, country, city):
        """How precisely a rate of OCD Live matches the departure: 2 city, 1 country, 0 any, -1 no match."""
        self.ensure_one()
        if self.origin_city_id:
            return 2 if city and self.origin_city_id == city else -1
        if self.origin_country_id:
            return 1 if country and self.origin_country_id == country else -1
        return 0

    def _ocd_best(self, partner, origin=None):
        """The most precise rate of `self` for the address of `partner` (and the departure
        `origin` for the rates of OCD Live). Between two rates as precise, the first by sequence,
        then the cheapest."""
        country, city, district = partner.country_id, partner.city_id, partner.district_id
        if district and not city:
            city = district.city_id
        local = bool(origin and origin[1] and city and origin[1] == city)
        candidates = []
        for rate in self:
            destination = rate._ocd_destination_level(country, city, district)
            if not destination:
                continue
            if local and rate.operator == "agency":
                # A travel agency never carries a parcel inside its own city
                continue
            departure = rate._ocd_origin_level(*origin) if origin and not rate.vendor_id else 0
            if departure < 0:
                continue
            candidates.append(((-destination, -departure, rate.sequence, rate.price, rate.id), rate))
        return min(candidates, key=lambda item: item[0])[1] if candidates else self.browse()

    @api.model
    def _ocd_rates(self, company):
        """The active rates of the company, read once for a whole cart."""
        return self.sudo().with_context(active_test=True).search([("company_id", "=", company.id)])

    @api.model
    def _ocd_quote(self, vendor, partner, goods_amount, currency, company, date=None, rates=None):
        """Return the delivery of the parcel of `vendor` (empty: the products of OCD Live) to the
        address of `partner`, as a dict:

        - ``rate``: the rate used (empty when the parcel cannot be delivered);
        - ``operator``: who delivers (vendor, courier, agency);
        - ``price``: the price, in `currency`, after the free delivery above an amount;
        - ``allow_cod``: whether the customer may pay at the door;
        - ``origin``: the city the parcel leaves from;
        - ``error``: why the parcel cannot be delivered, for the customer (or False).
        """
        rates = rates if rates is not None else self._ocd_rates(company)
        origin = self._ocd_origin(vendor, company)
        rate, operator = self._ocd_find_rate(vendor, partner, origin, rates, company)
        quote = {
            "vendor": vendor,
            "rate": rate,
            "operator": operator,
            "origin": origin[1],
            "price": 0.0,
            "allow_cod": False,
            "description": (rate.description or "") if rate else "",
            "error": False,
        }
        if not rate:
            quote["error"] = self._ocd_no_delivery_message(vendor, partner, origin)
            return quote
        quote["price"] = rate._ocd_price(goods_amount, currency, company, date)
        quote["allow_cod"] = rate._ocd_allows_cod(origin, partner, operator)
        return quote

    @api.model
    def _ocd_find_rate(self, vendor, partner, origin, rates, company):
        """Return (rate, who delivers) for the parcel of `vendor`:

        1. a vendor who delivers uses their own rate for the address;
        2. else, in their area (their delivery zones, or their own city when they have none), the
           vendor delivers at the price of the OCD courier of the city;
        3. else, when the team allows it, an OCD courier or a travel agency takes the parcel from
           the city of the vendor;
        4. the products of OCD Live, and the vendors whose products an OCD courier picks up or
           which are in the OCD stock, use the rates of OCD Live from their city.
        """
        own_rates = rates.filtered(lambda r: r.vendor_id and r.vendor_id == vendor)
        ocd_rates = rates.filtered(lambda r: not r.vendor_id)
        mode = (vendor.ocd_delivery_mode or company.ocd_default_delivery_mode) if vendor else "stock"
        if vendor and mode == "vendor":
            rate = own_rates._ocd_best(partner)
            if rate:
                return rate, "vendor"
            if self._ocd_in_vendor_area(vendor, partner, origin):
                courier_rate = ocd_rates.filtered(lambda r: r.operator == "courier")._ocd_best(partner, origin)
                if courier_rate:
                    return courier_rate, "vendor"
            if not vendor.ocd_zone_fallback:
                return self.browse(), False
        rate = ocd_rates._ocd_best(partner, origin)
        return (rate, rate.operator) if rate else (self.browse(), False)

    @api.model
    def _ocd_in_vendor_area(self, vendor, partner, origin):
        """Where a vendor without a rate for the address delivers: their delivery zones, or
        their own city when they have no zone."""
        district = partner.district_id
        if vendor.ocd_zone_ids:
            return bool(district) and district in vendor.ocd_zone_ids
        city = partner.city_id or district.city_id
        return bool(origin[1]) and city == origin[1]

    def _ocd_price(self, goods_amount, currency, company, date=None):
        """The price of the rate in `currency`; free above the amount of the rate."""
        self.ensure_one()
        date = date or fields.Date.context_today(self)
        price = self._ocd_converted_price(currency, company, date)
        if self.free_above:
            threshold = self.currency_id._convert(self.free_above, currency, company, date)
            if currency.compare_amounts(goods_amount, threshold) >= 0:
                price = 0.0
        return currency.round(price)

    def _ocd_converted_price(self, currency, company, date):
        """The price of the rate in `currency`: converted, then rounded to the unit as the prices
        of the products (1 500 F CFA: 2 € and 3 $, not 2.29 € and 2.53 $)."""
        self.ensure_one()
        price = self.currency_id._convert(self.price, currency, company, date)
        if currency != self.currency_id:
            price = float_round(price, precision_rounding=1.0)
        return price

    def _ocd_allows_cod(self, origin, partner, operator):
        """Payment at the door: never through a travel agency, nor towards another country."""
        self.ensure_one()
        if not self.allow_cod or operator == "agency":
            return False
        return not (origin[0] and partner.country_id and origin[0] != partner.country_id)

    @api.model
    def _ocd_no_delivery_message(self, vendor, partner, origin):
        place = partner.district_id.name or partner.city_id.name or partner.city or partner.country_id.name or ""
        if vendor:
            if origin[1]:
                return self.env._(
                    "%(vendor)s (%(city)s) does not deliver to %(place)s yet.",
                    vendor=vendor.name, city=origin[1].name, place=place,
                )
            return self.env._("%(vendor)s does not deliver to %(place)s yet.", vendor=vendor.name, place=place)
        return self.env._("OCD Live does not deliver to %s yet.", place)

    # === SUMMARY FOR THE PRODUCT PAGE === #

    @api.model
    def _ocd_summary(self, vendor, company, currency, limit=3):
        """Lines of the product page: where the parcel leaves from, and the main prices."""
        rates = self._ocd_rates(company)
        origin = self._ocd_origin(vendor, company)
        mode = (vendor.ocd_delivery_mode or company.ocd_default_delivery_mode) if vendor else "stock"
        shown = self.browse()
        if vendor and mode == "vendor":
            shown |= rates.filtered(lambda r: r.vendor_id == vendor)
        if not (vendor and mode == "vendor" and not vendor.ocd_zone_fallback):
            shown |= rates.filtered(
                lambda r: not r.vendor_id and r._ocd_origin_level(*origin) >= 0
            )
        lines = []
        for rate in shown.sorted(lambda r: (r.vendor_id.id or 0, r.operator == "agency", r.sequence, r.price))[:limit]:
            price = rate._ocd_converted_price(currency, company, fields.Date.context_today(self))
            lines.append(self.env._(
                "%(zone)s: %(price)s", zone=rate._ocd_zone_label(limit=2),
                price=currency.format(price) if price else self.env._("free"),
            ))
        return {"origin": origin[1].name or origin[0].name or "", "lines": lines}

    # === RATES CREATED FROM THE DELIVERY METHODS OF ODOO === #

    @api.model
    def _ocd_rates_from_carriers(self, company):
        """Turn the delivery methods by city (Douala, Lomé, other cities...) into rates of OCD
        Live, once each: a method for some cities gives one rate of OCD couriers per city; a
        method for a whole country gives a rate of travel agency inside that country. A rate is
        active only when its method was published with a price; the method is then unpublished,
        the rates of OCD Live replace it. The others are created archived, for the team to set
        their price."""
        carrier_ocd = self.env.ref("ocd_live_shop.carrier_ocd", raise_if_not_found=False)
        carriers = self.env["delivery.carrier"].sudo().with_context(active_test=False).search([
            ("delivery_type", "=", "fixed"),
            ("country_ids", "!=", False),
            ("company_id", "in", (company.id, False)),
        ])
        done = self.sudo().with_context(active_test=False).search(
            [("source_carrier_id", "in", carriers.ids)]
        ).source_carrier_id
        created = self.browse()
        for carrier in carriers - done - (carrier_ocd or self.env["delivery.carrier"]):
            price = carrier.fixed_price or carrier.product_id.list_price
            active = bool(carrier.is_published and carrier.active and price > 0)
            common = {
                "company_id": company.id,
                "currency_id": company.currency_id.id,
                "price": price,
                "description": carrier.carrier_description or False,
                "allow_cod": carrier.allow_cash_on_delivery,
                "active": active,
                "source_carrier_id": carrier.id,
            }
            values = []
            if carrier.city_ids:
                for city in carrier.city_ids:
                    values.append({
                        **common,
                        "operator": "courier",
                        "origin_country_id": city.country_id.id,
                        "origin_city_id": city.id,
                        "country_id": city.country_id.id,
                        "city_ids": [(6, 0, city.ids)],
                        "district_ids": [(6, 0, carrier.district_ids.filtered(lambda d, c=city: d.city_id == c).ids)],
                    })
            else:
                for country in carrier.country_ids:
                    values.append({
                        **common,
                        "operator": "agency",
                        "allow_cod": False,
                        "origin_country_id": country.id,
                        "country_id": country.id,
                        "sequence": 20,
                    })
            created |= self.sudo().create(values)
            if active:
                carrier.is_published = False
        return created

    @api.model
    def _ocd_init_default_rates(self):
        """At the installation (and the updates) of the module: the companies without any rate
        of OCD Live get the rates of their delivery methods by city."""
        for company in self.env["res.company"].sudo().search([]):
            if not self.sudo().with_context(active_test=False).search_count(
                [("company_id", "=", company.id), ("vendor_id", "=", False)], limit=1
            ):
                self._ocd_rates_from_carriers(company)
        return True
