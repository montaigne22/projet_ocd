from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_conversations = fields.Boolean(
        related="company_id.whatsapp_conversations", readonly=False
    )
    whatsapp_read_receipts = fields.Boolean(
        related="company_id.whatsapp_read_receipts", readonly=False
    )
    whatsapp_answer_reminders = fields.Boolean(
        related="company_id.whatsapp_answer_reminders", readonly=False
    )
    # options of the WhatsApp accounts of the company, set on all of them at once
    whatsapp_welcome_menu = fields.Boolean(string="Welcome Menu")
    whatsapp_away_message = fields.Boolean(string="Away Message")
    whatsapp_account_count = fields.Integer(
        string="WhatsApp Accounts", compute="_compute_whatsapp_account_count"
    )

    def _get_whatsapp_accounts(self):
        return self.env["whatsapp.account"].sudo().search([("company_id", "=", self.env.company.id)])

    def _compute_whatsapp_account_count(self):
        count = len(self._get_whatsapp_accounts())
        for settings in self:
            settings.whatsapp_account_count = count

    def get_values(self):
        values = super().get_values()
        accounts = self._get_whatsapp_accounts()
        values.update(
            whatsapp_welcome_menu=all(accounts.mapped("bot_enabled")) if accounts else True,
            whatsapp_away_message=all(accounts.mapped("away_message_enabled")) if accounts else True,
        )
        return values

    def set_values(self):
        super().set_values()
        accounts = self._get_whatsapp_accounts()
        for settings in self:
            vals = {}
            if any(account.bot_enabled != settings.whatsapp_welcome_menu for account in accounts):
                vals["bot_enabled"] = settings.whatsapp_welcome_menu
            if any(account.away_message_enabled != settings.whatsapp_away_message for account in accounts):
                vals["away_message_enabled"] = settings.whatsapp_away_message
            if vals:
                accounts.write(vals)

    def action_open_whatsapp_accounts(self):
        return self.env["ir.actions.act_window"]._for_xml_id("whatsapp_cloud.whatsapp_account_action")
