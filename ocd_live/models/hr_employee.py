from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ocd_is_animatrice = fields.Boolean(
        string="Live Host",
        help="Accompanies the remote lives from the studio in Lome.",
    )
    ocd_booking_ids = fields.One2many(
        comodel_name="ocd.live.booking", inverse_name="animatrice_id", string="Hosted Lives"
    )
