from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_evening_alert_minutes = fields.Integer(
        string="Big Event: Told Before", default=15,
        help="Minutes before the start of a big event, to the people who asked « Tell me on WhatsApp ».",
    )
    ocd_evening_registration_days = fields.Integer(
        string="Big Event: Registrations Until", default=3,
        help="Days before a new big event when the registrations of the vendors close.",
    )
    ocd_evening_max_days = fields.Integer(
        string="Big Event: Days At Most", default=14,
        help="The length of a big event at most, in days: its promos last as long.",
    )

    @api.constrains("ocd_evening_max_days")
    def _check_ocd_evening_max_days(self):
        for company in self:
            if not 1 <= company.ocd_evening_max_days <= 60:
                raise ValidationError(self.env._("A big event lasts between 1 and 60 days at most."))
