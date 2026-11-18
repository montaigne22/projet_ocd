from odoo import models

# The messages of an order of the shop that would repeat the one of the tickets
ORDER_TEMPLATES = ("order_confirmed", "order_received")


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    def _send(self, records):
        """Override of `whatsapp_cloud`: an order of tickets is told by its own message (the
        tickets ready), not by the messages of the orders of the shop."""
        if records._name == "sale.order" and self.template_name in ORDER_TEMPLATES:
            records = records.filtered(lambda order: not order.sudo().ocd_ticket_event_id)
            if not records:
                return self.env["whatsapp.message"]
        return super()._send(records)
