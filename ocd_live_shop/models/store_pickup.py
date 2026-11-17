"""Pick up in a store (chantier 20, A.1 and S.5 of the plan of « My products », design
RetraitMagasin).

The customer chooses « I come and get it » for the parcel of a vendor, in one of their stores that
has the whole parcel: no delivery fee. The parcel leaves from that store, the vendor prepares it
(« It is ready »: the customer is told, with the day it waits until), then hands it over at the
counter: paid online, or at the counter on the phone of the customer (Mobile Money, at every
vendor) or in cash (only at a vendor who already collects at the door, their commission kept on
the next payout). The code of the customer is accepted only once the money is collected.

A customer who does not come: a WhatsApp the day before the end, then the parcel is cancelled,
its pieces go back to the stock of the store, and the team refunds them when they paid online,
like a parcel returned after failed deliveries. Never at a vendor who sells from home."""
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.ocd_live import tools


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_store_pickup = fields.Boolean(
        string="Pick Up In A Store",
        default=True,
        help="The customers pick the parcel of a vendor up in one of their stores that has it, without "
        "delivery fee.",
    )
    ocd_collect_days = fields.Integer(
        string="Days To Pick Up A Parcel",
        default=3,
        help="A parcel ready in a store waits so many days for its customer (until the closing of the "
        "store on the last day): a reminder the day before, then it is cancelled.",
    )


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        """Override of `portal`: an order picked up in a store asks no address (the country of
        the WhatsApp number given is kept, it is not « an address started »)."""
        order = kwargs.get("order_sudo")
        if order and len(order) == 1 and order._ocd_collect_only():
            return set()
        return super()._get_mandatory_address_fields(country_sudo, **kwargs)


