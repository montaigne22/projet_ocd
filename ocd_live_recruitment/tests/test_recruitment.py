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
