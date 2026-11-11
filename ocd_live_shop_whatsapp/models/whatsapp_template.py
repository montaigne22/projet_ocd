from odoo import models


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    def _send(self, records):
        """Override of `whatsapp_cloud`: the parcels of OCD Live have their own messages (on
        the way with the code, failed attempt, delivered); the messages of the shop about the
        transfers are kept only where they add something (see `_ocd_whatsapp_keep`)."""
        if records._name == "stock.picking":
            records = records._ocd_whatsapp_keep(self)
        return super()._send(records)
