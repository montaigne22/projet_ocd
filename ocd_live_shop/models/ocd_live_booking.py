from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    current_product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Shown Now", copy=False
    )
    moment_ids = fields.One2many(
        comodel_name="ocd.live.moment", inverse_name="booking_id", string="Moments Of The Replay"
    )
    ocd_visit_count = fields.Integer(
        string="Boutique Visits",
        copy=False,
        readonly=True,
        help="Visits of the boutique of the vendor during the live, one per browser.",
    )
    vendor_product_ids = fields.Many2many(
        comodel_name="product.template",
        string="Products Of The Vendor",
        compute="_compute_vendor_product_ids",
    )

    @api.depends("partner_id")
    def _compute_vendor_product_ids(self):
        products = self.env["product.template"].search([
            ("ocd_vendor_id", "in", self.partner_id.ids),
            ("sale_ok", "=", True),
            ("ocd_review_state", "=", "approved"),
        ])
        by_vendor = products.grouped("ocd_vendor_id")
        for booking in self:
            booking.vendor_product_ids = by_vendor.get(booking.partner_id, self.env["product.template"])

    def _ocd_show_product(self, product):
        """Show `product` on the boutique of the vendor and note the moment for the replay."""
        self.ensure_one()
        if self.state not in ("confirmed", "done"):
            raise UserError(self.env._("The live is not confirmed."))
        if product.ocd_vendor_id != self.partner_id:
            raise UserError(self.env._("This product does not belong to the vendor of the live."))
        offset = max(int((fields.Datetime.now() - self.start_datetime).total_seconds()), 0)
        self.current_product_tmpl_id = product
        self.env["ocd.live.moment"].create({
            "booking_id": self.id,
            "product_tmpl_id": product.id,
            "offset_seconds": offset,
        })

    def _ocd_count_visit(self):
        """Count a visit of the boutique during the live, in one query (many visitors at once)."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET ocd_visit_count = COALESCE(ocd_visit_count, 0) + 1 WHERE id = %s",
            [self.id],
        )
        self.invalidate_recordset(["ocd_visit_count"])
