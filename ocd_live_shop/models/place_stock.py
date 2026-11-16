"""The stock of the places of a vendor (chantier 18, « Stock par magasin » of the plan).

Each place of a vendor has its own location of stock, inside the stock of the warehouse of the
shop: the website still counts all the pieces of a product (its availability is computed on the
warehouse), and each place has its own. Not a warehouse per store: a warehouse makes its own
locations, operations, routes and numbers, and the products of the other stores would seem sold
out.

- The first place of a vendor receives the pieces they had (S.1); a place removed gives its
  pieces back to the main place of the vendor (the place the parcels leave from).
- The vendors whose products are kept in the stock of OCD Live are not concerned.
- Every move of pieces is an internal transfer of the stock, traced with its reference."""
from collections import defaultdict

from odoo import Command, api, fields, models


class OcdVendorPlace(models.Model):
    _inherit = "ocd.vendor.place"

    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Stock Location",
        readonly=True,
        copy=False,
        index="btree_not_null",
        help="Where the pieces of the place are counted, inside the stock of the shop: the website still counts them all.",
    )
    ocd_stock_count = fields.Integer(
        string="Pieces Free To Sell",
        compute="_compute_ocd_stock_count",
        help="The pieces of the products of the vendor in this place, minus the ones kept for an order.",
    )

    def _compute_ocd_stock_count(self):
        counts = dict.fromkeys(self.ids, 0)
        with_location = self.filtered("location_id")
        if with_location:
            groups = self.env["stock.quant"].sudo()._read_group(
                [("location_id", "in", with_location.location_id.ids)],
                ["location_id"], ["quantity:sum", "reserved_quantity:sum"],
            )
            by_location = {location.id: max(int(quantity - reserved), 0) for location, quantity, reserved in groups}
            for place in with_location:
                counts[place.id] = by_location.get(place.location_id.id, 0)
        for place in self:
            place.ocd_stock_count = counts.get(place.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        places = super().create(vals_list)
        places._ocd_take_stock()
        return places

    def write(self, vals):
        leaving = self.filtered("active") if "active" in vals and not vals["active"] else self.browse()
        result = super().write(vals)
        if vals.get("active"):
            self._ocd_take_stock()
        if leaving:
            leaving._ocd_give_back_stock()
        if "name" in vals:
            for place in self.filtered("location_id"):
                place.location_id.sudo().name = place._ocd_location_name()
        return result

    def _ocd_location_name(self):
        self.ensure_one()
        return f"{self.vendor_id.name} · {self.name}"

    def _ocd_location(self):
        """The location of stock of the place, made the first time it is needed."""
        self.ensure_one()
        place = self.sudo()
        if not place.location_id:
            root = self.env["product.product"]._ocd_stock_root(place.company_id)
            place.location_id = self.env["stock.location"].sudo().create({
                "name": place._ocd_location_name(),
                "location_id": root.id,
                "usage": "internal",
                "company_id": root.company_id.id,
            })
        return place.location_id

    def _ocd_take_stock(self, receive=False):
        """A place of a vendor who keeps their pieces: its location of stock; the first one (or
        the places given, when `receive`) receives the pieces the vendor had in the stock of the
        shop."""
        for place in self.sudo().filtered(lambda p: p.active and p.vendor_id._ocd_stock_in_places()):
            location = place._ocd_location()
            vendor = place.vendor_id
            if receive or vendor._ocd_stock_places() == place:
                root = self.env["product.product"]._ocd_stock_root(place.company_id)
                free = vendor._ocd_free_pieces(root, exact=True)
                self.env["stock.picking"]._ocd_transfer(
                    free, root, location, origin=self.env._("First place of %s", vendor.name),
                )

    def _ocd_give_back_stock(self):
        """A place removed: its free pieces go to the main place of the vendor (else back to the
        stock of the shop). The pieces kept for an order leave from it with their parcel."""
        for place in self.sudo().filtered("location_id"):
            vendor = place.vendor_id
            main = vendor._ocd_main_stock_place()
            destination = main._ocd_location() if main else self.env["product.product"]._ocd_stock_root(place.company_id)
            free = vendor._ocd_free_pieces(place.location_id, exact=True)
            self.env["stock.picking"]._ocd_transfer(
                free, place.location_id, destination, origin=self.env._("Place removed: %s", place.name),
            )


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_stock_in_places(self):
        """Whether the pieces of the vendor are counted in their places: not for the products
        kept in the stock of OCD Live."""
        self.ensure_one()
        mode = self.ocd_delivery_mode or (self.company_id or self.env.company).ocd_default_delivery_mode
        return bool(self.ocd_is_vendor) and mode != "stock"

    def _ocd_stock_places(self):
        """The places of the vendor that keep pieces, in their order (none for a vendor whose
        products are in the stock of OCD Live)."""
        self.ensure_one()
        Place = self.env["ocd.vendor.place"].sudo()
        if not self._ocd_stock_in_places():
            return Place
        return Place.search([("vendor_id", "=", self.id)], order="sequence, id")

    def _ocd_main_stock_place(self):
        """Where a piece goes when no place is said: the place the parcels leave from, else the
        first place of the vendor."""
        self.ensure_one()
        places = self._ocd_stock_places()
        departure = self.sudo()._ocd_departure_place()
        return departure if departure and departure in places else places[:1]

    def _ocd_stock_per_place(self):
        """The stock of each place shows from two places on (one place: nothing changes for the
        vendor)."""
        self.ensure_one()
        return len(self._ocd_stock_places()) >= 2

    def _ocd_serving_plan(self, quantities, city=None):
        """Where the pieces of an order leave from (S.4 of the plan): {place: {variant: qty}},
        empty for a vendor with less than two places (nothing to choose).

        - a place in the city of the customer that has every piece;
        - else the place the parcels leave from, if it has every piece;
        - else another place that has every piece;
        - else a parcel per place: each product from the first of these places that has it all,
          else from the place that has the most of it.
        A product whose stock is not counted is found everywhere."""
        self.ensure_one()
        places = self._ocd_stock_places()
        quantities = {product: qty for product, qty in quantities.items() if qty > 0}
        # Without a counted stock, nothing says where the pieces are: the place the parcels
        # leave from (A.4)
        if len(places) < 2 or not any(product.is_storable for product in quantities):
            return {}
        products = self.env["product.product"].browse([product.id for product in quantities])
        free = products._ocd_free_by_location(places.location_id)
        departure = self._ocd_main_stock_place()
        in_city = places.filtered(lambda p: city and (p.city_id or p.district_id.city_id) == city)
        ordered = in_city | departure | places

        def has(place, product, qty):
            return not product.is_storable or free.get((place.location_id.id, product.id), 0) >= qty

        for place in ordered:
            if all(has(place, product, qty) for product, qty in quantities.items()):
                return {place: quantities}
        plan = defaultdict(dict)
        for product, qty in quantities.items():
            place = next((p for p in ordered if has(p, product, qty)), None) or max(
                ordered, key=lambda p: free.get((p.location_id.id, product.id), 0)
            )
            plan[place][product] = qty
        return dict(plan)

    def _ocd_free_pieces(self, location, exact=False):
        """{variant: pieces free to sell} of the products of the vendor at `location` (with its
        sub-locations, or only there when `exact`), the pieces kept for an order left out."""
        self.ensure_one()
        operator = "=" if exact else "child_of"
        groups = self.env["stock.quant"].sudo()._read_group(
            [
                ("location_id", operator, location.id),
                ("product_id.product_tmpl_id.ocd_vendor_id", "=", self.id),
            ],
            ["product_id"], ["quantity:sum", "reserved_quantity:sum"],
        )
        return {product: int(quantity - reserved) for product, quantity, reserved in groups if quantity - reserved >= 1}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ocd_stock_by_place = fields.Char(
        string="Stock Per Place",
        compute="_compute_ocd_stock_by_place",
        help="The pieces free to sell in each place of the vendor (from two places on).",
    )

    def _compute_ocd_stock_by_place(self):
        for product in self:
            vendor = product.sudo().ocd_vendor_id
            places = vendor._ocd_stock_places() if vendor else self.env["ocd.vendor.place"]
            if len(places) < 2:
                product.ocd_stock_by_place = False
                continue
            free = product.product_variant_ids._ocd_free_by_location(places.location_id)
            product.ocd_stock_by_place = " · ".join(
                f"{place.name}: {sum(free.get((place.location_id.id, variant.id), 0) for variant in product.product_variant_ids)}"
                for place in places
            )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ocd_split_by_place(self):
        """The new deliveries of the vendors with several places, before their pieces are
        kept: each one leaves from the place chosen by `_ocd_serving_plan`, a parcel per place
        when no place has everything. Return the deliveries, the new ones included."""
        result = self.browse()
        for picking in self:
            vendor = picking.sudo().ocd_vendor_id
            moves = picking.move_ids.filtered(lambda m: m.state not in ("cancel", "done"))
            if (
                picking.ocd_is_parcel or picking.picking_type_code != "outgoing" or not picking.sale_id
                or not vendor or moves.move_line_ids
            ):
                result |= picking
                continue
            quantities = defaultdict(float)
            for move in moves:
                quantities[move.product_id] += move.product_uom_qty
            customer = picking.partner_id
            plan = vendor._ocd_serving_plan(quantities, customer.city_id or customer.district_id.city_id)
            if not plan:
                result |= picking
                continue
            for index, (place, products) in enumerate(plan.items()):
                target = picking if index == 0 else picking.copy({
                    "move_ids": [], "ocd_vendor_id": vendor.id, "ocd_pickup_place_id": False,
                })
                place_moves = moves.filtered(lambda m: m.product_id in products)
                location = place._ocd_location()
                place_moves.write({"picking_id": target.id, "location_id": location.id})
                target.write({"location_id": location.id, "ocd_pickup_place_id": place.id})
                result |= target
        return result

    @api.model
    def _ocd_transfer(self, quantities, source, destination, note=False, origin=False):
        """Move `quantities` {variant: pieces} from the location `source` to `destination` at
        once: an internal transfer of the stock, done, traced with its reference. Return it."""
        quantities = {product: int(qty) for product, qty in quantities.items() if int(qty) > 0}
        if not quantities or source == destination:
            return self.browse()
        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", source.company_id.id)], limit=1)
        picking = self.sudo().create({
            "picking_type_id": warehouse.int_type_id.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "origin": origin or False,
            "note": note or False,
            "move_ids": [
                Command.create({
                    "product_id": product.id,
                    "product_uom_qty": qty,
                    "uom_id": product.uom_id.id,
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                })
                for product, qty in quantities.items()
            ],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = min(move.quantity, move.product_uom_qty)
            move.picked = True
        picking.with_context(skip_backorder=True, picking_ids_not_to_backorder=picking.ids, skip_sms=True).button_validate()
        return picking
