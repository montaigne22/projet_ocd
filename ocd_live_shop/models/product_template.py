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
    ocd_review_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Approved"), ("refused", "Refused")],
        string="Review",
        default="approved",
        tracking=True,
        help="The products added by the vendors from their space are checked by the team "
        "before they appear on the website.",
    )
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
        self.write({"ocd_review_state": "approved"})
        return True

    def action_ocd_refuse(self):
        self.write({"ocd_review_state": "refused", "is_published": False})
        return True

    def action_ocd_show_on_live(self):
        """Show this product on the boutique of the vendor during the live of the context."""
        self.ensure_one()
        booking = self.env["ocd.live.booking"].browse(self.env.context.get("ocd_booking_id")).exists()
        if not booking:
            raise UserError(self.env._("Open the live first."))
        booking._ocd_show_product(self)
        return True

    def _ocd_whatsapp_url(self):
        """Return the WhatsApp link to the vendor, with a message about the product."""
        self.ensure_one()
        digits = re.sub(r"\D", "", self.ocd_vendor_id.phone or "")
        if len(digits) < 8:
            return False
        text = self.env._("Hello, I saw %(product)s on OCD Live.", product=self.name)
        return f"https://wa.me/{digits}?text={url_quote(text)}"
