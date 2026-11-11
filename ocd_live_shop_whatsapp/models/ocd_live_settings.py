from odoo import api, models


class OcdLiveSettings(models.AbstractModel):
    """The messages of the shop on the WhatsApp section of the settings page: the automation
    rules of whatsapp_cloud_sale that OCD Live keeps for its orders."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_section_whatsapp(self):
        section = super()._ocd_section_whatsapp()
        _ = self.env._
        items = []
        confirmed = "whatsapp_cloud_sale.automation_order_confirmed"
        if self.env.ref(confirmed, raise_if_not_found=False):
            title = _("Order confirmed, to the customer")
            help_text = _("When the order is confirmed: paid, or to pay at the door.")
            items.append(self._ocd_rule_item("wa_order_confirmed", confirmed, title, help_text))
        feedback = "whatsapp_cloud_sale.automation_delivery_feedback"
        if self.env.ref(feedback, raise_if_not_found=False):
            title = _("Ask for a rating after the delivery")
            help_text = _("Two days after the last parcel of the order, the customer rates it from 1 to 5.")
            items.append(self._ocd_rule_item("wa_delivery_feedback", feedback, title, help_text))
        # before the templates, last of the section
        section["items"][-1:-1] = items
        return section

    @api.model
    def _ocd_rule_item(self, key, xmlid, title, help_text):
        return self._ocd_item("check", key, title, help_text, get="_ocd_get_rule_active", set="_ocd_set_rule_active", args=[xmlid])

    def _ocd_get_rule_active(self, xmlid):
        rule = self.env.ref(xmlid, raise_if_not_found=False)
        return bool(rule and rule.sudo().active)

    def _ocd_set_rule_active(self, xmlid, value):
        rule = self.env.ref(xmlid, raise_if_not_found=False)
        if rule:
            rule.sudo().active = value
