from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """The modules around the shop in the demo, those installed: the formulas of OCD Business, the
    ambassador and her gains, the big events of Friday. Also done by the scheduled action."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    OcdLiveDemo(env).keep_current()
