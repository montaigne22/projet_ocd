from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ocd_booking_ids = fields.One2many(
        comodel_name="ocd.live.booking", inverse_name="sale_order_id", string="Lives"
    )
    ocd_booking_count = fields.Integer(string="Lives Count", compute="_compute_ocd_booking_count")
    ocd_pass_ids = fields.One2many(
        comodel_name="ocd.directory.pass", inverse_name="sale_order_id", string="Directory Passes"
    )

    @api.depends("ocd_booking_ids")
    def _compute_ocd_booking_count(self):
        for order in self:
            order.ocd_booking_count = len(order.ocd_booking_ids)

    def _action_confirm(self):
        """Override of `sale` to turn the paid packages into credits and confirmed lives, and
        the paid passes into directory passes. The payment provider confirms the order: the
        lives are never confirmed by the browser."""
        result = super()._action_confirm()
        self.order_line._ocd_process_confirmed_lines()
        return result

    def _action_cancel(self):
        result = super()._action_cancel()
        self.ocd_booking_ids.filtered(lambda b: b.state == "draft").action_cancel()
        return result

    def action_ocd_view_bookings(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("ocd_live.ocd_live_booking_action")
        action["domain"] = [("sale_order_id", "=", self.id)]
        return action
