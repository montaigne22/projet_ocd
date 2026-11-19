from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

from odoo.addons.ocd_live.tools import day_text

from .res_company import PARTS


class OcdExpressPickup(models.Model):
    """A passage of a courier at a sender, for all their parcels of a part of the day: free
    from the number of parcels of the settings, paid below; two passages missed in a row are
    paid."""

    _name = "ocd.express.pickup"
    _description = "OCD Express Pick-Up"
    _inherit = ["mail.thread"]
    _order = "date desc, part, id desc"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name")
    sender_id = fields.Many2one(comodel_name="res.partner", string="Sender", required=True, index=True)
    courier_id = fields.Many2one(
        comodel_name="res.partner", string="Courier", index="btree_not_null", tracking=True,
        domain=[("ocd_is_courier", "=", True)],
    )
    company_id = fields.Many2one(comodel_name="res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    date = fields.Date(required=True, index=True)
    part = fields.Selection(selection=PARTS, string="Part Of The Day", required=True)
    state = fields.Selection(
        selection=[("planned", "Planned"), ("done", "Done"), ("missed", "Sender absent"), ("cancelled", "Cancelled")],
        required=True, default="planned", tracking=True, index=True,
    )
    parcel_ids = fields.One2many(comodel_name="stock.picking", inverse_name="ocd_express_pickup_id", string="Parcels")
    parcel_count = fields.Integer(string="Number Of Parcels", compute="_compute_parcel_count")
    taken_count = fields.Integer(string="Parcels Taken", readonly=True)
    done_at = fields.Datetime(string="Done At", readonly=True)
    photo = fields.Binary(string="Photo Of The Parcels Closed", attachment=True)
    fee = fields.Monetary(string="Price Of The Pick-Up", readonly=True)
    note = fields.Char()

    @api.depends("sender_id.name", "date", "part")
    @api.depends_context("lang")
    def _compute_name(self):
        parts = dict(self._fields["part"]._description_selection(self.env))
        for pickup in self:
            pickup.name = " · ".join(part for part in (
                pickup.sender_id.name, day_text(self.env, pickup.date, "EEE d MMM") if pickup.date else "",
                parts.get(pickup.part, ""),
            ) if part)

    @api.depends("parcel_ids")
    def _compute_parcel_count(self):
        for pickup in self:
            pickup.parcel_count = len(pickup.parcel_ids)

    @api.model
    def _ocd_money(self, amount, currency=None):
        return format_amount(self.env, amount, currency or self.env.company.currency_id)

    @api.model
    def _ocd_for(self, sender, day, part):
        """The passage of `day` and `part` at `sender`, made when needed with a courier of their
        district."""
        pickup = self.sudo().search([
            ("sender_id", "=", sender.id), ("date", "=", day), ("part", "=", part), ("state", "=", "planned"),
        ], limit=1)
        if not pickup:
            courier = self.env["res.partner"].sudo()._ocd_find_courier(sender.district_id)
            pickup = self.sudo().create({"sender_id": sender.id, "date": day, "part": part, "courier_id": courier.id})
        return pickup

    def write(self, vals):
        result = super().write(vals)
        if "courier_id" in vals:
            # The dispatch gives the passage to another courier: they take and deliver its parcels
            for pickup in self.filtered(lambda p: p.state == "planned"):
                pickup.parcel_ids.filtered(lambda p: p.ocd_stage in ("to_prepare", "ready")).sudo().write(
                    {"ocd_courier_id": pickup.courier_id.id})
        return result

    def _ocd_done(self, taken, not_taken=None, photo=None):
        """The courier took the parcels `taken` (the others not, {parcel: reason}). Below the
        number of the settings, the pick-up is paid by the sender."""
        self.ensure_one()
        if self.state != "planned":
            raise UserError(self.env._("This pick-up is already over."))
        not_taken = not_taken or {}
        open_parcels = self.parcel_ids.filtered(lambda p: p.ocd_stage == "ready")
        taken = taken & open_parcels
        if not taken:
            raise UserError(self.env._("Tick the parcels you took, or « The sender is absent »."))
        company = self.company_id
        taken.action_ocd_pick_up()
        for parcel in open_parcels - taken:
            parcel.sudo().ocd_express_not_taken = not_taken.get(parcel) or self.env._("Not given to the courier")
            parcel.message_post(body=self.env._("Not taken at the pick-up: %s", parcel.ocd_express_not_taken))
            parcel._ocd_express_replan()
            parcel._ocd_express_notify("not_taken")
        fee = 0.0
        # The small pick-up is free with OCD Business
        if len(taken) < company.ocd_express_pickup_free_from and company.ocd_express_pickup_fee \
                and not self.sender_id._ocd_business_formula():
            fee = company.ocd_express_pickup_fee
            self.env["stock.picking"]._ocd_express_move(self.sender_id, "in_refund", "pickup", [(
                "ocd_express.product_express_pickup",
                self.env._("Pick-up of %(count)s parcels on %(day)s", count=len(taken), day=self.date), fee,
            )], parcel=taken.sorted("id")[:1])
        self.sudo().write({
            "state": "done", "done_at": fields.Datetime.now(), "taken_count": len(taken), "fee": fee,
            "photo": photo or self.photo,
        })
        self.sender_id.sudo().ocd_express_place_checked = True
        self._ocd_notify_done(taken)
        return True

    def _ocd_missed(self, note=None):
        """The sender was not there: the parcels wait for the next passage. From the second
        passage missed in a row, it is paid."""
        self.ensure_one()
        if self.state != "planned":
            raise UserError(self.env._("This pick-up is already over."))
        company = self.company_id
        self.sudo().write({"state": "missed", "note": note or False})
        previous = self.sudo().search([
            ("sender_id", "=", self.sender_id.id), ("state", "in", ("done", "missed")), ("id", "!=", self.id),
        ], order="date desc, id desc", limit=1)
        parcels = self.parcel_ids.filtered(lambda p: p.ocd_stage == "ready")
        if previous.state == "missed" and company.ocd_express_pickup_fee and parcels:
            self.sudo().fee = company.ocd_express_pickup_fee
            self.env["stock.picking"]._ocd_express_move(self.sender_id, "in_refund", "pickup", [(
                "ocd_express.product_express_pickup",
                self.env._("Second pick-up missed in a row on %s", self.date), self.fee,
            )], parcel=parcels.sorted("id")[:1])
        self.message_post(body=self.env._("The sender was not there: %s", note or "-"))
        parcels._ocd_express_replan()
        parcels[:1]._ocd_express_notify("pickup_missed")
        return True

    def _ocd_notify_done(self, taken):
        """Tell the sender which parcels the courier took (extended by ocd_express_whatsapp)."""
