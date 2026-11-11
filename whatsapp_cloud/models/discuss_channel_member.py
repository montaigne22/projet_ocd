from datetime import timedelta

from odoo import fields, models

# "Typing..." is sent to the customer at most once in this time per conversation (it lasts
# 25 seconds at WhatsApp). Kept in memory: a best effort, per worker.
TYPING_INTERVAL = timedelta(seconds=20)
_typing_sent = {}


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    def _set_last_seen_message(self, message, notify=True):
        """An agent read the conversation: blue ticks for the customer."""
        super()._set_last_seen_message(message, notify=notify)
        if (
            self.channel_id.channel_type == "whatsapp"
            and self.channel_id.whatsapp_account_id.company_id.whatsapp_read_receipts
            and self.partner_id.user_ids.filtered(lambda user: not user.share)
        ):
            self.channel_id._whatsapp_queue_read_receipt(typing=False)

    def _notify_typing(self, is_typing):
        """An agent writes: "typing..." for the customer."""
        super()._notify_typing(is_typing)
        if not is_typing:
            return
        now = fields.Datetime.now()
        for member in self.filtered(
            lambda m: m.channel_id.channel_type == "whatsapp"
            and m.channel_id.whatsapp_account_id.company_id.whatsapp_read_receipts
            and m.partner_id.user_ids.filtered(lambda user: not user.share)
        ):
            channel = member.channel_id
            last = _typing_sent.get(channel.id)
            if last and last > now - TYPING_INTERVAL:
                continue
            if channel._whatsapp_is_window_open():
                _typing_sent[channel.id] = now
                channel._whatsapp_queue_read_receipt(typing=True)
