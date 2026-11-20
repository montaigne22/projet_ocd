from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """The stores, the team and the life of the shop in the demo: the stores of Brenda and her team,
    the relay point, the orders picked up at the store and at the relay point, the reviews, the
    followers, the figures of the last months. Also done by the scheduled action of the demo."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    OcdLiveDemo(env).keep_current()
