from datetime import timedelta

from odoo import api, fields, models

# Lives without video shown in « To do now »
TODO_LIVES = 3
# The clips not made of these last days
FAILED_DAYS = 7


class OcdLiveDashboard(models.AbstractModel):
    """« To do now » of the team: the lives of the last days with products shown and no video
    sent (no clip without it), and the clips not made with their reason."""

    _inherit = "ocd.live.dashboard"

    @api.model
    def _ocd_todos(self):
        todos = super()._ocd_todos()
        if not self.env["ocd.automation"]._ocd_enabled("clips_video_missing"):
            return todos
        Booking = self.env["ocd.live.booking"]
        for booking in Booking._ocd_lives_without_video()[-TODO_LIVES:]:
            todos.append({
                "key": f"clips_video_{booking.id}",
                "tag": self.env._("Clips"),
                "tone": "yellow",
                "text": self.env._(
                    "Live of %(vendor)s, %(day)s: send its video to make its clips",
                    vendor=booking.partner_id.name, day=self._ocd_local_day(booking.start_datetime),
                ),
                "action": booking.action_ocd_open_clips(),
            })
        failed = self.env["ocd.live.clip"].search([
            ("company_id", "in", (self.env.company.id, False)), ("state", "=", "failed"),
            ("write_date", ">", fields.Datetime.now() - timedelta(days=FAILED_DAYS)),
        ])
        if failed:
            action = self._ocd_action("ocd_clips.ocd_live_clip_action", [("id", "in", failed.ids)],
                                      name=self.env._("Clips not made"))
            todos.append({
                "key": "clips_failed",
                "tag": self.env._("Clips"),
                "tone": "grey",
                "text": self.env._("1 clip not made: see why") if len(failed) == 1
                else self.env._("%s clips not made: see why", len(failed)),
                "action": action,
            })
        return todos
