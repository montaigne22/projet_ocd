from odoo import fields, models


class HrRecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    ocd_next_label = fields.Char(
        string="Button To The Next Step",
        translate=True,
        help="Shown on the cards of the applicants of this step, e.g. Call, Invite to the trial.",
    )
