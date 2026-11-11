from odoo import fields, models


class WhatsappBotOption(models.Model):
    _inherit = "whatsapp.bot.option"

    action = fields.Selection(
        selection_add=[
            ("order_status", "Status of the orders"),
            ("pay", "Pay an order"),
            ("stores", "Our stores"),
            ("delivery_fees", "Delivery fees"),
        ],
        ondelete={
            "order_status": "cascade", "pay": "cascade", "stores": "cascade",
            "delivery_fees": "cascade",
        },
    )

    def _is_available(self, channel):
        if self.action == "order_status":
            return channel.whatsapp_account_id.company_id.whatsapp_order_tracking
        if self.action == "pay":
            return bool(channel._whatsapp_get_orders_to_pay())
        if self.action == "stores":
            return bool(channel._whatsapp_get_stores())
        if self.action == "delivery_fees":
            return bool(channel._whatsapp_get_delivery_carriers())
        return super()._is_available(channel)

    def _run(self, channel, wa_message):
        if self.action == "order_status":
            if channel.whatsapp_account_id.company_id.whatsapp_order_tracking:
                channel._whatsapp_send_order_status()
            else:  # option of a menu sent before the order tracking was disabled
                channel._whatsapp_handover()
            return
        if self.action in ("pay", "stores", "delivery_fees"):
            channel.whatsapp_bot_state = "menu"
            if self.action == "pay":
                channel._whatsapp_send_orders_to_pay()
            elif self.action == "stores":
                channel._whatsapp_send_stores()
            else:
                channel._whatsapp_ask_delivery_city()
            return
        super()._run(channel, wa_message)
