from odoo import fields, models

from odoo.addons.ocd_live.models import ocd_automation

# The automations of OCD Tickets have their group on the page of the automations, after the votes
if "tickets" not in ocd_automation.GROUP_ORDER:
    after = "votes" if "votes" in ocd_automation.GROUP_ORDER else "money"
    ocd_automation.GROUP_ORDER.insert(ocd_automation.GROUP_ORDER.index(after) + 1, "tickets")


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    group = fields.Selection(selection_add=[("tickets", "Tickets")], ondelete={"tickets": "set default"})
