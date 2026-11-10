from odoo import fields, models


class OcdParcelForce(models.TransientModel):
    _name = "ocd.parcel.force"
    _description = "Validate A Parcel Without The Code"

    picking_id = fields.Many2one(comodel_name="stock.picking", string="Parcel", required=True)
    reason = fields.Text(required=True)
    photo = fields.Binary(string="Photo Of The Handover")

    def action_confirm(self):
        self.ensure_one()
        self.picking_id._ocd_force_deliver(self.reason, self.photo)
        return {"type": "ir.actions.act_window_close"}
