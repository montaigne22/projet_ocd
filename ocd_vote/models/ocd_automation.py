from odoo import fields, models

from odoo.addons.ocd_live.models import ocd_automation

# The automations of OCD Vote have their group on the page of the automations
if "votes" not in ocd_automation.GROUP_ORDER:
    ocd_automation.GROUP_ORDER.insert(ocd_automation.GROUP_ORDER.index("money") + 1, "votes")


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    group = fields.Selection(selection_add=[("votes", "Votes")], ondelete={"votes": "set default"})
