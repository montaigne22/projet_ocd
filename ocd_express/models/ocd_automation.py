from odoo import fields, models

from odoo.addons.ocd_live.models import ocd_automation

# The automations of OCD Express have their group on the page of the automations
if "express" not in ocd_automation.GROUP_ORDER:
    ocd_automation.GROUP_ORDER.insert(ocd_automation.GROUP_ORDER.index("money") + 1, "express")


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    group = fields.Selection(selection_add=[("express", "OCD Express")], ondelete={"express": "set default"})
