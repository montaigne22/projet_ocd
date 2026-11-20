import secrets

from odoo import _, api, fields, models

from odoo.addons.whatsapp_cloud_call import const


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_call_host = fields.Char(
        string="Address of the Call Server",
        config_parameter=const.PARAM_HOST,
        help="Name of the call server (FreeSWITCH), e.g. calls.example.com: its certificate must "
        "be for this name (Meta checks it).",
    )
    whatsapp_call_sip_port = fields.Integer(
        string="SIP Port (Meta)", config_parameter=const.PARAM_SIP_PORT,
        default=const.DEFAULT_SIP_PORT,
    )
    whatsapp_call_wss_port = fields.Integer(
        string="Port of the Agents (WSS)", config_parameter=const.PARAM_WSS_PORT,
        default=const.DEFAULT_WSS_PORT,
    )
    whatsapp_call_turn_secret = fields.Char(
        string="Secret of the TURN Relay", config_parameter=const.PARAM_TURN_SECRET,
        groups="base.group_system",
        help="Same value as static-auth-secret in the configuration of coturn on the call server.",
    )
    whatsapp_call_token = fields.Char(
        string="Key of the Call Server", compute="_compute_whatsapp_call_token",
        groups="base.group_system",
    )
    whatsapp_call_last_seen = fields.Char(
        string="Last Report of the Call Server", compute="_compute_whatsapp_call_token"
    )
    whatsapp_call_agents = fields.Integer(
        string="Connected Agents", compute="_compute_whatsapp_call_token"
    )

    @api.model
    def _whatsapp_call_get_token(self):
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_str(const.PARAM_TOKEN)
        if not token:
            token = secrets.token_urlsafe(32)
            params.set_str(const.PARAM_TOKEN, token)
        return token

    def _compute_whatsapp_call_token(self):
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_str(const.PARAM_TOKEN) or ""
        server = self.env["whatsapp.call.server"]._get()
        last_seen = (
            fields.Datetime.to_string(fields.Datetime.context_timestamp(self, server.last_seen))
            if server.last_seen else _("Never")
        )
        for settings in self:
            settings.whatsapp_call_token = token
            settings.whatsapp_call_last_seen = last_seen
            settings.whatsapp_call_agents = server.registration_count

    def action_whatsapp_call_new_token(self):
        """A new key for the call server (to copy in its configuration)."""
        self.env["ir.config_parameter"].sudo().set_str(const.PARAM_TOKEN, secrets.token_urlsafe(32))
        return {"type": "ir.actions.client", "tag": "reload"}
