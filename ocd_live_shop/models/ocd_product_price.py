from odoo import api, fields, models


class OcdProductPrice(models.Model):
    """The prices of a product of a vendor, one line per change (2.1 of the plan of « My
    products »): the vendor changes the price without a check, the team sees each change, and
    the big gaps the vendor confirmed."""

    _name = "ocd.product.price"
    _description = "Price Of A Product Of A Vendor"
    _order = "create_date desc, id desc"
    _rec_name = "product_tmpl_id"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Product", required=True, index=True, ondelete="cascade"
    )
    currency_id = fields.Many2one(related="product_tmpl_id.currency_id")
    price = fields.Monetary(string="Price", currency_field="currency_id", readonly=True)
    previous_price = fields.Monetary(string="Before", currency_field="currency_id", readonly=True)
    gap = fields.Integer(
        string="Change (%)",
        readonly=True,
        help="How much the price changed, in percent of the price before (negative: lower).",
    )
    source = fields.Selection(
        selection=[("creation", "Creation"), ("vendor", "Vendor"), ("team", "Team")],
        string="By",
        required=True,
        default="team",
        readonly=True,
    )
    confirmed = fields.Boolean(
        string="Confirmed By The Vendor",
        readonly=True,
        help="A big gap the vendor confirmed (« You go from 15,000 to 1,500, is that right? »).",
    )
    big_gap = fields.Boolean(
        string="Big Gap",
        compute="_compute_big_gap",
        help="A change bigger than the gap the vendors confirm (setting).",
    )

    @api.depends("gap")
    def _compute_big_gap(self):
        for line in self:
            limit = (line.product_tmpl_id.company_id or self.env.company).ocd_price_gap_confirm
            line.big_gap = bool(limit) and abs(line.gap) > limit

    @api.model
    def _ocd_gap(self, previous, price):
        """The change from `previous` to `price`, in percent (0 when there was no price)."""
        if not previous:
            return 0
        return round((price - previous) * 100 / previous)
