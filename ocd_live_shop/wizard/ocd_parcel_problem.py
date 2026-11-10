from odoo import fields, models

from ..models.stock_picking import PROBLEM_REASONS


class OcdParcelProblem(models.TransientModel):
    _name = "ocd.parcel.problem"
    _description = "Report A Delivery Problem"

    picking_id = fields.Many2one(comodel_name="stock.picking", string="Parcel", required=True)
    reason = fields.Selection(selection=PROBLEM_REASONS, required=True, default="unreachable")
    note = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        self.picking_id._ocd_report_problem(self.reason, self.note)
        return {"type": "ir.actions.act_window_close"}
