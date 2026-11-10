from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ocd_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="OCD Vendor",
        compute="_compute_ocd_vendor",
        store=True,
        readonly=False,
        index="btree_not_null",
    )
    ocd_commission_rate = fields.Float(
        string="Commission (%)",
        compute="_compute_ocd_vendor",
        store=True,
        readonly=False,
        help="Commission of OCD when the line was sold, kept even if the rate changes later.",
    )
    ocd_vendor_share = fields.Monetary(
        string="Share Of The Vendor",
        compute="_compute_ocd_vendor_share",
        currency_field="currency_id",
    )

    @api.depends("product_id")
    def _compute_ocd_vendor(self):
        for line in self:
            vendor = line.product_id.product_tmpl_id.ocd_vendor_id
            line.ocd_vendor_id = vendor if vendor.ocd_sale_mode == "ocd" else False
            line.ocd_commission_rate = vendor.ocd_commission_rate if line.ocd_vendor_id else 0.0

    @api.depends("price_total", "ocd_commission_rate", "ocd_vendor_id")
    def _compute_ocd_vendor_share(self):
        for line in self:
            if line.ocd_vendor_id:
                line.ocd_vendor_share = line.currency_id.round(
                    line.price_total * (1 - line.ocd_commission_rate / 100.0)
                )
            else:
                line.ocd_vendor_share = 0.0
