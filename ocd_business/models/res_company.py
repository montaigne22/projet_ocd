from odoo import fields, models


class ResCompany(models.Model):
    """The rules of OCD Business (chantier 12, design OcdBusiness)."""

    _inherit = "res.company"

    ocd_business_launch_date = fields.Date(
        string="Launch Of OCD Business",
        help="This day, the features offered to all stop; the vendors who use them receive the months of the "
             "settings first, once.",
    )
    ocd_business_launch_months = fields.Integer(
        string="Months Offered At The Launch", default=2,
        help="To the vendors who use the features (several stores, a team) on the day of the launch.",
    )
    ocd_business_launch_done = fields.Boolean(string="Launch Of OCD Business Done", readonly=True, copy=False)
    ocd_business_reminder_days = fields.Integer(
        string="OCD Business: First Reminder (Days Before)", default=7,
        help="Then the day before; one message per date of end, never after a renewal.",
    )
    ocd_business_grace_days = fields.Integer(
        string="OCD Business: Grace For A Payment Checked (Days)", default=3,
        help="After « I paid » for a Mobile Money checked by the team: the features stay this long after the end, "
             "the time of the check.",
    )

    def _ocd_business_users(self):
        """The vendors who use the features of OCD Business today: several stores shown, or a
        team."""
        self.ensure_one()
        Place = self.env["ocd.vendor.place"].sudo()
        places = Place._read_group([("state", "=", "approved"), ("vendor_id.ocd_is_vendor", "=", True)],
                                   ["vendor_id"], ["__count"])
        vendors = self.env["res.partner"].sudo().browse([vendor.id for vendor, count in places if count >= 2])
        members = self.env["ocd.vendor.member"].sudo().search([("active", "=", True)])
        return (vendors | members.vendor_id).filtered(lambda vendor: vendor.ocd_is_vendor)

    def _ocd_business_launch(self):
        """The day of the launch (once): the vendors who use the features receive the months of
        the settings first, are told, then the features offered to all stop. Nobody loses their
        features at midnight."""
        Period = self.env["ocd.business.period"].sudo()
        for company in self.sudo():
            if not company.ocd_business_offered_all or company.ocd_business_launch_done \
                    or not company.ocd_business_launch_date \
                    or company._ocd_local_today() < company.ocd_business_launch_date:
                continue
            days = max(company.ocd_business_launch_months, 0) * 30
            if days:
                for vendor in company._ocd_business_users():
                    if Period.search_count([("vendor_id", "=", vendor.id), ("kind", "=", "launch")]):
                        continue
                    Period._ocd_add(vendor, days, "launch", note=self.env._("Offered at the launch of OCD Business"))
                    vendor._ocd_business_tell("launch")
            company.write({"ocd_business_offered_all": False, "ocd_business_launch_done": True})
