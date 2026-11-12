from odoo import models


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    def _send(self, records):
        """Override of `whatsapp_cloud`: no message at all for the contacts of the demo (their
        numbers are examples); the callers see that nothing is on its way."""
        self.ensure_one()
        kept = records.filtered(lambda record: not self._get_recipient(record)._ocd_demo_contact())
        if not kept:
            return self.env["whatsapp.message"]
        return super()._send(kept)

    def _get_skip_reason(self, account, partner, number):
        """Override of `whatsapp_cloud`: tell why in the sending window of WhatsApp."""
        if partner and partner._ocd_demo_contact():
            return self.env._("Contact of the demo of OCD Live: its number is an example, no message is sent to it.")
        return super()._get_skip_reason(account, partner, number)
