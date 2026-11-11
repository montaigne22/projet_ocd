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
    ocd_vendor_rate_min = fields.Monetary(related="company_id.ocd_vendor_rate_min", readonly=False)
    ocd_vendor_rate_max = fields.Monetary(related="company_id.ocd_vendor_rate_max", readonly=False)
    ocd_delivery_commission = fields.Float(related="company_id.ocd_delivery_commission", readonly=False)
    ocd_stock_city_id = fields.Many2one(related="company_id.ocd_stock_city_id", readonly=False)
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

    def action_ocd_rates_from_carriers(self):
        """Create the rates of OCD Live from the delivery methods by city, once each."""
        created = self.env["ocd.delivery.rate"]._ocd_rates_from_carriers(self.company_id)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if created else "info",
                "message": self.env._("%s rates created: check their prices, then activate them.", len(created))
                if created else self.env._("No new delivery method to turn into rates."),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

