from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ocd_booking_open_date = fields.Date(
        related="company_id.ocd_booking_open_date", readonly=False
    )
    ocd_studio_tz = fields.Selection(related="company_id.ocd_studio_tz", readonly=False)
    ocd_first_slot_hour = fields.Float(related="company_id.ocd_first_slot_hour", readonly=False)
    ocd_slot_hours = fields.Float(related="company_id.ocd_slot_hours", readonly=False)
    ocd_slots_per_day = fields.Integer(related="company_id.ocd_slots_per_day", readonly=False)
    ocd_hold_minutes = fields.Integer(related="company_id.ocd_hold_minutes", readonly=False)
    ocd_manual_hold_hours = fields.Integer(
        related="company_id.ocd_manual_hold_hours", readonly=False
    )
    ocd_require_animatrice = fields.Boolean(
        related="company_id.ocd_require_animatrice", readonly=False
    )
    ocd_live_responsible_id = fields.Many2one(
        related="company_id.ocd_live_responsible_id", readonly=False
    )
    ocd_lives_channel_id = fields.Many2one(
        related="company_id.ocd_lives_channel_id", readonly=False
    )
    ocd_pass_reminder_days = fields.Integer(
        related="company_id.ocd_pass_reminder_days", readonly=False
    )
    ocd_min_notice_hours = fields.Integer(
        related="company_id.ocd_min_notice_hours", readonly=False
    )
    ocd_open_mon = fields.Boolean(related="company_id.ocd_open_mon", readonly=False)
    ocd_open_tue = fields.Boolean(related="company_id.ocd_open_tue", readonly=False)
    ocd_open_wed = fields.Boolean(related="company_id.ocd_open_wed", readonly=False)
    ocd_open_thu = fields.Boolean(related="company_id.ocd_open_thu", readonly=False)
    ocd_open_fri = fields.Boolean(related="company_id.ocd_open_fri", readonly=False)
    ocd_open_sat = fields.Boolean(related="company_id.ocd_open_sat", readonly=False)
    ocd_open_sun = fields.Boolean(related="company_id.ocd_open_sun", readonly=False)
    ocd_calendar_mode = fields.Selection(related="company_id.ocd_calendar_mode", readonly=False)
    ocd_booking_flow = fields.Selection(related="company_id.ocd_booking_flow", readonly=False)
    ocd_vendor_login = fields.Selection(related="company_id.ocd_vendor_login", readonly=False)
    ocd_move_limit_hours = fields.Integer(related="company_id.ocd_move_limit_hours", readonly=False)
    ocd_studio_city = fields.Char(related="company_id.ocd_studio_city", readonly=False)