class OcdOrderDelivery(models.Model):
    _inherit = "ocd.order.delivery"

    pickup_place_id = fields.Many2one(
        comodel_name="ocd.vendor.place",
        string="Picked Up By The Customer At",
        ondelete="set null",
        help="The store where the customer picks the parcel up, without delivery fee.",
    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_collect_place_ids = fields.Many2many(
        comodel_name="ocd.vendor.place",
        relation="sale_order_ocd_collect_place_rel",
        column1="order_id",
        column2="place_id",
        string="Picked Up In",
        copy=False,
        help="The stores where the customer picks the parcels up (one per vendor).",
    )

    def _ocd_vendor_quantities(self, vendor):
        """{variant: pieces} of the products of `vendor` in the order."""
        self.ensure_one()
        pieces = {}
        for line in self.order_line.filtered(lambda l: not l.is_delivery and not l.display_type and l.product_id):
            if line.ocd_vendor_id == vendor:
                pieces[line.product_id] = pieces.get(line.product_id, 0) + line.product_uom_qty
        return pieces

    def _ocd_collect_options(self, vendor):
        """The stores of `vendor` the customer may pick their parcel up in: [(store, has the
        whole parcel)]; empty when the vendor offers no pickup (no store, a vendor whose
        products are in the stock of OCD, the setting off)."""
        self.ensure_one()
        company = self.company_id or self.env.company
        if not vendor or not company.ocd_store_pickup or not vendor.sudo()._ocd_stock_in_places():
            return []
        stores = self.env["ocd.vendor.place"]._ocd_shown_places(vendor).filtered(lambda place: place.kind == "store")
        if not stores:
            return []
        pieces = self._ocd_vendor_quantities(vendor)
        if not vendor._ocd_stock_per_place():
            # One place: its stock is the stock of the vendor, already checked by the cart
            return [(store, True) for store in stores]
        products = self.env["product.product"].browse([product.id for product in pieces])
        free = products._ocd_free_by_location(stores.location_id)
        return [(store, all(
            not product.is_storable or free.get((store.location_id.id, product.id), 0) >= qty
            for product, qty in pieces.items()
        )) for store in stores]

    def _ocd_collect_place(self, vendor):
        """The store chosen for the parcel of `vendor`, while it still has the whole parcel."""
        self.ensure_one()
        chosen = self.ocd_collect_place_ids.filtered(lambda place: place.vendor_id == vendor)[:1]
        if not chosen or self.state not in ("draft", "sent"):
            # A confirmed order keeps its store: its pieces are reserved there now
            return chosen
        return chosen if (chosen, True) in self._ocd_collect_options(vendor) else chosen.browse()

    def _ocd_set_collect_places(self, stores):
        """The stores chosen by the customer (one per vendor), each checked."""
        self.ensure_one()
        kept = self.env["ocd.vendor.place"]
        for store in stores:
            if (store, True) not in self._ocd_collect_options(store.vendor_id):
                raise UserError(self.env._(
                    "%s does not have your whole order any more: choose another store or the delivery.", store.name,
                ))
            kept |= store
        self.sudo().ocd_collect_place_ids = [fields.Command.set(kept.ids)]

    def _ocd_collect_only(self):
        """Whether every parcel of the order is picked up in a store (no address to deliver)."""
        self.ensure_one()
        if not self.ocd_collect_place_ids:
            return False
        groups = self._ocd_delivery_groups()
        return bool(groups) and all(vendor and self._ocd_collect_place(vendor) for vendor in groups)

    def _needs_customer_address(self):
        """Override of `website_sale`: every parcel picked up in a store, the customer gives their
        name and their WhatsApp, not an address."""
        if len(self) == 1 and self._ocd_collect_only():
            return False
        return super()._needs_customer_address()


class OcdDeliveryRate(models.Model):
    _inherit = "ocd.delivery.rate"

    @api.model
    def _ocd_collect_quote(self, vendor, store):
        """The « delivery » of a parcel picked up in `store`: free, paid online or at the counter."""
        return {
            "vendor": vendor,
            "rate": self.browse(),
            "operator": "store",
            "origin": store.city_id or store.district_id.city_id,
            "price": 0.0,
            "allow_cod": True,
            "description": self.env._("Pickup at %s", store.name),
            "error": False,
            "place": store,
        }


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ocd_collect = fields.Boolean(
        string="Picked Up At The Store",
        copy=False,
        index=True,
        help="The customer picks the parcel up at the store it leaves from (« Picked Up At »).",
    )
    ocd_collect_deadline = fields.Datetime(
        string="Picked Up Before",
        copy=False,
        help="The parcel ready in the store waits until then: a reminder the day before, then it is cancelled.",
    )
    ocd_collect_reminded_at = fields.Datetime(string="Reminded To Pick Up At", copy=False)

    def _ocd_assign_courier(self, courier):
        """Override: a parcel picked up at the store stays with its vendor, at the counter."""
        if courier and self.filtered(lambda picking: picking.ocd_collect and picking.ocd_vendor_id != courier):
            raise UserError(self.env._("The customer picks this parcel up at the store: no courier delivers it."))
        return super()._ocd_assign_courier(courier)

    def _ocd_collect_deadline_from(self, start):
        """The end of the wait of a parcel ready at `start`: the closing of the store on the day
        so many days later (the setting), else on its next day open; the end of that day for a
        store without hours."""
        self.ensure_one()
        place = self.ocd_pickup_place_id
        days = max(self.company_id.ocd_collect_days or 3, 1)
        tz = place._ocd_tz() if place else pytz.timezone(self.ocd_vendor_id._ocd_tz_name() if self.ocd_vendor_id else "UTC")
        day = pytz.utc.localize(start).astimezone(tz).date() + timedelta(days=days)
        intervals = place._ocd_intervals() if place else {}
        closing = None
        for offset in range(8):
            candidate = day + timedelta(days=offset)
            if place and place.closed_until and candidate <= place.closed_until:
                continue
            hours = intervals.get(candidate.weekday()) if intervals else None
            if hours:
                closing = tz.localize(datetime.combine(candidate, time()) + timedelta(hours=max(end for _start, end in hours)))
                break
        if closing is None:
            closing = tz.localize(datetime.combine(day, time(23, 59)))
        return closing.astimezone(pytz.utc).replace(tzinfo=None)

    def _ocd_collect_deadline_text(self, lang=None):
        """« Thursday 20 November at 19:00 », at the hour of the store; in `lang` when it is
        installed (the language of a WhatsApp template), else in the one of the context."""
        self.ensure_one()
        if lang and lang != self.env.lang and self.env["res.lang"]._ocd_is_active(lang):
            return self.with_context(lang=lang)._ocd_collect_deadline_text()
        if not self.ocd_collect_deadline:
            return ""
        place = self.ocd_pickup_place_id
        tz = place._ocd_tz() if place else pytz.utc
        local = pytz.utc.localize(self.ocd_collect_deadline).astimezone(tz)
        return self.env._("%(day)s at %(hour)s", day=tools.day_text(self.env, local.date(), "EEEE d MMMM"),
                          hour=local.strftime("%H:%M"))

    def action_ocd_collect_ready(self):
        """« It is ready »: the parcel waits for its customer in the store; they are told, with
        the day it waits until, and find their code on the tracking page."""
        self._ocd_check_stage(("to_prepare",))
        now = fields.Datetime.now()
        for picking in self:
            if not picking.ocd_collect:
                raise UserError(self.env._("The parcel %s is delivered, not picked up at the store.", picking.name))
            picking_sudo = picking.sudo()
            values = {
                "ocd_stage": "ready",
                "ocd_ready_at": now,
                "ocd_code_sent_at": now,
                "ocd_collect_deadline": picking._ocd_collect_deadline_from(now),
            }
            if not picking_sudo.ocd_delivery_code:
                values.update({"ocd_delivery_code": picking._ocd_new_code(), "ocd_code_attempts": 0})
            picking_sudo.write(values)
            picking._ocd_notify_customer("collect_ready")
        return True

    @api.model
    def _cron_ocd_collect(self):
        """The parcels waiting in a store: a reminder the day before the end, then cancelled."""
        now = fields.Datetime.now()
        waiting = self.search([
            ("ocd_is_parcel", "=", True), ("ocd_collect", "=", True), ("ocd_stage", "=", "ready"),
            ("ocd_collect_deadline", "!=", False),
        ])
        for picking in waiting:
            if picking.ocd_collect_deadline <= now:
                picking._ocd_collect_expire()
            elif not picking.ocd_collect_reminded_at and picking.ocd_collect_deadline - timedelta(days=1) <= now:
                picking.ocd_collect_reminded_at = now
                picking._ocd_notify_customer("collect_reminder")

    def _ocd_collect_expire(self):
        """Not picked up in time: cancelled, the pieces back in the store, refunded when paid
        online (like a parcel returned after failed deliveries)."""
        for picking in self:
            picking.message_post(body=self.env._("Not picked up before %s: the parcel is cancelled.",
                                                 picking._ocd_collect_deadline_text()))
            picking._ocd_return(event="collect_expired")
        return True
