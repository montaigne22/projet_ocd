from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_evening_alert_minutes = fields.Integer(
        string="Big Evening: Told Before", default=15,
        help="Minutes before the start of a big evening, to the people who asked « Tell me on WhatsApp ».",
    )
    ocd_evening_registration_days = fields.Integer(
        string="Big Evening: Registrations Until", default=3,
        help="Days before a new big evening when the registrations of the vendors close.",
    )
