from odoo import fields, models

from odoo.addons.ocd_live.models import ocd_automation

# The automations of the big evenings have their group on the page of the automations
if "evenings" not in ocd_automation.GROUP_ORDER:
    ocd_automation.GROUP_ORDER.insert(ocd_automation.GROUP_ORDER.index("lives") + 1, "evenings")


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    group = fields.Selection(selection_add=[("evenings", "Big evenings")], ondelete={"evenings": "set default"})
