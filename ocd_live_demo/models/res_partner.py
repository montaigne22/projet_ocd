from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_demo_contact(self):
        """Whether one of these contacts belongs to the demo (its vendors, customers and
        couriers have example numbers: no message goes to them, see ocd_live_demo_whatsapp)."""
        partners = self | self.commercial_partner_id
        if not partners:
            return False
        return bool(self.env["ir.model.data"].sudo().search_count([
            ("module", "=", "ocd_live_demo"), ("model", "=", "res.partner"), ("res_id", "in", partners.ids),
        ], limit=1))
