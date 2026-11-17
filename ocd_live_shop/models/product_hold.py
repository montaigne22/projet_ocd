"""Hold a piece to try it in a store (chantier 20, A.7 of the plan of « My products », design
MettreDeCote).

From the page of a product, the customer holds a piece (a colour and a size) in a store of the
vendor that has it, to come and try it: they pay only if they take it, at the store. The piece is
reserved there at once (it is no longer free for the other customers), the vendor is told on
WhatsApp and answers « OK » or « Refuse »; without an answer the piece stays held. At the store
the vendor says how it went: bought (the piece leaves the stock of the store), not bought or the
customer did not come (the piece is on sale again). Past the deadline, the piece comes back by
itself.

Guards (settings): the time the piece is held (24 hours by default, moved to the closing of the
store when it is closed then), one hold at a time at a vendor, no more holds at a vendor after
two absences there (the vendor can unblock the customer)."""
import uuid
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.ocd_live import tools

ACTIVE = ("requested", "accepted")


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_hold_enabled = fields.Boolean(
        string="Hold A Piece To Try",
        default=True,
        help="From the page of a product, the customers hold a piece in a store that has it, to come "
        "and try it; they pay only if they take it.",
    )
    ocd_hold_hours = fields.Integer(
        string="Hours A Piece Is Held",
        default=24,
        help="Then the piece is on sale again. A store closed at that hour holds it until its next "
        "closing.",
    )
    ocd_hold_max_absences = fields.Integer(
        string="Absences Before No More Holds",
        default=2,
        help="A customer who did not come so many times can no longer hold a piece at this vendor "
        "(the vendor can unblock them).",
    )


class ResLang(models.Model):
    _inherit = "res.lang"

    @api.model
    def _ocd_is_active(self, code):
        """Whether the language `code` is installed: a text asked in it can be written in it."""
        return bool(self.sudo().search_count([("code", "=", code), ("active", "=", True)], limit=1))


