from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOcdRecruitment(TransactionCase):

    def test_hired_host_is_ready_for_the_lives(self):
        job = self.env.ref("ocd_live_recruitment.job_live_host")
        self.assertTrue(job.website_published)
        applicant = self.env["hr.applicant"].create({
            "partner_name": "Dzifa A.",
            "email_from": "dzifa@example.com",
            "job_id": job.id,
        })
        applicant.create_employee_from_applicant()
        employee = self.env["hr.employee"].search([("name", "=", "Dzifa A.")])
        self.assertTrue(employee.ocd_is_animatrice)

    def test_other_jobs_are_not_hosts(self):
        other = self.env["hr.job"].create({"name": "Accountant"})
        applicant = self.env["hr.applicant"].create({"partner_name": "Kofi", "job_id": other.id})
        applicant.create_employee_from_applicant()
        self.assertFalse(self.env["hr.employee"].search([("name", "=", "Kofi")]).ocd_is_animatrice)

    def test_steps_of_the_live_hosts(self):
        job = self.env.ref("ocd_live_recruitment.job_live_host")
        applicant = self.env["hr.applicant"].create({
            "partner_name": "Akossiwa A.",
            "email_from": "akossiwa@example.com",
            "job_id": job.id,
            "stage_id": self.env.ref("ocd_live_recruitment.stage_host_new").id,
        })
        self.assertTrue(applicant.ocd_next_label)
        applicant.action_ocd_next_stage()
        self.assertEqual(applicant.stage_id, self.env.ref("ocd_live_recruitment.stage_host_call"))
        applicant.action_ocd_next_stage()
        applicant.action_ocd_next_stage()
        applicant.action_ocd_next_stage()
        self.assertTrue(applicant.stage_id.hired_stage)
        self.assertTrue(applicant.employee_id.ocd_is_animatrice)
        summary = self.env["hr.applicant"].ocd_job_summary(job.id)
        self.assertTrue(summary["online"])
