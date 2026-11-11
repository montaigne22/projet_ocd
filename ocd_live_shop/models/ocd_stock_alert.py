import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdStockAlert(models.Model):
    """A customer who wants a WhatsApp message when a product sold out in a colour or a size is
    back ("Tell me when it is back")."""

    _name = "ocd.stock.alert"
    _description = "Alert When A Product Is Back"
    _order = "id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact", required=True, index=True, ondelete="cascade"
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    state = fields.Selection(
        selection=[("waiting", "Waiting"), ("sent", "Sent"), ("cancelled", "Cancelled")],
        required=True,
        default="waiting",
        index=True,
    )
    sent_at = fields.Datetime(readonly=True)

    _unique_waiting = models.UniqueIndex(
        "(partner_id, product_id) WHERE state = 'waiting'",
        "This contact is already told when this product is back.",
    )

    @api.model
    def _ocd_register(self, product, phone=None, partner=None):
        """Tell the contact of `phone` (or `partner`) when `product` (a variant) is back."""
        Partner = self.env["res.partner"].sudo()
        if not partner:
            if len(re.sub(r"\D", "", phone or "")) < 8:
                raise UserError(self.env._("Type your WhatsApp number."))
            partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
            if not partner:
                partner = Partner.create({"name": phone, "phone": phone})
        # sudo: public page, the contact only gives a number
        existing = self.sudo().search(
            [("partner_id", "=", partner.id), ("product_id", "=", product.id), ("state", "=", "waiting")], limit=1
        )
        return existing or self.sudo().create({"partner_id": partner.id, "product_id": product.id})

    @api.model
    def _ocd_available(self, product):
        """Whether `product` can be ordered again on the website."""
        template = product.product_tmpl_id
        if not (product.active and template.sale_ok and template.is_published):
            return False
        if not product.is_storable or product.allow_out_of_stock_order:
            return True
        product = product.sudo()
        product.invalidate_recordset(["qty_available", "free_qty"])  # the stock may have just come back
        website = self.env["website"].sudo().search([("company_id", "in", (product.company_id.id or self.env.company.id, False))], limit=1)
        quantity = website._get_product_available_qty(product) if website else product.free_qty
        return quantity > 0

    @api.model
    def _ocd_send_back(self, products=None):
        """Tell the contacts whose product is back (all of them, or the ones of `products`). A
        product removed from the shop ends its alerts."""
        domain = [("state", "=", "waiting")]
        if products is not None:
            domain.append(("product_id", "in", products.ids))
        waiting = self.sudo().search(domain)
        now = fields.Datetime.now()
        gone = waiting.filtered(lambda alert: not alert.product_id.active or not alert.product_id.product_tmpl_id.active)
        gone.write({"state": "cancelled"})
        for product, alerts in (waiting - gone).grouped("product_id").items():
            if not self._ocd_available(product):
                continue
            for alert in alerts:
                alert._ocd_send_product_back()
            alerts.write({"state": "sent", "sent_at": now})

    def _ocd_product_path(self):
        """The page of the product with its colour and its size (without the first "/")."""
        self.ensure_one()
        product = self.product_id
        path = (product.product_tmpl_id.website_url or f"/shop/{product.product_tmpl_id.id}").lstrip("/")
        values = ",".join(str(value) for value in sorted(product.product_template_attribute_value_ids.ids))
        return f"{path}?v={values}" if values else path

    def _ocd_variant_label(self):
        """What came back: "Bleu, L"."""
        self.ensure_one()
        return ", ".join(self.product_id.product_template_attribute_value_ids.mapped("name")) or self.product_id.name

    def _ocd_send_product_back(self):
        """Send the news that the product is back. Extended by ocd_live_shop_whatsapp."""
        return False

    @api.model
    def _cron_send_back(self):
        self._ocd_send_back()
