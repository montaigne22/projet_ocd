from datetime import timedelta

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ocd_booking_ids = fields.One2many(
        comodel_name="ocd.live.booking", inverse_name="sale_line_id", string="Lives"
    )
    ocd_credit_ids = fields.One2many(
        comodel_name="ocd.live.credit", inverse_name="sale_line_id", string="Live Credits"
    )
    ocd_pass_ids = fields.One2many(
        comodel_name="ocd.directory.pass", inverse_name="sale_line_id", string="Directory Passes"
    )

    def _ocd_process_confirmed_lines(self):
        # sudo: run from the payment flow, the order itself is already confirmed
        for line in self.sudo():
            kind = line.product_id.ocd_product_kind
            if kind == "live_package" and not line.ocd_credit_ids:
                credit = self.env["ocd.live.credit"].sudo().create(line._ocd_prepare_credit_vals())
                held = line.ocd_booking_ids.filtered(lambda b: b.state == "draft")
                held.write({"credit_id": credit.id})
                held._ocd_confirm()
                if line.ocd_booking_ids and not held:
                    line.order_id.message_post(
                        body=self.env._(
                            "The payment came after the slot was released: the lives of the "
                            "package stay available to place."
                        )
                    )
            elif kind == "directory_pass" and not line.ocd_pass_ids:
                self.env["ocd.directory.pass"].sudo()._ocd_create_from_line(line)
            elif kind == "hour_price":
                # A live of a package placed on an hour that costs more, held until paid
                line.ocd_booking_ids.filtered(lambda b: b.state == "draft")._ocd_confirm()

    def _ocd_prepare_credit_vals(self):
        self.ensure_one()
        product = self.product_id
        validity = product.ocd_validity_days
        today = fields.Date.context_today(self)
        return {
            "partner_id": self.order_id.partner_id.id,
            "company_id": self.order_id.company_id.id,
            "product_id": product.id,
            "sale_line_id": self.id,
            "quantity": product.ocd_live_count * max(int(self.product_uom_qty), 1),
            "date_expiry": today + timedelta(days=validity) if validity else False,
        }
