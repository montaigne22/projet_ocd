from odoo import fields, models

from odoo.addons.ocd_live.models import ocd_automation

# The automations of the ambassadors have their group on the page of the automations
if "ambassadors" not in ocd_automation.GROUP_ORDER:
    ocd_automation.GROUP_ORDER.insert(ocd_automation.GROUP_ORDER.index("money") + 1, "ambassadors")


class OcdAutomation(models.Model):
    _inherit = "ocd.automation"

    group = fields.Selection(selection_add=[("ambassadors", "Ambassadors")], ondelete={"ambassadors": "set default"})

    def _ocd_runs_ambassador_gains(self):
        gains = self.env["ocd.ambassador.gain"].sudo().search(
            [("confirmed_at", ">=", fields.Datetime.now() - ocd_automation.WEEK)])
        return self._ocd_runs_of(gains, "confirmed_at", lambda gain: gain.ambassador_id.name)
