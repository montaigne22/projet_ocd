from odoo import fields, models

from odoo.addons.ocd_live.models import ocd_automation

# The automations of the clips have their group on the page of the automations, after the lives
if "clips" not in ocd_automation.GROUP_ORDER:
    ocd_automation.GROUP_ORDER.insert(ocd_automation.GROUP_ORDER.index("lives") + 1, "clips")


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    group = fields.Selection(selection_add=[("clips", "Clips")], ondelete={"clips": "set default"})
