from datetime import timedelta

from odoo import fields, models


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    def _ocd_runs_business_paid(self):
        periods = self.env["ocd.business.period"].sudo().search([
            ("kind", "=", "paid"), ("create_date", ">=", fields.Datetime.now() - timedelta(days=7))])
        return self._ocd_runs_of(periods, "create_date", lambda period: period.vendor_id.name)
