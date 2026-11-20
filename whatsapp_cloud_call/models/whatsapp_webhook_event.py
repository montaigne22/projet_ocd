from odoo import models


class WhatsappWebhookEvent(models.Model):
    _inherit = "whatsapp.webhook.event"

    def _dispatch(self, value):
        if self.field == "calls":
            metadata = value.get("metadata") or {}
            if metadata.get("phone_number_id") not in (None, self.account_id.phone_number_id):
                return
            self.env["whatsapp.call"]._meta_process(self.account_id, value)
            return
        super()._dispatch(value)
