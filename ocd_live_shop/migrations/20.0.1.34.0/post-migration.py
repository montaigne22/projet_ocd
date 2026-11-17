"""Follow a vendor (chantier 1): the « Tell me on WhatsApp » of the next live still waiting become
follows of the lives (not of the news, which they never asked for)."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    alerts = env["ocd.boutique.alert"].search([("kind", "=", "live"), ("state", "=", "waiting")])
    Follower = env["ocd.vendor.follower"].with_context(active_test=False)
    for alert in alerts:
        vendor, partner = alert.vendor_id, alert.partner_id
        if partner == vendor or not vendor.ocd_is_vendor:
            continue
        if not Follower.search_count([("partner_id", "=", partner.id), ("vendor_id", "=", vendor.id)]):
            Follower.create({
                "partner_id": partner.id, "vendor_id": vendor.id, "lives": True, "news": False,
                "source": "alert", "followed_at": alert.create_date, "company_id": alert.company_id.id,
            })
        partner._ocd_agree_by_following()
    alerts.write({"state": "cancelled"})
