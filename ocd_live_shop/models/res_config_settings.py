from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ocd_default_commission = fields.Float(related="company_id.ocd_default_commission", readonly=False)
    ocd_default_delivery_mode = fields.Selection(
        related="company_id.ocd_default_delivery_mode", readonly=False
    )
    ocd_prep_hours = fields.Integer(related="company_id.ocd_prep_hours", readonly=False)
    ocd_escalation_hours = fields.Integer(related="company_id.ocd_escalation_hours", readonly=False)
    ocd_code_max_attempts = fields.Integer(related="company_id.ocd_code_max_attempts", readonly=False)
    ocd_max_failed_attempts = fields.Integer(
        related="company_id.ocd_max_failed_attempts", readonly=False
    )
    ocd_return_days = fields.Integer(related="company_id.ocd_return_days", readonly=False)
    ocd_cash_deadline = fields.Float(related="company_id.ocd_cash_deadline", readonly=False)
    ocd_cod_cash = fields.Boolean(related="company_id.ocd_cod_cash", readonly=False)
    ocd_cod_online = fields.Boolean(related="company_id.ocd_cod_online", readonly=False)
    ocd_cod_momo_declared = fields.Boolean(
        related="company_id.ocd_cod_momo_declared", readonly=False
    )
    ocd_default_payout_frequency = fields.Selection(
        related="company_id.ocd_default_payout_frequency", readonly=False
    )
    ocd_payout_weekday = fields.Selection(related="company_id.ocd_payout_weekday", readonly=False)
    ocd_payout_min_amount = fields.Float(related="company_id.ocd_payout_min_amount", readonly=False)
    ocd_payout_journal_id = fields.Many2one(
        related="company_id.ocd_payout_journal_id", readonly=False
    )
    ocd_deliveries_channel_id = fields.Many2one(
        related="company_id.ocd_deliveries_channel_id", readonly=False
    )
