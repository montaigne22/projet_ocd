from odoo import models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    def _get_employee_create_vals(self):
        """Override of `hr_recruitment`: a hired live host is ready for the remote lives."""
        vals = super()._get_employee_create_vals()
        if self.job_id == self.env.ref("ocd_live_recruitment.job_live_host", raise_if_not_found=False):
            vals["ocd_is_animatrice"] = True
        return vals
