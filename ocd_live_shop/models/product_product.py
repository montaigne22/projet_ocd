from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _is_add_to_cart_allowed(self):
        """Override of `website_sale`: the products of a vendor in direct contact are not sold
        on the website (OCD Live does not take the money), the customer writes to the vendor."""
        allowed = super()._is_add_to_cart_allowed()
        vendor = self.sudo().product_tmpl_id.ocd_vendor_id
        return allowed and not (vendor and vendor.ocd_sale_mode == "direct")
