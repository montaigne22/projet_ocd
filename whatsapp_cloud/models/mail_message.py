from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    message_type = fields.Selection(
        selection_add=[("whatsapp_message", "WhatsApp")],
        ondelete={"whatsapp_message": lambda recs: recs.write({"message_type": "comment"})},
    )

    def _store_extra_fields(self, res: Store.FieldList, *, format_reply):
        super()._store_extra_fields(res, format_reply=format_reply)
        if not res.is_for_internal_users():
            return
        whatsapp_messages = self.filtered(lambda m: m.message_type == "whatsapp_message")
        if not whatsapp_messages:
            return
        # sudo: whatsapp.message - the status of the messages of an accessible conversation
        wa_messages = self.env["whatsapp.message"].sudo().search(
            [("mail_message_id", "in", whatsapp_messages.ids)], order="id"
        )
        by_message = {}
        for wa_message in wa_messages:
            # several WhatsApp messages for a message with files: the least advanced status
            current = by_message.get(wa_message.mail_message_id.id)
            if not current or wa_message._status_rank() < current._status_rank():
                by_message[wa_message.mail_message_id.id] = wa_message

        def status(message):
            wa_message = by_message.get(message.id)
            return wa_message._get_discuss_status() if wa_message else False

        def error(message):
            wa_message = by_message.get(message.id)
            return (wa_message.error_help or wa_message.error or False) if wa_message else False

        res.attr("whatsapp_status", status, predicate=lambda m: m in whatsapp_messages)
        res.attr("whatsapp_error", error, predicate=lambda m: m in whatsapp_messages)
