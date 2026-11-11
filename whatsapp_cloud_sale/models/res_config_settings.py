from odoo import fields, models

# Notifications of the settings: automation rules, archived when disabled.
WHATSAPP_RULES = {
    "whatsapp_notify_order_received": "whatsapp_cloud_sale.automation_order_received",
    "whatsapp_notify_order_confirmed": "whatsapp_cloud_sale.automation_order_confirmed",
    "whatsapp_notify_order_shipped": "whatsapp_cloud_sale.automation_order_shipped",
    "whatsapp_notify_delivery_feedback": "whatsapp_cloud_sale.automation_delivery_feedback",
}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_whatsapp_number = fields.Char(
        related="website_id.whatsapp_number", readonly=False, string="WhatsApp Number"
    )
    website_whatsapp_order_button = fields.Boolean(
        related="website_id.whatsapp_order_button", readonly=False
    )
    website_whatsapp_checkout_consent = fields.Boolean(
        related="website_id.whatsapp_checkout_consent", readonly=False
    )
    whatsapp_order_tracking = fields.Boolean(
        related="company_id.whatsapp_order_tracking", readonly=False
    )
    whatsapp_quotation = fields.Boolean(related="company_id.whatsapp_quotation", readonly=False)
    whatsapp_notify_order_received = fields.Boolean(string="Order Received")
    whatsapp_notify_order_confirmed = fields.Boolean(string="Order Confirmed")
    whatsapp_notify_order_shipped = fields.Boolean(string="Order Shipped")
    whatsapp_notify_delivery_feedback = fields.Boolean(string="Satisfaction after the Delivery")

    def get_values(self):
        values = super().get_values()
        for fname, xmlid in WHATSAPP_RULES.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            values[fname] = bool(rule and rule.active)
        return values

    def set_values(self):
        super().set_values()
        for fname, xmlid in WHATSAPP_RULES.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if rule and rule.active != self[fname]:
                rule.sudo().active = self[fname]

    def action_open_whatsapp_automations(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("base_automation.base_automation_act")
        action["domain"] = [("action_server_ids.state", "=", "whatsapp")]
        action["context"] = {"active_test": False}
        return action
