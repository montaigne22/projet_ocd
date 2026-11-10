from datetime import datetime, time, timedelta

from odoo import api, fields, models


class OcdDirectoryWindow(models.Model):
    """Hours of the day when the team checks the live links of the directory."""

    _name = "ocd.directory.window"
    _description = "Directory Checking Window"
    _order = "start_hour, id"

    name = fields.Char(required=True, translate=True)
    start_hour = fields.Float(string="From", required=True)
    end_hour = fields.Float(string="To", required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name="res.company", index=True)

    _check_hours = models.Constraint(
        "CHECK (start_hour >= 0 AND end_hour <= 24 AND start_hour < end_hour)",
        "A window starts and ends on the same day, and ends after it starts.",
    )

    @api.model
    def _ocd_find(self, moment=None, company=None):
        """Return the window open at `moment`, or the next one, as a tuple
        (window, start, end) with naive UTC datetimes, or None when no window exists."""
        company = company or self.env.company
        moment = moment or fields.Datetime.now()
        windows = self.search([("company_id", "in", (company.id, False))])
        if not windows:
            return None
        tz = company._ocd_tz()
        local_moment = company._ocd_to_local(moment)
        for day_offset in range(3):
            midnight = datetime.combine(local_moment.date() + timedelta(days=day_offset), time())
            for window in windows:
                end = tz.localize(midnight + timedelta(hours=window.end_hour))
                if local_moment < end:
                    start = tz.localize(midnight + timedelta(hours=window.start_hour))
                    return window, company._ocd_to_utc(start), company._ocd_to_utc(end)
        return None
