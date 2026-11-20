import base64
import hashlib
import hmac
import secrets
import time

from odoo import fields, models

from odoo.addons.whatsapp_cloud_call import const


class ResUsers(models.Model):
    _inherit = "res.users"

    whatsapp_call_available = fields.Boolean(
        string="Takes the WhatsApp Calls",
        help="The agent takes the calls (phone of the top bar): the calls ring for them while "
        "their page is open.",
    )
    whatsapp_call_sip_password = fields.Char(
        string="Password of the Phone", groups="base.group_system", copy=False,
        help="Password of the agent on the call server, given to their phone in Odoo.",
    )

    def _whatsapp_call_password(self):
        """Password of the agent on the call server (created at the first need)."""
        self.ensure_one()
        user = self.sudo()
        if not user.whatsapp_call_sip_password:
            user.whatsapp_call_sip_password = secrets.token_urlsafe(24)
        return user.whatsapp_call_sip_password

    def _whatsapp_call_ice_servers(self, host):
        """STUN and TURN of the call server for the agent's browser: TURN credentials of the
        REST API of coturn (use-auth-secret), valid 12 hours."""
        self.ensure_one()
        servers = [{"urls": [f"stun:{host}:3478"]}]
        secret = self.env["ir.config_parameter"].sudo().get_str(const.PARAM_TURN_SECRET)
        if secret:
            expiry = int(time.time() + const.TURN_VALIDITY.total_seconds())
            username = f"{expiry}:{const.AGENT_PREFIX}{self.id}"
            digest = hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
            servers.append({
                "urls": [f"turn:{host}:3478?transport=udp", f"turns:{host}:443?transport=tcp"],
                "username": username,
                "credential": base64.b64encode(digest).decode(),
            })
        return servers

    def _whatsapp_call_softphone(self):
        """Settings of the phone of the top bar for the agent, or None when the agent takes no
        call (no account with calls, or no call server)."""
        self.ensure_one()
        host = (self.env["ir.config_parameter"].sudo().get_str(const.PARAM_HOST) or "").strip()
        if not host or self.share or self not in self.env["whatsapp.account"]._call_get_agents():
            return None
        port = int(self.env["ir.config_parameter"].sudo().get_str(const.PARAM_WSS_PORT)
                   or const.DEFAULT_WSS_PORT)
        login = f"{const.AGENT_PREFIX}{self.id}"
        return {
            "wss": f"wss://{host}:{port}",
            "uri": f"sip:{login}@{host}",
            "login": login,
            "password": self._whatsapp_call_password(),
            "display_name": self.name,
            "ice_servers": self._whatsapp_call_ice_servers(host),
            "available": self.whatsapp_call_available,
        }
