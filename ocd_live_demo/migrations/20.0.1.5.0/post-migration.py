from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """The currencies by country in the demo: the vendors of Cameroon in FCFA (XAF, CamPay),
    Kadi (Paris) in euros. The orders already made keep their currency."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    demo = OcdLiveDemo(env)
    demo.step("the currencies by country", demo.currencies)
