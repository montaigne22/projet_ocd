from odoo import api, fields, models
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    ocd_next_label = fields.Char(related="stage_id.ocd_next_label")

    def _get_employee_create_vals(self):
        """Override of `hr_recruitment`: a hired live host is ready for the remote lives."""
        vals = super()._get_employee_create_vals()
        if self.job_id == self.env.ref("ocd_live_recruitment.job_live_host", raise_if_not_found=False):
            vals["ocd_is_animatrice"] = True
        return vals

    @api.model
    def _ocd_stages_of(self, job):
        """The steps of `job`: its own steps when it has some, else the steps of every job."""
        Stage = self.env["hr.recruitment.stage"]
        own = Stage.search([("job_ids", "=", job.id)], order="sequence, id") if job else Stage
        return own or Stage.search([("job_ids", "=", False)], order="sequence, id")

    def _ocd_job_stages(self):
        self.ensure_one()
        return self._ocd_stages_of(self.job_id)

    def _compute_stage(self):
        """A new application of a job with its own steps starts at its first step."""
        Stage = self.env["hr.recruitment.stage"]
        own = self.filtered(
            lambda applicant: applicant.job_id and not applicant.stage_id
            and Stage.search_count([("job_ids", "=", applicant.job_id.id)])
        )
        for applicant in own:
            applicant.stage_id = self._ocd_stages_of(applicant.job_id)[:1]
        super(HrApplicant, self - own)._compute_stage()

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """A job with its own steps shows only them, as the steps of the live hosts."""
        job = self.env["hr.job"].browse(self.env.context.get("default_job_id")).exists()
        own = self.env["hr.recruitment.stage"].search([("job_ids", "=", job.id)], order="sequence, id") if job else None
        if own:
            return own
        return super()._read_group_stage_ids(stages, domain)

    def action_ocd_next_stage(self):
        """Move the applicant to the next step of the job; the hired step creates the employee."""
        for applicant in self:
            stages = applicant._ocd_job_stages()
            if applicant.stage_id not in stages:
                raise UserError(self.env._("The step of %s is not a step of the job.", applicant.partner_name))
            index = stages.ids.index(applicant.stage_id.id)
            if index + 1 >= len(stages):
                continue
            applicant.stage_id = stages[index + 1]
            if applicant.stage_id.hired_stage and not applicant.employee_id:
                applicant.create_employee_from_applicant()
        return True

    @api.model
    def ocd_job_summary(self, job_id):
        """Figures of the top of the applications of a job: offer online, positions, hired, refused."""
        job = self.env["hr.job"].browse(job_id).exists()
        if not job:
            return {}
        refused = self.with_context(active_test=False).search_count(
            [("job_id", "=", job.id), ("application_status", "=", "refused")]
        )
        hired = self.search_count([("job_id", "=", job.id), ("stage_id.hired_stage", "=", True)])
        return {
            "title": self.env._("Offer online on the website") if job.website_published
            else self.env._("Offer not published on the website"),
            "online": job.website_published,
            "line": self.env._("No diploma · live in Lome · a video of one minute, by the website or by WhatsApp"),
            "positions": self.env._(
                "%(count)s positions · filled: %(hired)s", count=job.no_of_recruitment, hired=hired
            ),
            "refused": self.env._("Refused: %s", refused),
        }
