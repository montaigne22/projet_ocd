from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models

from .res_partner import same_number

# The products read for a list of « Products to share » before the stock is checked
CANDIDATES = 400


class ProductTemplate(models.Model):
    """The products an ambassador shares (design Ambassadeurs, « Produits à partager »): on sale
    on OCD Live (not the vendors in direct contact on WhatsApp), checked by the team, in stock, not
    their own; and what they earn on each one."""

    _inherit = "product.template"

    @api.model
    def _ocd_ambassador_domain(self):
        return [
            ("is_published", "=", True), ("sale_ok", "=", True), ("ocd_review_state", "=", "approved"),
            ("type", "=", "consu"), "|", ("ocd_vendor_id", "=", False), ("ocd_vendor_id.ocd_sale_mode", "=", "ocd"),
        ]

    @api.model
    def _ocd_ambassador_own_vendors(self, ambassador):
        """The boutiques of the ambassador themselves (the same number): never shared for a gain."""
        numbers = ambassador._ocd_ambassador_numbers()
        if not numbers:
            return self.env["res.partner"]
        vendors = self.env["res.partner"].sudo().search([("ocd_is_vendor", "=", True), ("phone", "!=", False)])
        return vendors.filtered(lambda vendor: any(same_number(vendor.phone, number) for number in numbers))

    @api.model
    def _ocd_ambassador_products(self, ambassador, tab="best", search=None, offset=0, limit=30):
        """(products, more) of the tab `tab` (best, promo, live, new) for `ambassador`, the ones of
        their country first; `more`: whether there are others after."""
        Product = self.sudo()
        domain = self._ocd_ambassador_domain()
        own = self._ocd_ambassador_own_vendors(ambassador)
        if own:
            domain.append(("ocd_vendor_id", "not in", own.ids))
        if search:
            domain += ["|", ("name", "ilike", search), ("ocd_vendor_id.name", "ilike", search)]
        now = fields.Datetime.now()
        if tab == "promo":
            promos = self.env["ocd.product.promo"].sudo().search([
                ("active", "=", True), ("stopped_at", "=", False), ("date_start", "<=", now), ("date_end", ">", now),
            ])
            domain.append(("id", "in", promos.product_tmpl_id.ids))
        elif tab == "live":
            domain.append(("ocd_vendor_id", "in", self._ocd_ambassador_live_vendors(now).ids))
        order = "create_date desc, id desc" if tab == "new" else "website_sequence, id desc"
        products = Product.search(domain, order=order, limit=CANDIDATES)
        if tab == "best":
            sold = self._ocd_ambassador_sold(products, now)
            products = products.sorted(lambda product: (-sold.get(product.id, 0), product.website_sequence, -product.id))
        country = ambassador.country_id
        if country:
            products = products.sorted(lambda product: (product.ocd_vendor_id.country_id or self.env.company.country_id) != country)
        products = products._ocd_ambassador_in_stock()
        return products[offset:offset + limit], len(products) > offset + limit

    def _ocd_ambassador_in_stock(self):
        """The products of `self` that can be ordered: a product whose stock limits the sales has a
        piece free (the cart would refuse it otherwise); the stock read in one query."""
        tracked = self.filtered(lambda product: product.is_storable and not product.allow_out_of_stock_order)
        if not tracked:
            return self
        free = tracked.product_variant_ids._ocd_free_qties()
        return self.filtered(lambda product: product not in tracked or any(
            free.get(variant.id, 0) > 0 for variant in product.product_variant_ids))

    @api.model
    def _ocd_ambassador_sold(self, products, now):
        """{product: pieces sold these 7 days} of `products`."""
        if not products:
            return {}
        rows = self.env["sale.order.line"].sudo()._read_group(
            [("product_id.product_tmpl_id", "in", products.ids), ("state", "=", "sale"),
             ("order_id.date_order", ">=", now - timedelta(days=7))],
            ["product_id"], ["product_uom_qty:sum"],
        )
        sold = {}
        for variant, quantity in rows:
            sold[variant.product_tmpl_id.id] = sold.get(variant.product_tmpl_id.id, 0) + quantity
        return sold

    @api.model
    def _ocd_ambassador_live_vendors(self, now):
        """The vendors with a live today (at the hour of OCD), not ended yet."""
        company = self.env.company
        tz = company._ocd_tz()
        today = pytz.utc.localize(now).astimezone(tz).date()
        end = tz.localize(datetime.combine(today + timedelta(days=1), time())).astimezone(pytz.utc).replace(tzinfo=None)
        bookings = self.env["ocd.live.booking"].sudo().search([
            ("state", "=", "confirmed"), ("start_datetime", ">=", now - timedelta(hours=3)),
            ("start_datetime", "<", end),
        ])
        return bookings.partner_id

    def _ocd_ambassador_earn(self, company=None):
        """What an ambassador earns on one piece at the price of now, in the currency of OCD."""
        self.ensure_one()
        company = company or self.env.company
        price, _was = self.sudo()._ocd_on_sale_price()
        rate = company.ocd_ambassador_rate
        amount = price * rate / 100.0
        vendor = self.ocd_vendor_id
        if vendor:
            amount = min(amount, price * vendor.ocd_commission_rate / 100.0)
        # The price of now is in the currency of the company already
        if company.ocd_ambassador_cap:
            amount = min(amount, company.ocd_ambassador_cap)
        return company.currency_id.round(max(amount, 0.0))
