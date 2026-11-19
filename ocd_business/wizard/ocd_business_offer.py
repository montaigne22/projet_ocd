from odoo import fields, models
from odoo.exceptions import AccessError, UserError


class OcdBusinessOffer(models.TransientModel):
    """« Offer days »: the team gives days of OCD Business with a reason, kept in the history; it
    never types a date of end."""

    _name = "ocd.business.offer"
    _description = "Offer Days Of OCD Business"

    vendor_id = fields.Many2one(comodel_name="res.partner", string="Vendor", required=True)
    days = fields.Integer(required=True, default=30)
    note = fields.Char(string="Why", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of OCD Live offers days of OCD Business."))
        if self.days < 1 or self.days > 400:
            raise UserError(self.env._("Offer between 1 and 400 days."))
        period = self.env["ocd.business.period"]._ocd_add(
            self.vendor_id, self.days, "offered", note=self.note, user=self.env.user)
        self.vendor_id.message_post(body=self.env._(
            "%(days)s days of OCD Business offered by %(user)s: %(note)s",
            days=self.days, user=self.env.user.name, note=self.note))
        return {"type": "ir.actions.act_window_close"} if period else True
