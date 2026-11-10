from odoo import fields, models


class OcdParcelCode(models.TransientModel):
    _name = "ocd.parcel.code"
    _description = "Type The Code Of The Customer"

    picking_id = fields.Many2one(comodel_name="stock.picking", string="Parcel", required=True)
    code = fields.Char(required=True, size=8)

    def action_confirm(self):
        self.ensure_one()
        delivered, attempts_left = self.picking_id._ocd_check_code(self.code)
        if delivered:
            return {"type": "ir.actions.act_window_close"}
        if attempts_left:
            message = self.env._("Wrong code. Attempts left: %s.", attempts_left)
        else:
            message = self.env._("Wrong code. The parcel is locked: the team was alerted.")
        # The wrong attempt is already saved: show the message without rolling it back
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "danger", "sticky": False},
        }