class OcdProductHold(models.Model):
    _name = "ocd.product.hold"
    _description = "Piece Held In A Store To Try"
    _order = "id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Customer", required=True, index=True, ondelete="cascade"
    )
    place_id = fields.Many2one(
        comodel_name="ocd.vendor.place", string="Store", required=True, index=True, ondelete="cascade",
        check_company=True,
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", related="place_id.vendor_id", store=True, index=True
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    state = fields.Selection(
        selection=[
            ("requested", "Held, waiting for the vendor"),
            ("accepted", "Held, accepted by the vendor"),
            ("taken", "Bought at the store"),
            ("not_taken", "Tried, not bought"),
            ("no_show", "The customer did not come"),
            ("refused", "Refused by the vendor"),
            ("cancelled", "Cancelled by the customer"),
            ("expired", "Time over"),
        ],
        required=True,
        default="requested",
        index=True,
    )
    deadline = fields.Datetime(string="Held Until", required=True)
    answered_at = fields.Datetime(string="Answered At", readonly=True)
    closed_at = fields.Datetime(string="Closed At", readonly=True)
    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Reservation", readonly=True, ondelete="set null",
        help="Reserves the piece in the store while it is held; done when the customer buys it.",
    )
    forgiven = fields.Boolean(
        string="Absence Forgiven", help="The vendor unblocked the customer: this absence no longer counts."
    )
    access_token = fields.Char(copy=False, readonly=True, groups="base.group_system")

    _one_active_hold = models.UniqueIndex(
        "(partner_id, vendor_id) WHERE state IN ('requested', 'accepted')",
        "One piece held at a time at a vendor.",
    )

    @api.depends("product_id", "partner_id")
    def _compute_display_name(self):
        for hold in self:
            hold.display_name = self.env._(
                "%(product)s for %(customer)s", product=hold.product_id.display_name, customer=hold.partner_id.name,
            )

    # === WHAT IS OFFERED === #

    @api.model
    def _ocd_offered(self, place):
        """Whether the customers may hold a piece in `place`: a store online, its vendor not on
        holiday, the setting on."""
        place = place.sudo()
        company = place.company_id or self.env.company
        vendor = place.vendor_id
        return bool(
            company.ocd_hold_enabled and place.kind == "store" and place.location_id and vendor
            and not vendor._ocd_on_holiday() and place in self.env["ocd.vendor.place"]._ocd_shown_places(vendor)
        )

    @api.model
    def _ocd_absences(self, partner, vendor):
        """The times `partner` did not come to the stores of `vendor` (not forgiven)."""
        return self.sudo().search_count([
            ("partner_id", "=", partner.id), ("vendor_id", "=", vendor.id), ("state", "=", "no_show"),
            ("forgiven", "=", False),
        ])

    @api.model
    def _ocd_blocked(self, partner, vendor):
        company = vendor.company_id or self.env.company
        limit = company.ocd_hold_max_absences
        return bool(limit) and self._ocd_absences(partner, vendor) >= limit

    # === THE CUSTOMER === #

    @api.model
    def _ocd_contact(self, phone):
        """The contact of the WhatsApp number `phone` (normalized), created when unknown."""
        Partner = self.env["res.partner"].sudo()
        partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
        return partner or Partner.create({"name": phone, "phone": phone})

    @api.model
    def _ocd_request(self, place, product, partner):
        """Hold one piece of `product` (a variant) in `place` for `partner`: checked, reserved,
        the vendor told. Return the hold."""
        place, product, partner = place.sudo(), product.sudo(), partner.sudo()
        vendor = place.vendor_id
        template = product.product_tmpl_id
        if not self._ocd_offered(place):
            raise UserError(self.env._("This store does not hold pieces to try."))
        if (
            template.ocd_vendor_id != vendor or not template.is_published or not template.sale_ok
            or template.ocd_review_state != "approved" or not product.active
        ):
            raise UserError(self.env._("This product cannot be held in this store."))
        active = self.sudo().search(
            [("partner_id", "=", partner.id), ("vendor_id", "=", vendor.id), ("state", "in", ACTIVE)], limit=1
        )
        if active:
            raise UserError(self.env._(
                "You already hold %(product)s at %(store)s: try it first, or tell them you no longer come.",
                product=active.product_id.display_name, store=active.place_id.name,
            ))
        if self._ocd_blocked(partner, vendor):
            raise UserError(self.env._(
                "You did not come several times: holding a piece is no longer possible at %s.", vendor.name,
            ))
        if product.is_storable and product._ocd_free_qty(place.location_id) < 1:
            raise UserError(self.env._("No piece left in this size at %s.", place.name))
        now = fields.Datetime.now()
        hold = self.sudo().create({
            "partner_id": partner.id,
            "place_id": place.id,
            "product_id": product.id,
            "company_id": place.company_id.id or self.env.company.id,
            "deadline": now + timedelta(hours=1),  # set below, once the store is known
            "access_token": str(uuid.uuid4()),
        })
        hold.deadline = hold._ocd_deadline_from(now)
        if product.is_storable:
            hold._ocd_reserve()
        hold._ocd_notify_vendor()
        return hold

    def _ocd_cancel_by_customer(self):
        """« I no longer come »: the piece is on sale again."""
        self._ocd_close(ACTIVE, "cancelled")
        return True

    # === THE VENDOR === #

    def action_ocd_accept(self):
        """« OK »: the customer is told the store keeps the piece for them."""
        for hold in self:
            hold._ocd_check_state(("requested",))
            hold.sudo().write({"state": "accepted", "answered_at": fields.Datetime.now()})
            hold._ocd_notify_customer("accepted")
        return True

    def action_ocd_refuse(self):
        """« Refuse »: the piece is on sale again, the customer is told (they can order it)."""
        for hold in self:
            hold._ocd_check_state(ACTIVE)
            hold.sudo().answered_at = hold.answered_at or fields.Datetime.now()
            hold._ocd_close(ACTIVE, "refused")
            hold._ocd_notify_customer("refused")
        return True

    def action_ocd_outcome(self, outcome):
        """How it went at the store: « bought » (the piece leaves the stock of the store), « not
        bought » or « did not come » (the piece is on sale again)."""
        if outcome not in ("taken", "not_taken", "no_show"):
            raise UserError(self.env._("Choose how it went."))
        self._ocd_close(ACTIVE, outcome)
        return True

    def action_ocd_unblock(self):
        """The vendor lets the customer hold pieces again: their absences no longer count."""
        for hold in self:
            self.sudo().search([
                ("partner_id", "=", hold.partner_id.id), ("vendor_id", "=", hold.vendor_id.id),
                ("state", "=", "no_show"), ("forgiven", "=", False),
            ]).write({"forgiven": True})
        return True

    # === THE PIECE === #

    def _ocd_check_state(self, states):
        for hold in self:
            if hold.state not in states:
                raise UserError(self.env._("This hold is already over."))

    def _ocd_close(self, states, state):
        """End the holds in `states` with `state`: the piece leaves the stock when bought, else it
        is free again."""
        self._ocd_check_state(states)
        now = fields.Datetime.now()
        for hold in self:
            hold.sudo().write({"state": state, "closed_at": now})
            if state == "taken":
                hold._ocd_sell()
            else:
                hold._ocd_release()

    def _ocd_reserve(self):
        """Reserve the piece in the store: a delivery from the store to the customer, waiting
        (its piece is no longer free), done when they buy it, cancelled otherwise."""
        self.ensure_one()
        place = self.place_id.sudo()
        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", self.company_id.id)], limit=1)
        customers = self.env.ref("stock.stock_location_customers")
        picking = self.env["stock.picking"].sudo().create({
            "picking_type_id": warehouse.out_type_id.id,
            "partner_id": self.partner_id.id,
            "location_id": place.location_id.id,
            "location_dest_id": customers.id,
            "origin": self.env._("Held to try: %s", self.display_name),
            "ocd_vendor_id": self.vendor_id.id,
            "move_ids": [fields.Command.create({
                "product_id": self.product_id.id,
                "product_uom_qty": 1,
                "uom_id": self.product_id.uom_id.id,
                "location_id": place.location_id.id,
                "location_dest_id": customers.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        if picking.state != "assigned":
            picking.action_cancel()
            raise UserError(self.env._("No piece left in this size at %s.", place.name))
        self.sudo().picking_id = picking

    def _ocd_release(self):
        """The piece is free again; the customers waiting for it are told soon."""
        for hold in self:
            picking = hold.sudo().picking_id
            if picking and picking.state not in ("done", "cancel"):
                picking.action_cancel()
        if self.picking_id:
            cron = self.env.ref("ocd_live_shop.ir_cron_stock_alerts", raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()

    def _ocd_sell(self):
        """Bought at the store: the piece leaves its stock."""
        for hold in self:
            picking = hold.sudo().picking_id
            if picking and picking.state not in ("done", "cancel"):
                picking._ocd_validate_transfer()

    @api.model
    def _cron_ocd_holds(self):
        """The holds past their deadline: the piece is on sale again (not an absence: nobody
        said the customer did not come)."""
        self.sudo().search([("state", "in", ACTIVE), ("deadline", "<=", fields.Datetime.now())])._ocd_close(
            ACTIVE, "expired"
        )

    # === TIME === #

    def _ocd_deadline_from(self, start):
        """`start` + the hours of the setting; when the store is closed then, its next closing
        (the customer can still come). As is for a store without hours."""
        self.ensure_one()
        place = self.place_id.sudo()
        hours = max(self.company_id.ocd_hold_hours or 24, 1)
        end = start + timedelta(hours=hours)
        tz = place._ocd_tz()
        local = pytz.utc.localize(end).astimezone(tz)
        intervals = place._ocd_intervals()
        if not any(intervals.values()):
            return end
        moment = local.hour + local.minute / 60
        for offset in range(8):
            day = local.date() + timedelta(days=offset)
            if place.closed_until and day <= place.closed_until:
                continue
            for opening, closing in intervals[day.weekday()]:
                if offset == 0 and closing <= moment:
                    continue
                if offset == 0 and opening <= moment:
                    return end  # open at that moment
                closes = tz.localize(datetime.combine(day, time()) + timedelta(hours=closing))
                return closes.astimezone(pytz.utc).replace(tzinfo=None)
        return end

    def _ocd_deadline_text(self, lang=None):
        """« today at 19:00 », « tomorrow at 14:00 », « Thursday 20 November at 14:00 », at the
        hour of the store; in `lang` when it is installed (the language of a WhatsApp template),
        else in the one of the context."""
        self.ensure_one()
        if lang and lang != self.env.lang and self.env["res.lang"]._ocd_is_active(lang):
            return self.with_context(lang=lang)._ocd_deadline_text()
        tz = self.place_id.sudo()._ocd_tz()
        local = pytz.utc.localize(self.deadline).astimezone(tz)
        today = pytz.utc.localize(fields.Datetime.now()).astimezone(tz).date()
        hour = local.strftime("%H:%M")
        if local.date() == today:
            return self.env._("today at %s", hour)
        if local.date() == today + timedelta(days=1):
            return self.env._("tomorrow at %s", hour)
        return self.env._("%(day)s at %(hour)s", day=tools.day_text(self.env, local.date(), "EEEE d MMMM"), hour=hour)

    # === LINKS AND MESSAGES === #

    def _ocd_page_path(self):
        """The page of the hold for the customer, without logging in (its token): « I no longer
        come », the itinerary."""
        self.ensure_one()
        return f"ocd/essayer/{self.id}?t={self.sudo().access_token}"

    def _ocd_product_path(self):
        """The page of the product, to order it online."""
        self.ensure_one()
        return (self.product_id.sudo().website_url or "/shop").lstrip("/")

    def _ocd_notify_vendor(self):
        """Tell the vendor a piece is held (extended by ocd_live_shop_whatsapp)."""

    def _ocd_notify_customer(self, event):
        """Tell the customer the answer of the vendor (extended by ocd_live_shop_whatsapp)."""
