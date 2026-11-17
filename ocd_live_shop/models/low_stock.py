"""Low stock alert (chantier 21, 3.4 of the plan of « My products », design StockBas).

When the confirmation of an order leaves a product (a colour and a size) with the threshold of
pieces or less, but at least one, the vendor is told on WhatsApp: once per passage under the
threshold, as it is counted from the stock free before the order (no state to keep). The
threshold is a setting of OCD Live (2 by default, 0: no alert), changed on the form of a vendor.
« My products » says it too, with a filter."""
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_low_stock_threshold = fields.Integer(
        string="Low Stock Alert",
        default=2,
        help="A WhatsApp to the vendor when a sale leaves this number of pieces or less of a product "
        "(a colour, a size). 0: no alert.",
    )


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_low_stock_threshold = fields.Integer(
        string="Low Stock Alert (Pieces)",
        help="Empty: the setting of OCD Live.",
    )

    def _ocd_low_stock_limit(self):
        """The pieces under which a product of the vendor is low on stock (0: no alert)."""
        self.ensure_one()
        vendor = self.sudo()
        if vendor.ocd_low_stock_threshold:
            return max(vendor.ocd_low_stock_threshold, 0)
        return max((vendor.company_id or self.env.company).ocd_low_stock_threshold, 0)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _ocd_low_stock_notify(self, pieces):
        """Tell the vendor only `pieces` of this variant are left (extended by
        ocd_live_shop_whatsapp)."""


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _ocd_low_stock_before(self):
        """{variant: (pieces free now, pieces of these orders)} for the products of vendors whose
        stock limits the sales, before the orders take them."""
        ordered = {}
        for line in self.filtered(lambda order: order.state in ("draft", "sent")).order_line:
            product = line.product_id
            if (
                line.display_type or line.is_delivery or not product or not product.is_storable
                or product.allow_out_of_stock_order or not product.sudo().product_tmpl_id.ocd_vendor_id
            ):
                continue
            ordered[product] = ordered.get(product, 0) + line.product_uom_qty
        if not ordered:
            return {}
        variants = self.env["product.product"].browse([product.id for product in ordered]).sudo()
        free = variants._ocd_free_qties()
        return {product: (free[product.id], qty) for product, qty in ordered.items()}

    def _ocd_low_stock_check(self, before):
        """Tell the vendors whose products these orders took under the threshold."""
        for product, (free, qty) in before.items():
            limit = product.sudo().product_tmpl_id.ocd_vendor_id._ocd_low_stock_limit()
            left = int(free - qty)
            if limit and free > limit and 1 <= left <= limit:
                product._ocd_low_stock_notify(left)

    def action_confirm(self):
        before = self._ocd_low_stock_before()
        result = super().action_confirm()
        self._ocd_low_stock_check(before)
        return result
