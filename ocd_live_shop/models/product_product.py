from odoo import api, models

# Most pieces of one product a vendor can have in one place (a typo of the stepper or of the
# field stays readable)
MAX_STOCK = 9999


class ProductProduct(models.Model):
    _inherit = "product.product"

    # === STOCK CHANGED BY THE VENDOR === #

    @api.model
    def _ocd_stock_root(self, company=None):
        """The stock of the main warehouse of the company: every piece of the shop, the places
        of the vendors included (their locations are inside it)."""
        company = company or self.env.company
        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", company.id)], limit=1)
        return warehouse.lot_stock_id

    def _ocd_stock_location(self):
        """Where a piece of the product goes when no place is said: the main place of its vendor
        (the place the parcels leave from), else the stock of the shop."""
        self.ensure_one()
        vendor = self.sudo().product_tmpl_id.ocd_vendor_id
        place = vendor._ocd_main_stock_place() if vendor else None
        if place:
            return place._ocd_location()
        return self._ocd_stock_root(self.company_id or self.env.company)

    def _ocd_free_qties(self, location=None):
        """{variant id: pieces free to sell} for the variants of `self` at `location` (all the
        stock of the shop by default, the places of the vendors included), in one query: the
        stock minus what is reserved for the orders not delivered yet."""
        free = dict.fromkeys(self.ids, 0)
        location = location or (self._ocd_stock_root(self[:1].company_id or self.env.company) if self else None)
        if not self or not location:
            return free
        groups = self.env["stock.quant"].sudo()._read_group(
            [("product_id", "in", self.ids), ("location_id", "child_of", location.id)],
            ["product_id"], ["quantity:sum", "reserved_quantity:sum"],
        )
        for product, quantity, reserved in groups:
            free[product.id] = max(int(quantity - reserved), 0)
        return free

    def _ocd_free_qty(self, location=None):
        """Pieces of the variant free to sell at `location` (see `_ocd_free_qties`)."""
        self.ensure_one()
        return self._ocd_free_qties(location)[self.id]

    def _ocd_change_stock(self, delta, location=None):
        """Add `delta` pieces (remove them when negative) to the free stock of the variant at
        `location`, as an inventory adjustment: each change is traced in the stock moves.

        The pieces reserved for an order are never taken away, so the free stock stops at 0 and
        at MAX_STOCK. Two taps sent at the same time both count: the change is added to the stock
        of the moment, never written over it (a concurrent write of the same quant makes the
        request start again). Return the free stock after the change."""
        self.ensure_one()
        location = location or self._ocd_stock_location()
        if not location:
            return 0
        free = self._ocd_free_qty(location)
        delta = min(max(int(delta), -free), MAX_STOCK - free)
        if not delta:
            return free
        Quant = self.env["stock.quant"].sudo().with_context(inventory_mode=True)
        quant = Quant.search([
            ("product_id", "=", self.id), ("location_id", "=", location.id),
            ("lot_id", "=", False), ("package_id", "=", False), ("owner_id", "=", False),
        ], order="quantity desc", limit=1)
        if not quant:
            quant = Quant.create({"product_id": self.id, "location_id": location.id})
        quant.inventory_quantity = quant.quantity + delta
        quant.action_apply_inventory()
        return free + delta

    def _ocd_set_free_stock(self, quantity, location=None):
        """Make the free stock of the variant `quantity` at `location` (the main place of its
        vendor by default, see `_ocd_change_stock`)."""
        self.ensure_one()
        location = location or self._ocd_stock_location()
        return self._ocd_change_stock(int(quantity) - self._ocd_free_qty(location), location)

    def _ocd_free_by_location(self, locations):
        """{(location id, variant id): pieces free to sell} for the variants of `self` in each of
        `locations` (the places of a vendor), in one query."""
        if not self or not locations:
            return {}
        groups = self.env["stock.quant"].sudo()._read_group(
            [("product_id", "in", self.ids), ("location_id", "in", locations.ids)],
            ["location_id", "product_id"], ["quantity:sum", "reserved_quantity:sum"],
        )
        return {(location.id, product.id): max(int(quantity - reserved), 0)
                for location, product, quantity, reserved in groups}

    def _is_add_to_cart_allowed(self):
        """Override of `website_sale`: the products of a vendor in direct contact are not sold
        on the website (OCD Live does not take the money), the customer writes to the vendor."""
        allowed = super()._is_add_to_cart_allowed()
        vendor = self.sudo().product_tmpl_id.ocd_vendor_id
        # A vendor on holiday: the orders are paused (chantier 20)
        return allowed and not (vendor and (vendor.ocd_sale_mode == "direct" or vendor._ocd_on_holiday()))
