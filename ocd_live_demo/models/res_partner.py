import re

from odoo import models

from .. import scenario


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_demo_contact(self):
        """Whether one of these contacts belongs to the demo (its vendors, customers and
        couriers have example numbers: no message goes to them, see ocd_live_demo_whatsapp), as
        the customers of its parcels of OCD Express, created with each parcel."""
        partners = self | self.commercial_partner_id
        if not partners:
            return False
        phones = scenario.express_phones()
        if any(re.sub(r"\D", "", partner.phone or "") in phones for partner in partners):
            return True
        return bool(self.env["ir.model.data"].sudo().search_count([
            ("module", "=", "ocd_live_demo"), ("model", "=", "res.partner"), ("res_id", "in", partners.ids),
        ], limit=1))
