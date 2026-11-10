from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.base.models.res_partner import _tz_get


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_booking_open_date = fields.Date(
        string="Bookings Open On",
        default=lambda self: fields.Date.to_date("2026-12-01"),
        help="No live can be booked before this date.",
    )
    ocd_studio_tz = fields.Selection(
        selection=_tz_get,
        string="Studio Time Zone",
        default="Africa/Lome",
        help="Time zone of the studio: the slots are defined in this time zone.",
    )
    ocd_first_slot_hour = fields.Float(string="First Live Starts At", default=8.5)
    ocd_slot_hours = fields.Float(string="Live Duration (Hours)", default=1.5)
    ocd_slots_per_day = fields.Integer(string="Lives Per Day", default=9)
    ocd_hold_minutes = fields.Integer(
        string="Slot Held During The Payment (Minutes)",
        default=30,
        help="A slot chosen on the website is held for this time. Without payment, it is "
        "released and offered again.",
    )
    ocd_manual_hold_hours = fields.Integer(
        string="Slot Held For A Payment Checked By The Team (Hours)",
        default=24,
        help="When the vendor pays with a method checked by the team (e.g. Mobile Money in "
        "Togo), the slot stays held for this time.",
    )
    ocd_require_animatrice = fields.Boolean(
        string="Host Required For Remote Lives",
        default=True,
        help="Remind the team when a remote live has no host.",
    )
    ocd_live_responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Lives Manager",
        help="Receives the activities about the lives (host to choose, replay to publish).",
    )
    ocd_lives_channel_id = fields.Many2one(
        comodel_name="discuss.channel",
        string="Team Channel For Lives",
        help="Every confirmed booking is announced in this channel.",
    )
    ocd_pass_reminder_days = fields.Integer(
        string="Pass Reminder (Days Before The End)",
        default=3,
    )
    ocd_min_notice_hours = fields.Integer(
        string="Book At Least (Hours Before)",
        default=2,
        help="A slot can be booked on the website until this number of hours before it starts.",
    )

    _check_ocd_slot_hours = models.Constraint(
        "CHECK (ocd_slot_hours IS NULL OR ocd_slot_hours > 0)",
        "The live duration must be positive.",
    )
    _check_ocd_slots_per_day = models.Constraint(
        "CHECK (ocd_slots_per_day IS NULL OR ocd_slots_per_day > 0)",
        "There must be at least one live per day.",
    )

    @api.constrains("ocd_first_slot_hour", "ocd_slot_hours", "ocd_slots_per_day")
    def _check_ocd_studio_day(self):
        for company in self:
            end = company.ocd_first_slot_hour + company.ocd_slot_hours * company.ocd_slots_per_day
            if company.ocd_first_slot_hour < 0 or end > 24:
                raise ValidationError(
                    self.env._("The lives of a day must start and end on the same day.")
                )

    # === STUDIO CALENDAR HELPERS === #

    def _ocd_tz(self):
        self.ensure_one()
        return pytz.timezone(self.ocd_studio_tz or "Africa/Lome")

    def _ocd_to_local(self, value):
        """Convert a naive UTC datetime into an aware datetime of the studio time zone."""
        self.ensure_one()
        return pytz.utc.localize(value).astimezone(self._ocd_tz())

    def _ocd_to_utc(self, local_value):
        """Convert an aware datetime into a naive UTC datetime, as stored by the ORM."""
        return local_value.astimezone(pytz.utc).replace(tzinfo=None)

    def _ocd_local_today(self):
        self.ensure_one()
        return self._ocd_to_local(fields.Datetime.now()).date()

    def _ocd_slot_starts(self, day):
        """Return the starts (naive UTC) of the slots of `day`, a date of the studio."""
        self.ensure_one()
        tz = self._ocd_tz()
        midnight = datetime.combine(day, time())
        return [
            self._ocd_to_utc(
                tz.localize(midnight + timedelta(hours=self.ocd_first_slot_hour + index * self.ocd_slot_hours))
            )
            for index in range(self.ocd_slots_per_day)
        ]
