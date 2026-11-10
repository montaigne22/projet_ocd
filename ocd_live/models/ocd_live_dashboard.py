from datetime import datetime, time, timedelta

from odoo import api, fields, models


class OcdLiveDashboard(models.AbstractModel):
    """Figures of the day for the team: lives, directory, and the shop when installed."""

    _name = "ocd.live.dashboard"
    _description = "OCD Live Dashboard"

    @api.model
    def get_dashboard_data(self):
        return {"sections": self._ocd_sections()}

    @api.model
    def _ocd_day_bounds(self):
        """Return the start and the end (naive UTC) of today at the studio."""
        company = self.env.company
        tz = company._ocd_tz()
        midnight = tz.localize(datetime.combine(company._ocd_local_today(), time()))
        start = company._ocd_to_utc(midnight)
        return start, start + timedelta(days=1)

    @api.model
    def _ocd_tile(self, key, label, model, domain, action_xmlid, value=None, alert=False):
        count = self.env[model].search_count(domain) if value is None else value
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action.update({"domain": domain, "context": {}, "name": label})
        return {
            "key": key,
            "label": label,
            "value": count,
            "alert": bool(alert and count),
            "action": action,
        }

    @api.model
    def _ocd_sections(self):
        start, end = self._ocd_day_bounds()
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        credits = self.env["ocd.live.credit"].search([("state", "=", "active")])
        reminder_days = self.env.company.ocd_pass_reminder_days
        return [
            {
                "key": "lives",
                "title": self.env._("Lives"),
                "tiles": [
                    self._ocd_tile(
                        "today", self.env._("Lives today"), "ocd.live.booking",
                        [("state", "in", ("confirmed", "done")), ("start_datetime", ">=", start), ("start_datetime", "<", end)],
                        "ocd_live.ocd_live_booking_action",
                    ),
                    self._ocd_tile(
                        "held", self.env._("Held, waiting for the payment"), "ocd.live.booking",
                        [("state", "=", "draft")], "ocd_live.ocd_live_booking_action",
                    ),
                    self._ocd_tile(
                        "host", self.env._("Remote lives without host"), "ocd.live.booking",
                        [("needs_host", "=", True), ("state", "=", "confirmed"), ("start_datetime", ">=", now)],
                        "ocd_live.ocd_live_booking_action", alert=True,
                    ),
                    self._ocd_tile(
                        "replay", self.env._("Replays to publish"), "ocd.live.booking",
                        [("state", "=", "done"), ("replay_published", "=", False)],
                        "ocd_live.ocd_live_booking_action",
                    ),
                    self._ocd_tile(
                        "credits", self.env._("Lives to place by the vendors"), "ocd.live.credit",
                        [("state", "=", "active")], "ocd_live.ocd_live_credit_action",
                        value=sum(credits.mapped("remaining")),
                    ),
                ],
            },
            {
                "key": "directory",
                "title": self.env._("Directory"),
                "tiles": [
                    self._ocd_tile(
                        "to_check", self.env._("Links to check"), "ocd.directory.listing",
                        [("state", "=", "to_check")], "ocd_live.ocd_directory_listing_action", alert=True,
                    ),
                    self._ocd_tile(
                        "online", self.env._("Lives online"), "ocd.directory.listing",
                        [("state", "=", "published")], "ocd_live.ocd_directory_listing_action",
                    ),
                    self._ocd_tile(
                        "passes", self.env._("Active passes"), "ocd.directory.pass",
                        [("state", "=", "active")], "ocd_live.ocd_directory_pass_action",
                    ),
                    self._ocd_tile(
                        "ending", self.env._("Passes ending soon"), "ocd.directory.pass",
                        [("state", "=", "active"), ("date_end", "<=", today + timedelta(days=reminder_days))],
                        "ocd_live.ocd_directory_pass_action",
                    ),
                    self._ocd_tile(
                        "vendors", self.env._("New vendors to check"), "res.partner",
                        [("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "to_check")],
                        "ocd_live.res_partner_action_ocd_vendor",
                    ),
                ],
            },
        ]
