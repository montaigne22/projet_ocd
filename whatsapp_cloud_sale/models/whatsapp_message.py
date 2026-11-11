import re

from odoo import api, models

FEEDBACK_TEMPLATE = "delivery_feedback"


class WhatsappMessage(models.Model):
    _inherit = "whatsapp.message"

    def _whatsapp_get_rating(self, reply_id=None):
        """The order and the rating (1 to 5) of a button of the satisfaction template;
        (empty order, 0) for another message."""
        self.ensure_one()
        no_rating = (self.env["sale.order"], 0)
        parent = self.parent_id
        if self.message_type != "button" or parent.template_id.template_name != FEEDBACK_TEMPLATE:
            return no_rating
        match = re.search(r"[1-5]", f"{reply_id or ''} {self.body or ''}")
        record = parent._get_record()
        if not match or record is None:
            return no_rating
        order = record.sale_id if record._name == "stock.picking" else record
        if order._name != "sale.order" or not order:
            return no_rating
        return order, int(match.group())

    @api.model
    def _process_incoming_without_conversation(self, account, data, number, user_ref):
        """The ratings are stored on the orders, even without conversations."""
        message = super()._process_incoming_without_conversation(account, data, number, user_ref)
        if message:
            order, value = message._whatsapp_get_rating((data.get("button") or {}).get("payload"))
            if order:
                order._whatsapp_add_rating(value, message.partner_id)
        return message
