from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """The shop of Douala kept on the days around today: Brenda and Fatou are paid every day
    by Mobile Money, Fatou prepares the orders of the evening the next morning; then the whole
    scenario is put on the days around today (the parcels of the former scenario are delivered)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    demo = OcdLiveDemo(env)
    demo.ref("vendor_brenda").write({"ocd_payout_frequency": "daily", "ocd_payout_momo": "+237 670112202"})
    demo.ref("vendor_fatou").write({
        "ocd_payout_frequency": "daily", "ocd_payout_momo": "+237 690112203", "ocd_prep_hours": 16,
    })
    demo.step("the WhatsApp account", demo.whatsapp_setup)
    demo.keep_current()
