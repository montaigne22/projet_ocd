from odoo import api, models


class OcdLivePlanning(models.AbstractModel):
    _inherit = "ocd.live.planning"

    @api.model
    def _ocd_regie_action(self):
        return self.env["ir.actions.actions"]._for_xml_id("ocd_live_shop.ocd_live_regie_action")
