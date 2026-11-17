"""The team of a vendor (chantier 22, A.9 of the plan of « My products », design EquipeDuVendeur).

The person who holds a store of the vendor has her own access, with her WhatsApp number like the
vendor (personal link or code): the stock of her store, without the prices, and its parcels, its
pickups at the counter and its pieces to try, without the payouts. She never sees the other
stores of the vendor and never adds a product.

The vendor adds and removes the people of the team from « My team »: at most 5 (setting, or the
number written on the vendor). OCD Business only: when the formula ends, the team is paused,
nothing is deleted, and it comes back with the formula. A person removed loses the access at
once; her history stays (archived)."""
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

# A visit is written at most every few minutes: each page of the person does not write
VISIT_EVERY = timedelta(minutes=5)


class OcdVendorMember(models.Model):
    _name = "ocd.vendor.member"
    _description = "Person Of The Team Of A Vendor"
    _order = "vendor_id, create_date, id"

    name = fields.Char(required=True, help="The name the vendor gave, shown to the vendor and in the messages.")
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="cascade",
        domain="[('ocd_is_vendor', '=', True)]",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact", required=True, index=True, ondelete="cascade",
        help="The contact of the WhatsApp number: the person logs in with it, as the vendors do.",
    )
    phone = fields.Char(related="partner_id.phone", string="WhatsApp")
    place_id = fields.Many2one(
        comodel_name="ocd.vendor.place", string="Store", required=True, index=True, ondelete="cascade",
        domain="[('vendor_id', '=', vendor_id)]",
        help="The store she holds: she sees its stock and its parcels only.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True, help="Removed from the team: no access, the history stays.")
    invited_at = fields.Datetime(string="Link Sent At", readonly=True, copy=False)
    last_visit = fields.Datetime(string="Last Visit", readonly=True, copy=False)
    state = fields.Selection(
        selection=[("waiting", "Not come yet"), ("active", "Active"), ("paused", "Paused")],
        compute="_compute_state",
        help="Paused: the vendor no longer has OCD Business, or the store is removed. Nothing is deleted.",
    )

    @api.depends("last_visit", "place_id.active", "vendor_id.ocd_business_until", "vendor_id.ocd_is_vendor")
    def _compute_state(self):
        for member in self:
            if member._ocd_paused():
                member.state = "paused"
            else:
                member.state = "active" if member.last_visit else "waiting"

    # === RULES === #

    @api.constrains("partner_id", "vendor_id", "place_id", "active")
    def _check_member(self):
        for member in self.filtered("active"):
            person = member.partner_id
            if person == member.vendor_id or person.ocd_is_vendor or person.ocd_is_courier:
                raise ValidationError(self.env._(
                    "%s is a vendor or a courier of OCD Live: choose another person.", person.name
                ))
            if not person.phone:
                raise ValidationError(self.env._("Add the WhatsApp number of %s first: she logs in with it.", person.name))
            if member.place_id.vendor_id != member.vendor_id:
                raise ValidationError(self.env._("The store must be a store of the vendor."))
            other = self.sudo().search(
                [("partner_id", "=", person.id), ("id", "!=", member.id)], limit=1
            )
            if other:
                raise ValidationError(self.env._(
                    "%(person)s is already in the team of %(vendor)s.", person=member.name, vendor=other.vendor_id.name
                ))

    @api.constrains("vendor_id", "active")
    def _check_team_size(self):
        for vendor in self.filtered("active").vendor_id:
            allowed = vendor._ocd_team_allowed()
            if not allowed:
                raise ValidationError(self.env._("The team of the vendors comes with OCD Business."))
            if self.sudo().search_count([("vendor_id", "=", vendor.id)]) > allowed:
                raise ValidationError(self.env._(
                    "%s people at most in a team: remove someone first.", allowed
                ))

    # === WHAT THE VENDOR DOES === #

    @api.model
    def _ocd_add(self, vendor, name, number, place):
        """Add the person of the WhatsApp number `number` (normalized) to the team of `vendor`,
        for `place`, and send her the link. Return the person of the team."""
        vendor, place = vendor.sudo(), place.sudo()
        env = self.env
        name = " ".join((name or "").split())[:80]
        if not vendor._ocd_team_allowed():
            raise UserError(env._("The team comes with OCD Business."))
        if not vendor._ocd_stock_in_places():
            raise UserError(env._("Your pieces are kept in the stock of OCD Live: your stores have no stock to hold."))
        if not name:
            raise UserError(env._("Give the name of the person."))
        if not number:
            raise UserError(env._("Give the WhatsApp number of the person."))
        if not place or place.vendor_id != vendor or not place.active or place.state == "refused":
            raise UserError(env._("Choose one of your stores."))
        Partner = env["res.partner"].sudo()
        if (
            Partner._ocd_find_vendor_by_phone(number)
            or Partner._ocd_find_by_phone(number, [("ocd_is_courier", "=", True)])
        ):
            raise UserError(env._("This number is already the one of a vendor or a courier: choose another one."))
        known = self._ocd_find_member_partner(number)
        member = self.sudo().with_context(active_test=False).search([("partner_id", "=", known.id)], limit=1) \
            if known else self.browse()
        if member.active:
            if member.vendor_id == vendor:
                raise UserError(env._("%s is already in your team.", member.name))
            raise UserError(env._("This number is already in the team of another vendor."))
        if self.sudo().search_count([("vendor_id", "=", vendor.id)]) >= vendor._ocd_team_allowed():
            raise UserError(env._(
                "%s people at most in a team: remove someone first.", vendor._ocd_team_allowed()
            ))
        person = known or Partner.search([("phone", "=", number), ("ocd_is_vendor", "=", False)], limit=1)
        if not person:
            person = Partner.create({
                "name": name,
                "phone": number,
                "lang": vendor.lang,
                "country_id": (place.country_id or vendor.country_id).id,
            })
        elif not person.name or person.name == person.phone:
            # A contact known by its number only (a customer who held a piece): it gets its name
            person.name = name
        values = {"name": name, "vendor_id": vendor.id, "place_id": place.id, "partner_id": person.id}
        if member and member.vendor_id == vendor:
            # Back in the same team: the same person, her history kept
            member.write({**values, "active": True})
        else:
            # New in this team (a past team of another vendor keeps its own history)
            member = self.sudo().create({**values, "company_id": (vendor.company_id or self.env.company).id})
        vendor.message_post(body=env._("%(person)s joins the team, for %(store)s.", person=name, store=place.name))
        member._ocd_send_link()
        return member

    def _ocd_remove(self):
        """Out of the team: no access from now on (her phone asks for the number again)."""
        for member in self.sudo():
            member.active = False
            member.vendor_id.message_post(body=self.env._("%s leaves the team.", member.name))

    def _ocd_move(self, place):
        """She holds another store of the vendor."""
        self.ensure_one()
        place = place.sudo()
        if not place or place.vendor_id != self.vendor_id or not place.active or place.state == "refused":
            raise UserError(self.env._("Choose one of your stores."))
        if place != self.place_id:
            self.sudo().place_id = place
            self.vendor_id.message_post(body=self.env._(
                "%(person)s now holds %(store)s.", person=self.name, store=place.name
            ))

    def _ocd_send_link(self):
        """Send her the link of her space; return whether it left. Sent by
        ocd_live_shop_whatsapp: without WhatsApp, the vendor gives the link."""
        self.ensure_one()
        if self._ocd_link_sent():
            self.sudo().invited_at = fields.Datetime.now()
            return True
        return False

    def action_ocd_send_link(self):
        """Back office: send her the link of her space again."""
        self.ensure_one()
        if self._ocd_send_link():
            message = self.env._("The link was sent on WhatsApp.")
        else:
            message = self.env._("Send her this link: %s", self._ocd_url())
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "success", "sticky": True},
        }

    def _ocd_link_sent(self):
        """Hook: send the message of the link (ocd_live_shop_whatsapp)."""
        return False

    # === HER ACCESS === #

    @api.model
    def _ocd_find_member_partner(self, number):
        """The contact of a person in a team whose number ends like `number` (8 digits at least,
        as for the vendors), active or not."""
        members = self.sudo().with_context(active_test=False).search([])
        return self.env["res.partner"].sudo()._ocd_find_by_phone(number, [("id", "in", members.partner_id.ids)])

    @api.model
    def _ocd_find_by_phone(self, number):
        """The person of a team (active) whose number ends like `number`, for the login pages."""
        members = self.sudo().search([])
        partner = self.env["res.partner"].sudo()._ocd_find_by_phone(number, [("id", "in", members.partner_id.ids)])
        return members.filtered(lambda member: member.partner_id == partner)[:1] if partner else self.browse()

    @api.model
    def _ocd_of_partner(self, partner):
        """The place in a team of `partner` (empty when she is not, or no longer, in a team)."""
        if not partner or partner.ocd_is_vendor or partner.ocd_is_courier:
            return self.browse()
        return self.sudo().search([("partner_id", "=", partner.id)], limit=1)

    def _ocd_paused(self):
        """The team waits: no more OCD Business, the store removed, the vendor gone."""
        self.ensure_one()
        vendor = self.sudo().vendor_id
        return (
            not vendor.active or not vendor.ocd_is_vendor or vendor.ocd_vendor_state == "refused"
            or not vendor._ocd_business() or not self.place_id.active
        )

    def _ocd_visit(self):
        """She opened a page: her last visit (shown to the vendor)."""
        now = fields.Datetime.now()
        for member in self.sudo():
            if not member.last_visit or member.last_visit < now - VISIT_EVERY:
                member.last_visit = now

    def _ocd_url(self):
        """Her personal link: it opens her space on her phone (link mode); otherwise it leads to
        the page of the number."""
        self.ensure_one()
        partner = self.sudo().partner_id
        return f"{partner.get_base_url()}/ocd/mon-magasin/{partner._ocd_get_space_token()}"

    def _ocd_first_name(self):
        self.ensure_one()
        return (self.name or "").split()[0] if self.name else ""

    def _ocd_location(self):
        """Where the pieces of her store are."""
        self.ensure_one()
        return self.sudo().place_id._ocd_location()

    def _ocd_products(self):
        """The products of the vendor whose stock she counts, by name."""
        self.ensure_one()
        return self.env["product.template"].sudo().search(
            [("ocd_vendor_id", "=", self.vendor_id.id), ("type", "=", "consu")], order="name, id"
        )

    # === WHAT HAPPENS IN HER STORE (WhatsApp in ocd_live_shop_whatsapp) === #

    @api.model
    def _ocd_of_place(self, place):
        """The people who hold `place` now (not paused)."""
        members = self.sudo().search([("place_id", "=", place.id)]) if place else self.browse()
        return members.filtered(lambda member: not member._ocd_paused())

    def _ocd_tell_parcel(self, parcel):
        """A parcel to prepare in her store."""

    def _ocd_tell_hold(self, hold):
        """A customer wants to try a piece in her store."""


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_team_ids = fields.One2many(
        comodel_name="ocd.vendor.member", inverse_name="vendor_id", string="Team",
        help="The people who hold the stores of the vendor (OCD Business).",
    )
    ocd_team_max = fields.Integer(
        string="Team At Most",
        help="How many people the team of the vendor may have. 0: the setting of OCD Live.",
    )

    def _ocd_team_allowed(self):
        """How many people the team of the vendor may have: none without OCD Business."""
        self.ensure_one()
        if not self._ocd_business():
            return 0
        company = self.company_id or self.env.company
        return max(self.ocd_team_max or company.ocd_vendor_team_max or 0, 0)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ocd_notify_new_parcel(self):
        """The people who hold the store also learn there is a parcel to prepare there."""
        super()._ocd_notify_new_parcel()
        for parcel in self.sudo():
            prepared_there = parcel.ocd_collect or parcel.ocd_delivery_mode in ("vendor", "pickup")
            if parcel.ocd_vendor_id and parcel.ocd_pickup_place_id and prepared_there:
                for member in self.env["ocd.vendor.member"]._ocd_of_place(parcel.ocd_pickup_place_id):
                    member._ocd_tell_parcel(parcel)


class OcdProductHold(models.Model):
    _inherit = "ocd.product.hold"

    ocd_member_id = fields.Many2one(
        comodel_name="ocd.vendor.member", string="Answered By (Team)", readonly=True, copy=False,
        help="The person of the team of the vendor who answered last, at the store.",
    )

    def _ocd_notify_vendor(self):
        """The people who hold the store also learn a customer wants to try a piece there."""
        super()._ocd_notify_vendor()
        for hold in self.sudo():
            for member in self.env["ocd.vendor.member"]._ocd_of_place(hold.place_id):
                member._ocd_tell_hold(hold)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        """A change of the stock made by a person of the team: the vendor sees who did it."""
        values = super()._get_inventory_move_values(qty, location_id, location_dest_id, package_id, package_dest_id)
        if self.env.context.get("ocd_member_id"):
            values["ocd_member_id"] = self.env.context["ocd_member_id"]
        return values


class StockMove(models.Model):
    _inherit = "stock.move"

    ocd_member_id = fields.Many2one(
        comodel_name="ocd.vendor.member", string="Changed By (Team)", readonly=True, index="btree_not_null",
        help="The person of the team of the vendor who changed the stock.",
    )
