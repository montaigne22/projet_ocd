import re
from urllib.parse import quote as url_quote

from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ocd_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="OCD Vendor",
        index="btree_not_null",
        domain=[("ocd_is_vendor", "=", True)],
        tracking=True,
    )
    ocd_sale_mode = fields.Selection(related="ocd_vendor_id.ocd_sale_mode", string="Sale Mode")
    ocd_category_id = fields.Many2one(
        related="ocd_vendor_id.ocd_category_id",
        store=True,
        index="btree_not_null",
        string="Category Of The Vendor",
        help="Used by the shop to filter the products by category of the vendors.",
    )
    ocd_review_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Approved"), ("refused", "Refused")],
        string="Review",
        default="approved",
        tracking=True,
        help="The products added by the vendors from their space are checked by the team "
        "before they appear on the website.",
    )
    ocd_review_date = fields.Datetime(string="Checked At", copy=False, readonly=True)
    ocd_moment_ids = fields.One2many(
        comodel_name="ocd.live.moment", inverse_name="product_tmpl_id", string="Live Moments"
    )
    ocd_wa_clicks = fields.Integer(
        string="WhatsApp Contacts",
        copy=False,
        readonly=True,
        help="Number of visitors who wrote to the vendor on WhatsApp from the boutique.",
    )

    @api.constrains("is_published", "ocd_review_state")
    def _check_ocd_review_before_publication(self):
        for product in self:
            if product.is_published and product.ocd_vendor_id and product.ocd_review_state != "approved":
                raise UserError(
                    self.env._("The product %s must be approved before it is published.", product.name)
                )

    def action_ocd_approve(self):
        self.write({"ocd_review_state": "approved", "ocd_review_date": fields.Datetime.now()})
        return True

    def action_ocd_refuse(self, reason=None):
        self.write({"ocd_review_state": "refused", "is_published": False, "ocd_review_date": fields.Datetime.now()})
        if reason:
            for product in self:
                product.message_post(body=self.env._("Product refused: %s", reason.name))
        return True

    def action_ocd_show_on_live(self):
        """Show this product on the boutique of the vendor during the live of the context."""
        self.ensure_one()
        booking = self.env["ocd.live.booking"].browse(self.env.context.get("ocd_booking_id")).exists()
        if not booking:
            raise UserError(self.env._("Open the live first."))
        booking._ocd_show_product(self)
        return True

    def _ocd_whatsapp_url(self, values=None, link=None):
        """Return the WhatsApp link to the vendor, with a message about the product: the
        values chosen (colour, size...) and the link of the product, when given."""
        self.ensure_one()
        digits = re.sub(r"\D", "", self.ocd_vendor_id.phone or "")
        if len(digits) < 8:
            return False
        text = self.env._("Hello, I saw %(product)s on OCD Live.", product=self.name)
        if values:
            text = f"{text} {self.env._('My choice: %s.', ', '.join(values))}"
        if link:
            text = f"{text} {link}"
        return f"https://wa.me/{digits}?text={url_quote(text)}"

    def _ocd_set_stock(self, quantity):
        """Set the quantity in stock of a product without variants, as an inventory adjustment
        of the main warehouse (traced in the stock moves). Used by the vendors from their
        space."""
        self.ensure_one()
        variant = self.product_variant_ids[:1]
        if not variant or len(self.product_variant_ids) != 1:
            raise UserError(self.env._("Change the stock of the product %s from the back office.", self.name))
        company = self.company_id or self.env.company
        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            return False
        Quant = self.env["stock.quant"].sudo().with_context(inventory_mode=True)
        quant = Quant.search([("product_id", "=", variant.id), ("location_id", "=", warehouse.lot_stock_id.id)], limit=1)
        if not quant:
            quant = Quant.create({"product_id": variant.id, "location_id": warehouse.lot_stock_id.id})
        quant.inventory_quantity = quantity
        quant.action_apply_inventory()
        return True
