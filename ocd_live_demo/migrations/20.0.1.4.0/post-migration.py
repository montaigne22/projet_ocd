from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_demo.hooks import OcdLiveDemo


def migrate(cr, version):
    """The cards of the feed (a short video for Awa, an image for Ama, the products for the
    others), the names on TikTok of the vendors, the phones of the hosts; the lives booked go
    on the accounts of OCD Live (added by the data of the demo): no link of the vendor on them."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    demo = OcdLiveDemo(env)
    demo.step("the cards of the feed", demo.cards)
    demo.step("the lives on the accounts of OCD Live", demo.apply_media)
    env["ocd.live.booking"]._ocd_assign_accounts()
