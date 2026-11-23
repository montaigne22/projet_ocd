from odoo import api, models


class WhatsappMessage(models.Model):
    _inherit = "whatsapp.message"

    @api.model
    def _process_incoming(self, account, data, contacts):
        """The answer of the customer to a request to call them (or the permission given when
        they call) is noted on the conversation, not posted as a message of the customer."""
        if (data.get("interactive") or {}).get("type") == "call_permission_reply":
            self.env["discuss.channel"].sudo()._whatsapp_call_permission_reply(account, data)
            return self.browse()
        return super()._process_incoming(account, data, contacts)
