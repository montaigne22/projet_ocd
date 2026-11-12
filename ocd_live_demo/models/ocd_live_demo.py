from odoo import api, models

from .. import hooks


class OcdLiveDemo(models.AbstractModel):
    """The scheduled action of the demo: it keeps the scenario on the days around today."""

    _name = "ocd.live.demo"
    _description = "OCD Live Demo"

    @api.model
    def _cron_keep_current(self):
        hooks.OcdLiveDemo(self.env).keep_current()
