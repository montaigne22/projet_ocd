from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """OCD Express in the demo (when it is installed): Nadège Mode and her parcels of the last
    week, the request of Linda Cosmétiques. Also done by the scheduled action of the demo."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    OcdLiveDemo(env).keep_current()
