from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class OcdLiveCredit(models.Model):
    """Lives of a paid package that the vendor places in the calendar."""

    _name = "ocd.live.credit"
    _description = "Live Credit"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Package",
        required=True,
        domain=[("ocd_product_kind", "=", "live_package")],
        check_company=True,
    )
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Order Line",
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    sale_order_id = fields.Many2one(related="sale_line_id.order_id", string="Order")
    quantity = fields.Integer(string="Lives", required=True, default=1, tracking=True)
    booking_ids = fields.One2many(
        comodel_name="ocd.live.booking", inverse_name="credit_id", string="Placed Lives"
    )
    used = fields.Integer(string="Placed", compute="_compute_usage", store=True)
    remaining = fields.Integer(string="To Place", compute="_compute_usage", store=True)
    date_expiry = fields.Date(string="To Place Before", tracking=True)
    state = fields.Selection(
        selection=[("active", "Active"), ("used", "All placed"), ("expired", "Expired")],
        compute="_compute_state",
        store=True,
        index=True,
    )

    _check_quantity = models.Constraint(
        "CHECK (quantity > 0)",
        "A credit contains at least one live.",
    )

    @api.depends("quantity", "booking_ids.state")
    def _compute_usage(self):
        for credit in self:
            credit.used = len(credit.booking_ids.filtered(lambda b: b.state != "cancelled"))
            credit.remaining = max(credit.quantity - credit.used, 0)

    @api.depends("remaining", "date_expiry")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for credit in self:
            if credit.date_expiry and credit.date_expiry < today:
                credit.state = "expired"
            elif not credit.remaining:
                credit.state = "used"
            else:
                credit.state = "active"

    @api.constrains("quantity", "used")
    def _check_usage(self):
        for credit in self:
            if credit.used > credit.quantity:
                raise ValidationError(
                    self.env._("The package %s has no live left to place.", credit.product_id.display_name)
                )

    @api.depends("product_id", "remaining")
    def _compute_display_name(self):
        for credit in self:
            credit.display_name = self.env._(
                "%(package)s: %(count)s to place",
                package=credit.product_id.name or "",
                count=credit.remaining,
            )

    def _ocd_check_usable(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.date_expiry and self.date_expiry < today:
            raise UserError(self.env._("This package expired on %s.", self.date_expiry))
        if self.remaining <= 0:
            raise UserError(self.env._("All the lives of this package are already placed."))

    def _ocd_hour_price_order(self, start, mode, percent):
        """Return the quotation of the difference to pay for a live of this package placed on
        an hour that costs `percent` more, in the currency of the package."""
        self.ensure_one()
        product = self.product_id
        line = self.sale_line_id
        if line:
            per_live = line.price_unit / max(product.ocd_live_count, 1)
            pricelist = line.order_id.pricelist_id
        else:
            pricelist = self.partner_id.with_company(self.company_id).property_product_pricelist
            price = pricelist._get_product_price(product, 1.0) if pricelist else product.list_price
            per_live = price / max(product.ocd_live_count, 1)
        # sudo: the vendor places the live from the space, identified by the personal link
        order = self.env["sale.order"].sudo().create({
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "pricelist_id": pricelist.id or False,
            "require_signature": False,
            "prepayment_percent": 1.0,
        })
        order._ocd_add_hour_price_line(start, mode, percent, per_live)
        return order

    @api.model
    def _cron_expire(self):
        """Mark the credits whose date passed as expired."""
        self.search(
            [("state", "=", "active"), ("date_expiry", "<", fields.Date.context_today(self))]
        )._compute_state()
