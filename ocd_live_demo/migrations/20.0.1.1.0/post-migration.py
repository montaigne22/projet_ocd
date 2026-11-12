from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """The demo installed before: no WhatsApp to its contacts (ocd_live_demo_whatsapp, new),
    no opening date for the bookings, and the new scenario (15 vendors in 8 countries) on the days
    around today."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Module = env["ir.module.module"]
    if Module.search_count([("name", "=", "whatsapp_cloud"), ("state", "in", ("installed", "to upgrade"))]):
        # Installed in this same update: the modules marked here are loaded after this one
        Module.search([("name", "=", "ocd_live_demo_whatsapp"), ("state", "=", "uninstalled")]).button_install()
    demo = OcdLiveDemo(env)
    # The former scenario: its past live of Brenda was at the studio (she lives in Douala) and
    # takes the hour of a live of the new week; the new scenario has her replays. The waiting
    # list of Mireille was for a day at the studio, far from Cotonou.
    brenda, mireille = demo.ref("vendor_brenda"), demo.ref("vendor_mireille")
    past = env["ocd.live.booking"].search([
        ("partner_id", "=", brenda.id), ("mode", "=", "studio"), ("state", "=", "done"), ("sale_line_id", "=", False),
    ])
    past.write({"state": "cancelled"})
    past.unlink()
    env["ocd.live.waitlist"].search([("partner_id", "=", mireille.id), ("mode", "=", "studio")]).unlink()
    demo.open_bookings()
    demo.keep_current()
