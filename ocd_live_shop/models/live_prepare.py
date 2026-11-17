"""Prepare the next live (chantier 21, 3.2 of the plan of « My products », design PreparerLive).

The vendor ticks the products they are going to show and puts them in order, with a word for the
host if they want: the control room shows these products first, numbered in this order, then the
others of the vendor. Nothing prepared: the control room shows all their products, as before. No
numbers of products for the customers nor page « I take it » (left aside on 14 November)."""
from odoo import fields, models
from odoo.exceptions import UserError

NOTE_MAX = 200


class OcdLivePrepared(models.Model):
    _name = "ocd.live.prepared"
    _description = "Product Prepared For A Live"
    _order = "booking_id, sequence, id"

    booking_id = fields.Many2one(
        comodel_name="ocd.live.booking", string="Live", required=True, index=True, ondelete="cascade"
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Product", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)

    _unique_product = models.UniqueIndex("(booking_id, product_tmpl_id)", "A product is prepared once per live.")


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    ocd_prepared_ids = fields.One2many(
        comodel_name="ocd.live.prepared", inverse_name="booking_id", string="Products Prepared By The Vendor",
        copy=False,
    )
    ocd_host_note = fields.Char(
        string="Word For The Host", copy=False, help="Written by the vendor when they prepare the live."
    )
    ocd_prepared_at = fields.Datetime(string="Prepared At", copy=False, readonly=True)

    def _ocd_can_prepare(self):
        """Whether the vendor may still prepare this live: held or confirmed, not over."""
        self.ensure_one()
        return self.state in ("draft", "confirmed") and self.end_datetime > fields.Datetime.now()

    def _ocd_preparable_products(self):
        """The products the vendor may show: theirs, checked, not taken off sale, in the order
        of their boutique."""
        self.ensure_one()
        return self.env["product.template"]._ocd_vendor_products(self.partner_id).filtered(
            lambda product: product.sale_ok and product.ocd_review_state == "approved" and not product.ocd_vendor_retired
        )

    def _ocd_prepared_products(self):
        """The products prepared, in the order of the vendor (the ones no longer on sale left
        aside)."""
        self.ensure_one()
        products = self.sudo().ocd_prepared_ids.sorted(lambda line: (line.sequence, line.id)).product_tmpl_id
        return products.filtered(
            lambda product: product.sale_ok and product.ocd_review_state == "approved" and not product.ocd_vendor_retired
        )

    def _ocd_prepare(self, products, note=False):
        """Keep `products` (in this order) for the live, and the word for the host."""
        self.ensure_one()
        if not self._ocd_can_prepare():
            raise UserError(self.env._("This live is over: prepare your next one."))
        allowed = self._ocd_preparable_products()
        unknown = products - allowed
        if unknown:
            raise UserError(self.env._("%s cannot be shown in your live.", unknown[0].name))
        booking = self.sudo()
        booking.ocd_prepared_ids.unlink()
        self.env["ocd.live.prepared"].sudo().create([
            {"booking_id": booking.id, "product_tmpl_id": product.id, "sequence": index}
            for index, product in enumerate(products)
        ])
        booking.write({
            "ocd_host_note": (note or "").strip()[:NOTE_MAX] or False,
            "ocd_prepared_at": fields.Datetime.now(),
        })
        return True
